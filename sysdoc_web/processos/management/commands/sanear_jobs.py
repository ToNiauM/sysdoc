"""
Comando de saneamento de subida (D-15 — 07-CONTEXT.md).

Roda antes de servir a aplicação (entrypoint do container, plano 07-04):
qualquer `AnaliseJob` encontrado `em_execucao` na subida não tem worker vivo
por trás dele — o reinício aconteceu no meio da análise — e vira
`interrompida` com mensagem honesta, nunca "em andamento" para sempre.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from sysdoc_web.processos import fila


class Command(BaseCommand):
    help = "Marca como 'interrompida' qualquer análise que ficou 'em_execucao' antes do reinício."

    def handle(self, *args, **options):
        contagem = fila.sanear_jobs_orfaos()
        self.stdout.write(f"{contagem} análise(s) órfã(s) marcada(s) como interrompida(s).")
