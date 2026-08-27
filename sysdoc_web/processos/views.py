# Convenção deste app: toda view é decorada com @login_required.
# Não existe view pública além da tela de login (D-07).
from __future__ import annotations

import logging
import shutil

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from . import servicos, uploads
from .forms import NovoProcessoForm, VerificacaoForm
from .models import Processo

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
            # TODO(07-06): redirecionar para processos:analise quando a tela
            # de progresso existir. Até lá, avisa e volta ao início.
            messages.success(request, "Tipo de contratação registrado.")
            return redirect("processos:inicio")
    else:
        processo = get_object_or_404(Processo, slug=slug, criado_por=request.user)
        form = VerificacaoForm(initial={"tipo": processo.tipo_verificacao or "geral"})
    return render(
        request, "processos/verificacao.html", {"form": form, "processo": processo}
    )
