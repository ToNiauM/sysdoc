"""
Agente de referência do protocolo `AnalysisAgent` (RF8).

`AgenteLLM` é o dono da escolha de template: resolve `item.tipo` via
`TEMPLATE_POR_TIPO` e sempre chama `montar_prompt` com o mesmo conjunto de
kwargs, cada template usando os que precisa. `item.tipo` fora do mapa
(`vigencia`, `mecanica`) nunca deveria chegar ao agente — vira
`ResultadoItem` `pendente` com `falha_estruturada` apontando o roteamento
indevido, sem exceção. Falha de provedor, mesmo após o retry embutido em
`provedores.chamar_modelo`, também nunca propaga (D-17): vira item
`pendente` com `falha_estruturada` preenchida.

Contrato de `tipo="calculo"` (ver docstring de `sysdoc_dvi.despacho`): a
resposta estruturada do provedor é uma lista de linhas
(`SCHEMA_TABELA_PRECOS`); o agente devolve essa lista serializada em JSON no
campo `para` do `ResultadoItem`, sem veredicto formado — a aritmética é
sempre refeita pelo despacho (`auditar_tabela_precos`).
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Callable

from sysdoc_dvi.config import ConfigDvi
from sysdoc_dvi.provedores import ErroProvedor, chamar_modelo
from sysdoc_dvi.tipos import ItemChecklist, ResultadoItem

TEMPLATE_POR_TIPO: dict[str, str] = {
    "presenca": "item_presenca",
    "julgamento": "item_julgamento",
    "calculo": "extracao_precos",
}

_INSTRUCAO_FIXA = (
    "Você é um agente de análise técnica e jurídica de documentos de licitação "
    "pública brasileira. Responda estritamente no formato solicitado, sem texto "
    "fora do JSON, fundamentando apenas na base legal fornecida."
)


def _montar_prompt_default(nome: str, **kwargs: object) -> str:
    from sysdoc_dvi.prompts import montar_prompt

    return montar_prompt(nome, **kwargs)


def _prefixo_cacheavel(item: ItemChecklist) -> str:
    return f"{_INSTRUCAO_FIXA}\n\n{item.base_legal_texto}"


def _resultado_pendente(item: ItemChecklist, falha_estruturada: str) -> ResultadoItem:
    return ResultadoItem(
        checklist_id=item.id,
        origem_verificacao="llm",
        documento=item.documento_saida,
        seção="",
        de="",
        para="",
        parecer="",
        fundamento="",
        classificação="pendente",
        severidade=item.severidade_default,
        risco_jurídico="informativo",
        falha_estruturada=falha_estruturada,
    )


class AgenteLLM:
    def __init__(
        self,
        config: ConfigDvi,
        montar_prompt: Callable[..., str] | None = None,
        schemas_por_tipo: dict[str, dict] | None = None,
    ) -> None:
        self._config = config
        self._montar_prompt = montar_prompt or _montar_prompt_default
        self._schemas_por_tipo = schemas_por_tipo or {}

    def executar_item(self, item: ItemChecklist, contexto: str) -> ResultadoItem:
        nome_template = TEMPLATE_POR_TIPO.get(item.tipo)
        if nome_template is None:
            return _resultado_pendente(
                item,
                f"item.tipo='{item.tipo}' não é resolvido pelo AgenteLLM (roteamento indevido: "
                "vigencia/mecanica são verificações determinísticas do despacho)",
            )

        alvo = self._config.economico if item.modelo_alvo == "economico" else self._config.forte
        prompt = self._montar_prompt(
            nome_template,
            pergunta=item.pergunta,
            peca=item.peca,
            trecho_peca=contexto,
            base_legal_texto=item.base_legal_texto,
            referencia=item.referencia,
        )
        schema = self._schemas_por_tipo.get(item.tipo)

        try:
            resposta = chamar_modelo(
                alvo,
                prompt,
                schema=schema,
                timeout_s=self._config.timeout_s,
                prefixo_cacheavel=_prefixo_cacheavel(item),
                max_retries=self._config.max_retries,
            )
        except ErroProvedor as exc:
            return _resultado_pendente(item, str(exc))

        conteudo = resposta.conteudo

        if item.tipo == "calculo":
            if isinstance(conteudo, list):
                linhas = conteudo
            elif isinstance(conteudo, dict) and isinstance(conteudo.get("linhas"), list):
                linhas = conteudo["linhas"]
            else:
                return replace(
                    _resultado_pendente(
                        item,
                        "extração de preços devolveu conteúdo estruturado que não é uma "
                        f"lista de linhas (tipo recebido: {type(conteudo).__name__})",
                    ),
                    uso=resposta.uso,
                )
            return ResultadoItem(
                checklist_id=item.id,
                origem_verificacao="llm",
                documento=item.documento_saida,
                seção="",
                de="",
                para=json.dumps(linhas, ensure_ascii=False),
                parecer="",
                fundamento="",
                classificação="pendente",
                severidade=item.severidade_default,
                risco_jurídico="informativo",
                uso=resposta.uso,
            )

        return ResultadoItem(
            checklist_id=item.id,
            origem_verificacao="llm",
            documento=item.documento_saida,
            seção=conteudo.get("seção", ""),
            de=conteudo.get("de", ""),
            para=conteudo.get("para", ""),
            parecer=conteudo.get("parecer", ""),
            fundamento=conteudo.get("fundamento", ""),
            classificação=conteudo.get("classificação", "pendente"),
            severidade=conteudo.get("severidade", item.severidade_default),
            risco_jurídico=conteudo.get("risco_jurídico", "informativo"),
            uso=resposta.uso,
        )

    def executar_lote(self, itens: list[ItemChecklist], contexto: str) -> list[ResultadoItem]:
        return [self.executar_item(item, contexto) for item in itens]
