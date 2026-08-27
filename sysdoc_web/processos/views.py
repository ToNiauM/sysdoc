# Convenção deste app: toda view é decorada com @login_required.
# Não existe view pública além da tela de login (D-07).
from __future__ import annotations

import logging
import shutil

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

import sysdoc

from . import apontamentos, downloads, fila, servicos, uploads
from .fila import FilaOcupada
from .forms import NovoProcessoForm, RevisaoDespachoForm, VerificacaoForm
from .models import STATUS_FINAIS, Processo

logger = logging.getLogger(__name__)


@login_required
def inicio(request):
    processos = Processo.objects.filter(criado_por=request.user).prefetch_related("jobs")
    return render(request, "processos/inicio.html", {"processos": processos})


@login_required
def novo_processo(request):
    if request.method == "POST":
        form = NovoProcessoForm(request.POST, request.FILES)
        if form.is_valid():
            slug = servicos.slug_disponivel(form.cleaned_data["nome"])
            documento_unico = form.cleaned_data.get("documento_unico")
            try:
                with transaction.atomic():
                    Processo.objects.create(
                        nome=form.cleaned_data["nome"],
                        slug=slug,
                        criado_por=request.user,
                    )
                    servicos.criar_pasta_do_processo(slug)
                    paths = servicos.caminhos(slug)
                    arquivos = (
                        [documento_unico]
                        if documento_unico
                        else request.FILES.getlist("pecas")
                    )
                    for arquivo in arquivos:
                        uploads.gravar_em(paths.documentos, arquivo)
            except Exception:
                logger.exception("Falha ao salvar documentos do processo %s", slug)
                shutil.rmtree(servicos.caminho_do_processo(slug), ignore_errors=True)
                messages.error(
                    request,
                    "Não foi possível salvar os documentos deste processo. Tente novamente.",
                )
                return render(
                    request,
                    "processos/novo.html",
                    {"form": form, "limite_upload_mb": settings.SYSDOC_WEB_MAX_UPLOAD_MB},
                )
            return redirect("processos:verificacao", slug=slug)
    else:
        form = NovoProcessoForm()
    return render(
        request,
        "processos/novo.html",
        {"form": form, "limite_upload_mb": settings.SYSDOC_WEB_MAX_UPLOAD_MB},
    )


@login_required
def verificacao(request, slug):
    if request.method == "POST":
        processo = get_object_or_404(Processo, slug=slug, criado_por=request.user)
        form = VerificacaoForm(request.POST)
        if form.is_valid():
            tipo = form.cleaned_data["tipo"]
            processo.tipo_verificacao = tipo
            processo.save(update_fields=["tipo_verificacao"])
            servicos.definir_tipo_verificacao(slug, tipo)
            return redirect("processos:analise", slug=slug)
    else:
        processo = get_object_or_404(Processo, slug=slug, criado_por=request.user)
        form = VerificacaoForm(initial={"tipo": processo.tipo_verificacao or "geral"})
    return render(
        request, "processos/verificacao.html", {"form": form, "processo": processo}
    )


@login_required
def analise(request, slug):
    processo = get_object_or_404(Processo, slug=slug, criado_por=request.user)
    job = processo.jobs.first()

    if job is not None and job.status == "concluida":
        return redirect("processos:resultado", slug=slug)

    pode_iniciar = job is None or not job.ativo
    return render(
        request,
        "processos/analise.html",
        {"processo": processo, "job": job, "pode_iniciar": pode_iniciar},
    )


@login_required
@require_POST
def iniciar_analise(request, slug):
    processo = get_object_or_404(Processo, slug=slug, criado_por=request.user)
    if not processo.tipo_verificacao:
        messages.error(
            request, "Escolha o tipo de contratação antes de iniciar a análise."
        )
        return redirect("processos:analise", slug=slug)
    try:
        fila.enfileirar(processo)
    except FilaOcupada as excecao:
        messages.warning(request, str(excecao))
    return redirect("processos:analise", slug=slug)


@login_required
@require_GET
def situacao_analise(request, slug):
    processo = get_object_or_404(Processo, slug=slug, criado_por=request.user)
    job = processo.jobs.first()

    if job is None:
        dados = {
            "status": "sem_analise",
            "situacao": "Nenhuma análise iniciada",
            "etapa": "",
            "percentual": 0,
            "concluida": False,
            "sucesso": False,
            "mensagem": "",
            "url_resultado": None,
        }
    else:
        concluida = job.status in STATUS_FINAIS
        sucesso = job.status == "concluida"
        dados = {
            "status": job.status,
            "situacao": job.get_status_display(),
            "etapa": job.etapa,
            "percentual": job.percentual,
            "concluida": concluida,
            "sucesso": sucesso,
            "mensagem": job.mensagem_erro,
            "url_resultado": (
                reverse("processos:resultado", args=[processo.slug]) if sucesso else None
            ),
        }

    resposta = JsonResponse(dados)
    resposta["Cache-Control"] = "no-store"
    return resposta


def _contexto_resultado(processo, dados, form=None):
    """Contexto compartilhado por `resultado` e `gerar_despacho` (D-13).

    Quando `dados` é `None` (análise ainda não produziu resultado), devolve
    só o suficiente para a tela mostrar a mensagem honesta e o link de
    volta — sem tentar montar contagem ou lista de itens sobre nada.
    """
    if dados is None:
        return {"processo": processo, "sem_resultado": True}
    paths = servicos.caminhos(processo.slug)
    return {
        "processo": processo,
        "resumo": apontamentos.resumo_para_tela(dados),
        "itens": apontamentos.itens_para_tela(dados),
        "form": form if form is not None else RevisaoDespachoForm(),
        "html_disponivel": sysdoc.localizar_html_analise(paths) is not None,
        "docx_disponivel": sysdoc.localizar_docx_despacho(paths) is not None,
    }


@login_required
def resultado(request, slug):
    """Tela 4 do fluxo (D-09): apontamentos, revisão e downloads."""
    processo = get_object_or_404(Processo, slug=slug, criado_por=request.user)
    dados = servicos.dados_consolidados(slug)
    contexto = _contexto_resultado(processo, dados)
    return render(request, "processos/resultado.html", contexto)


@login_required
@require_POST
def gerar_despacho(request, slug):
    """Única porta de entrada de `criar_documento` na aplicação web (D-11).

    O worker (`manage.py runworker`) e o fim da análise nunca chamam
    `criar_documento` — só um POST explícito nesta rota, com o campo
    `confirmo` marcado, pode produzir o DOCX do despacho. A ausência do
    aceite é o próprio bloqueio exigido por D-11, não um detalhe de UX.
    """
    processo = get_object_or_404(Processo, slug=slug, criado_por=request.user)
    if not processo.jobs.filter(status="concluida").exists():
        messages.error(request, "A análise deste processo ainda não foi concluída.")
        return redirect("processos:resultado", slug=slug)

    dados = servicos.dados_consolidados(slug)
    form = RevisaoDespachoForm(request.POST)
    if not form.is_valid():
        contexto = _contexto_resultado(processo, dados, form=form)
        return render(request, "processos/resultado.html", contexto)

    servicos.gravar_campos_despacho(
        slug, {campo: form.cleaned_data[campo] for campo in sysdoc.CAMPOS_DESPACHO}
    )

    try:
        sysdoc.criar_documento(str(servicos.caminho_do_processo(slug)), "dvi")
    except (SystemExit, Exception):
        logger.exception("Falha ao montar o despacho do processo %s", slug)
        messages.error(
            request,
            "Não foi possível montar o despacho. Procure o administrador do sistema.",
        )
        return redirect("processos:resultado", slug=slug)

    messages.success(request, "Despacho gerado. Use o botão de download abaixo.")
    return redirect("processos:resultado", slug=slug)


@login_required
@require_GET
def baixar_analise(request, slug):
    get_object_or_404(Processo, slug=slug, criado_por=request.user)
    paths = servicos.caminhos(slug)
    caminho = sysdoc.localizar_html_analise(paths)
    if caminho is None:
        raise Http404("Nenhuma análise disponível para download neste processo.")
    return downloads.entregar(
        caminho,
        servicos.caminho_do_processo(slug),
        caminho.name,
        "text/html; charset=utf-8",
    )


@login_required
@require_GET
def baixar_despacho(request, slug):
    get_object_or_404(Processo, slug=slug, criado_por=request.user)
    paths = servicos.caminhos(slug)
    caminho = sysdoc.localizar_docx_despacho(paths)
    if caminho is None:
        raise Http404("Nenhum despacho disponível para download neste processo.")
    return downloads.entregar(
        caminho,
        servicos.caminho_do_processo(slug),
        caminho.name,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
