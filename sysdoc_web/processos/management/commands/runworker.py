"""
Worker single-slot do pipeline DVI (D-03, D-14, D-15, D-17 — 07-CONTEXT.md).

Importa `sysdoc` e `sysdoc_dvi.pipeline` como módulos Python e chama
`sysdoc.prepare()`/`pipeline.executar_run()` diretamente — sem iniciar
processo filho do binário da CLI, sem passar pelo dispatch de linha de
comando do motor DVI. O progresso do pipeline é traduzido para linguagem de
processo (`progresso.texto_da_etapa`)
antes de tocar o banco; qualquer falha vira a mensagem fixa `MENSAGEM_FALHA`
em português — o traceback real só é registrado via `logger.exception`, no
log do servidor (D-17): nenhum nome de provedor, alvo de modelo ou caminho
de arquivo chega a `AnaliseJob.mensagem_erro`.
"""

from __future__ import annotations

import logging
import time

from django.core.management.base import BaseCommand

import sysdoc
from sysdoc_dvi import pipeline
from sysdoc_web.processos import fila, progresso, servicos
from sysdoc_web.processos.models import AnaliseJob

logger = logging.getLogger("sysdoc_web.processos.worker")

MENSAGEM_FALHA = (
    "Não foi possível concluir a análise deste processo. Procure o administrador do "
    "sistema e informe o nome do processo e o horário da tentativa."
)


def _executar(job: AnaliseJob) -> None:
    job.etapa = "Lendo os documentos do processo"
    job.save(update_fields=["etapa"])

    caminho = str(servicos.caminho_do_processo(job.processo.slug))

    try:
        sysdoc.prepare(caminho)
    except (SystemExit, Exception):
        logger.exception("Falha ao preparar o cache do processo %s", job.processo.slug)
        fila.concluir(job, "falhou", mensagem_erro=MENSAGEM_FALHA)
        return

    def _sink(evento) -> None:
        job.etapa = progresso.texto_da_etapa(evento)
        update_fields = ["etapa"]
        if evento.etapa == "itens":
            job.itens_concluidos = evento.atual or 0
            job.itens_total = evento.total or 0
            update_fields += ["itens_concluidos", "itens_total"]
        job.save(update_fields=update_fields)

    try:
        rc = pipeline.executar_run(
            caminho, tipo=job.processo.tipo_verificacao or None, progresso=_sink
        )
    except (SystemExit, Exception):
        logger.exception("Falha inesperada na análise do processo %s", job.processo.slug)
        fila.concluir(job, "falhou", mensagem_erro=MENSAGEM_FALHA)
        return

    if rc == 0:
        fila.concluir(job, "concluida")
    else:
        fila.concluir(job, "falhou", mensagem_erro=MENSAGEM_FALHA)


class Command(BaseCommand):
    help = "Executa uma análise por vez (D-14), reivindicando o próximo job na fila."

    def add_arguments(self, parser):
        parser.add_argument("--intervalo", type=float, default=2.0)
        parser.add_argument("--uma-vez", action="store_true", dest="uma_vez")

    def handle(self, *args, **options):
        intervalo = options["intervalo"]
        uma_vez = options["uma_vez"]

        fila.sanear_jobs_orfaos()

        job_atual: AnaliseJob | None = None
        try:
            while True:
                job = fila.reivindicar_proximo()
                if job is None:
                    if uma_vez:
                        return
                    time.sleep(intervalo)
                    continue
                job_atual = job
                _executar(job)
                job_atual = None
                if uma_vez:
                    return
        except KeyboardInterrupt:
            if job_atual is not None:
                fila.concluir(
                    job_atual,
                    "interrompida",
                    mensagem_erro=(
                        "A análise foi interrompida manualmente. Inicie novamente se necessário."
                    ),
                )
