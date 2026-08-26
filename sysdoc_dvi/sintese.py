"""
Síntese dedicada dos pareceres do motor DVI (RF6).

Uma chamada final ao modelo forte recebe exclusivamente os itens do
checklist já validados (campos estruturados e reduzidos, nunca o texto das
peças) e produz `parecer_executivo` e os dois `parecer_documento`
(ETP/TR). A classificação de documento (`classificação_documento`) é
calculada localmente por `classificar_documento` e nunca pedida ao
modelo — é a mitigação nº 4 do PRD: preserva os mínimos de palavras do
validador (450/120) sem induzir enchimento nos modelos econômicos que
executam os itens item a item (T-05-33, T-05-34, T-05-35).

`sintetizar` (Task 2) depende de um `agente` capaz de fazer uma chamada de
prompt livre no alvo `forte` (`AgenteSintese.chamar`). O protocolo
`AnalysisAgent` de `sysdoc_dvi.tipos` (frozen, não redefinido aqui) só
expressa chamadas por `ItemChecklist` (`executar_item`/`executar_lote`) e
não cobre esta chamada de síntese sem item de checklist associado.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sysdoc_dvi.tipos import ResultadoItem, UsoModelo

MINIMO_PALAVRAS_EXECUTIVO = 450
MINIMO_PALAVRAS_DOCUMENTO = 120

ALVO_SINTESE = "forte"

DOCUMENTOS = ("ETP", "TR")

_CAMPOS_REDUZIDOS = (
    "checklist_id",
    "documento",
    "seção",
    "classificação",
    "severidade",
    "risco_jurídico",
    "parecer",
)


class ErroSintese(Exception):
    """Parecer sintetizado não atingiu o mínimo de palavras após o retry único (RF6)."""


@dataclass(frozen=True)
class Pareceres:
    parecer_executivo: str
    secao_etp: dict
    secao_tr: dict
    nota_integridade: str
    uso: list[UsoModelo]


def word_count(text: object) -> int:
    return len(re.findall(r"\b\w+\b", str(text or ""), flags=re.UNICODE))


def classificar_documento(itens: list[ResultadoItem], documento: str) -> str:
    itens_doc = [item for item in itens if item.documento == documento]
    if any(item.risco_jurídico == "bloqueante" for item in itens_doc):
        return "reprovado"
    if any(item.classificação == "pendente" for item in itens_doc):
        return "pendente_de_complementação"
    if any(
        item.classificação == "ajuste_necessário"
        or (item.classificação == "risco" and item.risco_jurídico == "relevante")
        for item in itens_doc
    ):
        return "aprovado_com_ressalvas"
    return "aprovado"


def _reduzir_item(item: ResultadoItem) -> dict:
    return {campo: getattr(item, campo) for campo in _CAMPOS_REDUZIDOS}
