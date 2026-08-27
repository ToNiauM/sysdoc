"""
Fila single-slot de análise (D-14, D-15 — 07-CONTEXT.md; T-07-03-02).

`enfileirar` é o único ponto de entrada para criar um `AnaliseJob`. A recusa
de uma segunda análise concorrente vem da `UniqueConstraint`
`uma_analise_ativa_por_vez` do banco (models.py), nunca de um `if` de
leitura prévia que uma segunda thread do servidor de aplicação (gunicorn,
plano 07-04) poderia driblar entre a leitura e a escrita.

Nota sobre o retry de `OperationalError`: o SQLite já espera até
`OPTIONS["timeout"]` (20s, configurado em `sysdoc_web/settings.py` desde o
plano 07-02) pelo lock de escrita antes de o driver levantar
`OperationalError`. Na contenção comum — de milissegundos — essa espera do
driver resolve sozinha e o retry aqui nunca chega a ser exercitado; ele é
rede de segurança para o caso raro em que a contenção ultrapassa os 20s do
driver, não o caminho quente de latência. É o `timeout` do SQLite que
governa a espera típica, não o backoff de 0.1/0.2/0.4s abaixo.
"""

from __future__ import annotations

import time

from django.db import transaction
from django.db.utils import IntegrityError, OperationalError
from django.utils import timezone

from .models import STATUS_FINAIS, AnaliseJob

_MENSAGEM_FILA_OCUPADA = "Já existe uma análise em andamento. Aguarde a conclusão para iniciar outra."
_ESPERAS_RETRY_S = (0.1, 0.2, 0.4)


class FilaOcupada(Exception):
    def __init__(self, mensagem: str = _MENSAGEM_FILA_OCUPADA) -> None:
        super().__init__(mensagem)


def enfileirar(processo) -> AnaliseJob:
    ultimo_erro: OperationalError | None = None
    for tentativa, espera in enumerate((0.0, *_ESPERAS_RETRY_S)):
        if espera:
            time.sleep(espera)
        try:
            with transaction.atomic():
                # Nota (executor_notes, iteração 2 do plan-checker): este
                # `except IntegrityError` é intencionalmente amplo — não
                # distingue a violação de `uma_analise_ativa_por_vez` de
                # qualquer outro erro de integridade (por exemplo, uma FK
                # para um `Processo` apagado concorrentemente). Probabilidade
                # baixa (a view sempre busca o `Processo` antes de
                # enfileirar) e sem impacto no objetivo desta fase; inspecionar
                # o nome da constraint na exceção seria mais preciso, mas não
                # é feito aqui.
                return AnaliseJob.objects.create(processo=processo)
        except IntegrityError as exc:
            raise FilaOcupada() from exc
        except OperationalError as exc:
            ultimo_erro = exc
            continue
    raise FilaOcupada() from ultimo_erro


def reivindicar_proximo() -> AnaliseJob | None:
    job = AnaliseJob.objects.filter(status="na_fila").order_by("criado_em").first()
    if job is None:
        return None
    linhas_afetadas = AnaliseJob.objects.filter(pk=job.pk, status="na_fila").update(
        status="em_execucao", iniciado_em=timezone.now()
    )
    if linhas_afetadas != 1:
        return None
    job.refresh_from_db()
    return job


def concluir(job: AnaliseJob, status: str, mensagem_erro: str = "") -> None:
    if status not in STATUS_FINAIS:
        raise ValueError(f"status final inválido: {status!r}")
    job.status = status
    job.mensagem_erro = mensagem_erro
    job.concluido_em = timezone.now()
    job.save(update_fields=["status", "mensagem_erro", "concluido_em"])


def sanear_jobs_orfaos() -> int:
    return AnaliseJob.objects.filter(status="em_execucao").update(
        status="interrompida",
        concluido_em=timezone.now(),
        mensagem_erro=(
            "A análise foi interrompida porque o sistema foi reiniciado. Inicie novamente."
        ),
    )

