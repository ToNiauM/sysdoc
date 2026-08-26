"""
Despacho por tipo de verificação do motor DVI (RF4) — o ponto onde
checklist, peça, verificações determinísticas e agente de análise se
encontram. Sem este módulo, nenhum plano anterior (05-04 a 05-08) produz
um item de fato.

Este módulo NUNCA escolhe o template de prompt: para os tipos que exigem
modelo (`presenca`, `julgamento`, `calculo`) ele chama
`agente.executar_item(item, contexto)` e é o próprio agente quem resolve
qual template usar. O despacho é dono apenas dos schemas de saída
estruturada (`SCHEMA_ITEM`, `SCHEMA_TABELA_PRECOS`, publicados juntos em
`SCHEMAS_POR_TIPO`) e do portão de grounding (RF5) aplicado a todo
resultado de origem `llm`.

Contrato do agente para `tipo="calculo"`: como `AnalysisAgent.executar_item`
só pode devolver um `ResultadoItem`, e a extração de preços não deve trazer
nenhum veredicto formado pelo modelo, o agente devolve a lista de linhas
extraídas (mesmo formato de `SCHEMA_TABELA_PRECOS`) serializada em JSON no
campo `para`. `executar_item` decodifica esse JSON, converte cada linha em
`LinhaTabela` (plano 05-05) e substitui integralmente os campos do
resultado pelo output determinístico de `auditar_tabela_precos` — a
aritmética nunca vem do modelo (T-05-14).

Deviation from plan wording (documented in SUMMARY.md): as chaves de
`SCHEMA_ITEM` usam a acentuação canônica do schema SysDoc (não ASCII),
porque `sysdoc_dvi.agente.AgenteLLM.executar_item` (já mesclado, plano
05-08, não alterado aqui) lê o conteúdo estruturado do modelo diretamente
com essas chaves acentuadas — um `SCHEMA_ITEM` em ASCII quebraria essa
integração sem tradução, e nenhuma tradução existe hoje nesse ponto.
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from decimal import Decimal, InvalidOperation
from typing import Callable

from sysdoc_dvi.grounding import aplicar_grounding
from sysdoc_dvi.normas import _CITACAO_PATTERN, normalizar_citacao, verificar_item_vigencia
from sysdoc_dvi.tipos import AnalysisAgent, ItemChecklist, ResultadoItem
from sysdoc_dvi.verificacoes.calculo import (
    Cotacao,
    ErroTabelaPrecos,
    LinhaTabela,
    auditar_tabela_precos,
)
from sysdoc_dvi.verificacoes.mecanica import verificar_item_mecanico

LIMIAR_GROUNDING_PADRAO = 0.85
LIMITE_CONTEXTO_PADRAO = 120_000
_JANELA_CONTEXTO = 1500

SCHEMA_ITEM: dict = {
    "type": "object",
    "properties": {
        "seção": {"type": "string"},
        "de": {"type": "string"},
        "para": {"type": "string"},
        "parecer": {"type": "string"},
        "fundamento": {"type": "string"},
        "classificação": {
            "type": "string",
            "enum": ["conforme", "ajuste_necessário", "risco", "pendente"],
        },
        "severidade": {
            "type": "string",
            "enum": ["crítica", "alta", "média", "baixa", "informativa"],
        },
        "risco_jurídico": {
            "type": "string",
            "enum": ["bloqueante", "relevante", "menor", "informativo"],
        },
    },
    "required": [
        "seção",
        "de",
        "para",
        "parecer",
        "fundamento",
        "classificação",
        "severidade",
        "risco_jurídico",
    ],
    "additionalProperties": False,
}

SCHEMA_TABELA_PRECOS: dict = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "descricao": {"type": "string"},
            "unidade": {"type": "string"},
            "quantidade": {"type": "string"},
            "cotacoes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "fonte": {"type": "string"},
                        "valor_unitario": {"type": "string"},
                    },
                    "required": ["fonte", "valor_unitario"],
                    "additionalProperties": False,
                },
            },
            "metodo_declarado": {"type": "string", "enum": ["media", "mediana", "menor"]},
            "unitario_declarado": {"type": "string"},
            "total_declarado": {"type": "string"},
        },
        "required": [
            "descricao",
            "unidade",
            "quantidade",
            "cotacoes",
            "metodo_declarado",
            "unitario_declarado",
            "total_declarado",
        ],
        "additionalProperties": False,
    },
}

SCHEMAS_POR_TIPO: dict[str, dict] = {
    "presenca": SCHEMA_ITEM,
    "julgamento": SCHEMA_ITEM,
    "calculo": SCHEMA_TABELA_PRECOS,
}


def _pendente(item: ItemChecklist, motivo: str, origem: str = "deterministico") -> ResultadoItem:
    return ResultadoItem(
        checklist_id=item.id,
        origem_verificacao=origem,
        documento=item.documento_saida,
        seção="",
        de="",
        para="",
        parecer=motivo,
        fundamento="",
        classificação="pendente",
        severidade=item.severidade_default,
        risco_jurídico="informativo",
        falha_estruturada=motivo,
    )


def _extrair_termos_chave(pergunta: str) -> list[str]:
    termos = re.findall(r"[A-Za-zÀ-ÿ0-9]{4,}", pergunta or "")
    vistos: list[str] = []
    for termo in termos:
        baixo = termo.lower()
        if baixo not in vistos:
            vistos.append(baixo)
    return vistos


def _recortar_contexto(
    texto: str, pergunta: str, limite: int = LIMITE_CONTEXTO_PADRAO
) -> tuple[str, bool]:
    if len(texto) <= limite:
        return texto, False

    termos = _extrair_termos_chave(pergunta)
    texto_lower = texto.lower()
    janelas: list[tuple[int, int]] = []
    for termo in termos:
        for match in re.finditer(re.escape(termo), texto_lower):
            inicio = max(0, match.start() - _JANELA_CONTEXTO)
            fim = min(len(texto), match.end() + _JANELA_CONTEXTO)
            quebra_inicio = texto.rfind("\n", 0, inicio)
            inicio = quebra_inicio + 1 if quebra_inicio != -1 else 0
            quebra_fim = texto.find("\n", fim)
            fim = quebra_fim if quebra_fim != -1 else len(texto)
            janelas.append((inicio, fim))

    if not janelas:
        return texto[:limite], True

    janelas.sort()
    mescladas: list[list[int]] = []
    for inicio, fim in janelas:
        if mescladas and inicio <= mescladas[-1][1]:
            mescladas[-1][1] = max(mescladas[-1][1], fim)
        else:
            mescladas.append([inicio, fim])

    recorte = "\n[...]\n".join(texto[inicio:fim] for inicio, fim in mescladas)
    if len(recorte) > limite:
        recorte = recorte[:limite]
    return recorte, True


def _verificar_fundamentacao(resultado: ResultadoItem, item: ItemChecklist) -> ResultadoItem:
    if resultado.classificação == "pendente" or not resultado.fundamento:
        return resultado

    base_normalizada = normalizar_citacao(item.base_legal_texto)
    referencia_normalizada = normalizar_citacao(item.referencia)
    citacoes = [
        match.group(0).strip() for match in _CITACAO_PATTERN.finditer(resultado.fundamento)
    ]

    for citacao in citacoes:
        citacao_normalizada = normalizar_citacao(citacao)
        if citacao_normalizada and (
            citacao_normalizada in base_normalizada
            or citacao_normalizada in referencia_normalizada
        ):
            continue
        novo_parecer = (
            f"{resultado.parecer} [FUNDAMENTAÇÃO FORA DA BASE LEGAL: citação '{citacao}' não "
            "consta na base legal nem na referência deste item; item reclassificado "
            "como pendente]"
        ).strip()
        return replace(
            resultado,
            classificação="pendente",
            risco_jurídico="informativo",
            parecer=novo_parecer,
        )

    return resultado


def _construir_linha(bruto: dict) -> LinhaTabela:
    cotacoes = [
        Cotacao(fonte=str(cotacao["fonte"]), valor_unitario=Decimal(str(cotacao["valor_unitario"])))
        for cotacao in bruto["cotacoes"]
    ]
    return LinhaTabela(
        descricao=str(bruto["descricao"]),
        unidade=str(bruto["unidade"]),
        quantidade=Decimal(str(bruto["quantidade"])),
        cotacoes=cotacoes,
        metodo_declarado=str(bruto["metodo_declarado"]),
        unitario_declarado=Decimal(str(bruto["unitario_declarado"])),
        total_declarado=Decimal(str(bruto["total_declarado"])),
    )


def _executar_calculo(item: ItemChecklist, contexto: str, agente: AnalysisAgent) -> ResultadoItem:
    try:
        resultado_bruto = agente.executar_item(item, contexto)
    except Exception as exc:  # noqa: BLE001 - degradação obrigatória (T-05-32)
        return _pendente(item, f"falha ao chamar o agente para extração de preços: {exc}", origem="llm")

    try:
        linhas_brutas = json.loads(resultado_bruto.para or "[]")
        linhas = [_construir_linha(bruto) for bruto in linhas_brutas]
    except (json.JSONDecodeError, KeyError, InvalidOperation, TypeError, ValueError) as exc:
        return _pendente(
            item, f"falha ao interpretar a tabela de preços extraída pelo agente: {exc}", origem="llm"
        )

    try:
        resultado_calculo = auditar_tabela_precos(linhas)
    except ErroTabelaPrecos as exc:
        return _pendente(item, f"tabela de preços extraída é inválida: {exc}", origem="llm")

    if resultado_calculo.conforme:
        classificação = "conforme"
        risco_jurídico = "informativo"
        parecer = (
            "Tabela de preços conforme; nenhuma divergência aritmética identificada na "
            "auditoria determinística."
        )
    else:
        classificação = "risco"
        risco_jurídico = "relevante"
        parecer = (
            f"Auditoria determinística identificou {len(resultado_calculo.divergencias)} "
            f"divergência(s) aritmética(s). Memória de cálculo:\n{resultado_calculo.memoria_calculo}"
        )

    linhas_divergentes = "\n".join(
        divergencia.linha for divergencia in resultado_calculo.divergencias
    )

    return ResultadoItem(
        checklist_id=item.id,
        origem_verificacao="deterministico",
        documento=item.documento_saida,
        seção=item.peca,
        de=linhas_divergentes or "[OMISSÃO]",
        para="\n".join(str(divergencia.recalculado) for divergencia in resultado_calculo.divergencias),
        parecer=parecer,
        fundamento=(
            "Recálculo local em decimal.Decimal da tabela extraída "
            "(média, mediana, unitário × quantidade); ver memória de cálculo no parecer"
        ),
        classificação=classificação,
        severidade=item.severidade_default,
        risco_jurídico=risco_jurídico,
        uso=resultado_bruto.uso,
    )


def executar_item(
    item: ItemChecklist,
    textos: dict[str, str],
    agente: AnalysisAgent | None,
    tabela_vigencia: dict[str, dict],
    limiar_grounding: float = LIMIAR_GROUNDING_PADRAO,
) -> ResultadoItem:
    texto_peca = textos.get(item.peca)
    if texto_peca is None:
        return _pendente(
            item, f"peça '{item.peca}' não está disponível nos textos extraídos para este item"
        )

    if item.tipo == "vigencia":
        return verificar_item_vigencia(item, texto_peca, tabela_vigencia)

    if item.tipo == "mecanica":
        try:
            return verificar_item_mecanico(item, texto_peca)
        except ValueError as exc:
            return _pendente(item, str(exc))

    if item.tipo not in SCHEMAS_POR_TIPO:
        return _pendente(
            item, f"item.tipo='{item.tipo}' não corresponde a nenhum executor conhecido (erro de roteamento)"
        )

    if agente is None:
        return _pendente(
            item, f"item.tipo='{item.tipo}' requer agente de análise, mas nenhum agente foi fornecido", origem="llm"
        )

    contexto, recortado = _recortar_contexto(texto_peca, item.pergunta)

    if item.tipo == "calculo":
        resultado = _executar_calculo(item, contexto, agente)
    else:
        try:
            resultado = agente.executar_item(item, contexto)
        except Exception as exc:  # noqa: BLE001 - degradação obrigatória (T-05-32)
            return _pendente(item, f"falha ao chamar o agente: {exc}", origem="llm")

        if resultado.origem_verificacao == "llm":
            resultado = aplicar_grounding(resultado, texto_peca, limiar_grounding)
            resultado = _verificar_fundamentacao(resultado, item)

    if recortado and not resultado.falha_estruturada:
        resultado = replace(
            resultado,
            parecer=(
                f"{resultado.parecer} "
                f"[contexto recortado: peça excede {LIMITE_CONTEXTO_PADRAO} caracteres]"
            ).strip(),
        )

    return resultado


def executar_checklist(
    itens: list[ItemChecklist],
    textos: dict[str, str],
    agente: AnalysisAgent | None,
    tabela_vigencia: dict[str, dict],
    limiar_grounding: float = LIMIAR_GROUNDING_PADRAO,
    ao_concluir: Callable[[ResultadoItem], None] | None = None,
) -> list[ResultadoItem]:
    resultados: list[ResultadoItem] = []
    for item in itens:
        try:
            resultado = executar_item(item, textos, agente, tabela_vigencia, limiar_grounding)
        except Exception as exc:  # noqa: BLE001 - RF9/T-05-32: um item nunca derruba a análise inteira
            resultado = _pendente(item, f"falha inesperada ao executar item: {exc}")
        resultados.append(resultado)
        if ao_concluir is not None:
            ao_concluir(resultado)
    return resultados
