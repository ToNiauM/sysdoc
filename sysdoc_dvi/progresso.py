"""
Contrato de progresso estruturado do pipeline DVI (D-16, Plano 07-01).

`EventoProgresso` carrega só as strings que a CLI já imprime hoje — nenhum
alvo de modelo, chave de API ou prompt entra aqui (D-05/D-06). Este módulo
não importa Django nem `sysdoc`: é o contrato neutro entre `sysdoc_dvi.
pipeline.executar_run` e qualquer chamador (CLI, web, teste).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

ETAPAS = (
    "config",
    "checklist",
    "prepare",
    "pecas",
    "itens",
    "sintese",
    "montagem",
    "validacao",
    "render",
    "relatorio",
)


@dataclass(frozen=True)
class EventoProgresso:
    etapa: str
    mensagem: str
    atual: int | None = None
    total: int | None = None


SinkProgresso = Callable[[EventoProgresso], None]
