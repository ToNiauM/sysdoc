# Convenção deste app: toda view é decorada com @login_required.
# Não existe view pública além da tela de login (D-07).
from __future__ import annotations

import logging
import shutil

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from . import fila, servicos, uploads
from .fila import FilaOcupada
from .forms import NovoProcessoForm, VerificacaoForm
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
        # TODO(07-07): redirecionar para processos:resultado quando a tela
        # de resultado existir. Até lá, avisa e volta ao início.
        messages.success(
            request,
            "Análise concluída. A tela de resultado ainda será entregue no próximo plano.",
        )
        return redirect("processos:inicio")

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
                reverse("processos:analise", args=[processo.slug]) if sucesso else None
            ),
        }

    resposta = JsonResponse(dados)
    resposta["Cache-Control"] = "no-store"
    return resposta
