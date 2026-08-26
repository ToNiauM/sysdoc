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
from typing import Protocol

from sysdoc_dvi.prompts import montar_prompt
from sysdoc_dvi.provedores import RespostaModelo
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


SCHEMA_PARECER_EXECUTIVO = {
    "type": "object",
    "properties": {"parecer_executivo": {"type": "string"}},
    "required": ["parecer_executivo"],
}

SCHEMA_PARECER_DOCUMENTO = {
    "type": "object",
    "properties": {"parecer_documento": {"type": "string"}},
    "required": ["parecer_documento"],
}


class ErroSintese(Exception):
    """Parecer sintetizado não atingiu o mínimo de palavras após o retry único (RF6)."""


class AgenteSintese(Protocol):
    def chamar(self, alvo: str, prompt: str, *, schema: dict | None = None) -> RespostaModelo: ...


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


def _nota_integridade(itens: list[ResultadoItem]) -> str:
    total = len(itens)
    por_origem: dict[str, int] = {}
    for item in itens:
        por_origem[item.origem_verificacao] = por_origem.get(item.origem_verificacao, 0) + 1
    pendentes_falha = sum(
        1
        for item in itens
        if item.classificação == "pendente" and (item.falha_grounding or item.falha_estruturada)
    )
    partes_origem = ", ".join(
        f"{contagem} de origem {origem}" for origem, contagem in sorted(por_origem.items())
    )
    if not partes_origem:
        partes_origem = "nenhum item"
    return (
        f"Análise composta por {total} item(ns) do checklist ({partes_origem}). "
        f"{pendentes_falha} item(ns) ficaram pendentes por falha de grounding ou de estrutura "
        "na resposta do modelo."
    )


def _chamar_com_retry(
    agente: AgenteSintese,
    nome_template: str,
    contexto: dict,
    minimo: int,
    campo_resposta: str,
    schema: dict,
) -> tuple[str, list[UsoModelo]]:
    usos: list[UsoModelo] = []

    prompt = montar_prompt(nome_template, nota_retry=None, **contexto)
    resposta = agente.chamar(ALVO_SINTESE, prompt, schema=schema)
    usos.append(resposta.uso)
    texto = str(resposta.conteudo.get(campo_resposta, ""))
    contagem = word_count(texto)
    if contagem >= minimo:
        return texto, usos

    prompt_retry = montar_prompt(
        nome_template,
        nota_retry={"obtido": contagem, "minimo": minimo},
        **contexto,
    )
    resposta = agente.chamar(ALVO_SINTESE, prompt_retry, schema=schema)
    usos.append(resposta.uso)
    texto = str(resposta.conteudo.get(campo_resposta, ""))
    contagem = word_count(texto)
    if contagem < minimo:
        raise ErroSintese(
            f"{campo_resposta}: parecer sintetizado com {contagem} palavras após um retry; "
            f"mínimo exigido é {minimo}"
        )
    return texto, usos


def sintetizar(
    itens: list[ResultadoItem],
    projeto: dict,
    agente: AgenteSintese,
    numero_etp: str,
    numero_tr: str,
) -> Pareceres:
    itens_reduzidos = [_reduzir_item(item) for item in itens]
    uso_total: list[UsoModelo] = []

    parecer_executivo, uso_exec = _chamar_com_retry(
        agente,
        "sintese_executivo",
        {"projeto": projeto, "itens": itens_reduzidos},
        MINIMO_PALAVRAS_EXECUTIVO,
        "parecer_executivo",
        SCHEMA_PARECER_EXECUTIVO,
    )
    uso_total.extend(uso_exec)

    numeros = {"ETP": numero_etp, "TR": numero_tr}
    secoes: dict[str, dict] = {}
    for documento in DOCUMENTOS:
        itens_doc = [item for item in itens_reduzidos if item["documento"] == documento]
        parecer_documento, uso_doc = _chamar_com_retry(
            agente,
            "sintese_documento",
            {"projeto": projeto, "documento": documento, "itens": itens_doc},
            MINIMO_PALAVRAS_DOCUMENTO,
            "parecer_documento",
            SCHEMA_PARECER_DOCUMENTO,
        )
        uso_total.extend(uso_doc)
        secoes[documento] = {
            "classificação_documento": classificar_documento(itens, documento),
            "parecer_documento": parecer_documento,
            "numero": numeros[documento],
        }

    return Pareceres(
        parecer_executivo=parecer_executivo,
        secao_etp=secoes["ETP"],
        secao_tr=secoes["TR"],
        nota_integridade=_nota_integridade(itens),
        uso=uso_total,
    )
