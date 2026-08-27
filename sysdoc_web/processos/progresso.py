"""
Tradução de `EventoProgresso` (sysdoc_dvi.progresso) para linguagem de
processo (D-16 — 07-CONTEXT.md). Nenhum jargão de máquina — "checklist",
"prompt", "provedor", "schema", "grounding" — aparece nos textos aqui.
"""

from __future__ import annotations

from sysdoc_dvi.progresso import EventoProgresso

ETAPA_PARA_TEXTO: dict[str, str] = {
    "config": "Preparando a verificação",
    "checklist": "Preparando a verificação",
    "prepare": "Lendo os documentos do processo",
    "pecas": "Identificando as peças do processo",
    "itens": "Analisando o processo",
    "sintese": "Consolidando os apontamentos",
    "montagem": "Conferindo os apontamentos",
    "validacao": "Conferindo os apontamentos",
    "render": "Montando o resultado",
    "relatorio": "Montando o resultado",
}

_ETAPA_PADRAO = "Analisando o processo"


def texto_da_etapa(evento: EventoProgresso) -> str:
    texto = ETAPA_PARA_TEXTO.get(evento.etapa, _ETAPA_PADRAO)
    if evento.atual is not None and evento.total is not None and evento.total > 0:
        texto = f"{texto} ({evento.atual} de {evento.total})"
    return texto
