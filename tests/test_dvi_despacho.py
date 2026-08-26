"""
Testes de sysdoc_dvi.despacho (RF4 — despacho por tipo de verificação; RF5 —
portão de grounding).

`AgenteFalso` substitui qualquer chamada de rede real: cada teste programa
as respostas por item explicitamente. Nenhum teste importa `requests`.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sysdoc_dvi.despacho import (  # noqa: E402
    SCHEMA_ITEM,
    SCHEMA_TABELA_PRECOS,
    SCHEMAS_POR_TIPO,
    executar_checklist,
    executar_item,
)
from sysdoc_dvi.tipos import ItemChecklist, ResultadoItem  # noqa: E402


def _item(
    id="DVI-GER-001",
    tipo="presenca",
    peca="ETP",
    aplicabilidade="geral",
    pergunta="O objeto está descrito?",
    base_legal_texto="Lei 14.133/2021, art. 18.",
    referencia="art. 18 da Lei 14.133/2021",
    severidade_default="média",
    modelo_alvo="economico",
    documento_saida="ETP",
    parametros=None,
):
    return ItemChecklist(
        id=id,
        aplicabilidade=aplicabilidade,
        peca=peca,
        documento_saida=documento_saida,
        tipo=tipo,
        pergunta=pergunta,
        base_legal_texto=base_legal_texto,
        referencia=referencia,
        severidade_default=severidade_default,
        modelo_alvo=modelo_alvo,
        ativo=True,
        parametros=parametros or {},
    )


class AgenteFalso:
    """Agente de teste: devolve respostas programadas por checklist_id."""

    def __init__(self, respostas: dict[str, ResultadoItem] | None = None):
        self._respostas = dict(respostas or {})
        self.chamadas: list[tuple[str, str]] = []

    def programar(self, checklist_id: str, resultado: ResultadoItem) -> None:
        self._respostas[checklist_id] = resultado

    def executar_item(self, item: ItemChecklist, contexto: str) -> ResultadoItem:
        self.chamadas.append((item.id, contexto))
        resposta = self._respostas.get(item.id)
        if isinstance(resposta, Exception):
            raise resposta
        if resposta is None:
            raise AssertionError(f"AgenteFalso: nenhuma resposta programada para '{item.id}'")
        return resposta

    def executar_lote(self, itens, contexto):
        return [self.executar_item(item, contexto) for item in itens]


def _resultado_llm(
    checklist_id="DVI-GER-001",
    documento="ETP",
    de="trecho literal do objeto",
    classificação="conforme",
    parecer="conforme",
    fundamento="",
    risco="informativo",
):
    return ResultadoItem(
        checklist_id=checklist_id,
        origem_verificacao="llm",
        documento=documento,
        seção="1",
        de=de,
        para="",
        parecer=parecer,
        fundamento=fundamento,
        classificação=classificação,
        severidade="média",
        risco_jurídico=risco,
    )


TEXTO_PECA = (
    "1. Objeto\n"
    "O objeto é a contratação de serviços continuados de limpeza predial em "
    "edifício público, incluindo fornecimento de materiais e equipamentos.\n"
    "2. Garantia\n"
    "O contratado apresentará garantia contratual no percentual de cinco por "
    "cento do valor do contrato, na forma da legislação vigente."
)


class TestSchemas:
    def test_schema_item_e_objeto(self):
        assert SCHEMA_ITEM["type"] == "object"

    def test_schema_tabela_precos_e_lista(self):
        assert SCHEMA_TABELA_PRECOS["type"] == "array"

    def test_schemas_por_tipo_cobre_presenca_julgamento_calculo(self):
        assert set(SCHEMAS_POR_TIPO) == {"presenca", "julgamento", "calculo"}


class TestRoteamento:
    def test_vigencia_nunca_toca_no_agente(self):
        item = _item(tipo="vigencia", pergunta="")
        textos = {"ETP": "Nenhuma norma citada aqui."}
        resultado = executar_item(item, textos, agente=None, tabela_vigencia={})
        assert resultado.classificação == "pendente"

    def test_presenca_chama_o_agente(self):
        item = _item(tipo="presenca")
        agente = AgenteFalso({item.id: _resultado_llm(de="O objeto é a contratação de serviços continuados de limpeza predial")})
        textos = {"ETP": TEXTO_PECA}
        resultado = executar_item(item, textos, agente, tabela_vigencia={})
        assert resultado.classificação == "conforme"
        assert len(agente.chamadas) == 1

    def test_peca_ausente_de_textos_produz_pendente(self):
        item = _item(tipo="presenca", peca="TR")
        resultado = executar_item(item, {"ETP": TEXTO_PECA}, agente=None, tabela_vigencia={})
        assert resultado.classificação == "pendente"


class TestGrounding:
    def test_de_fabricado_reclassifica_para_pendente(self):
        item = _item(tipo="presenca")
        agente = AgenteFalso({item.id: _resultado_llm(de="cláusula totalmente inexistente sobre prazo estendido")})
        resultado = executar_item(item, {"ETP": TEXTO_PECA}, agente, tabela_vigencia={})
        assert resultado.classificação == "pendente"
        assert resultado.falha_grounding is True


class TestCalculo:
    def _tabela_json(self):
        import json

        linhas = [
            {
                "descricao": "Item 1",
                "unidade": "unid",
                "quantidade": "5",
                "cotacoes": [
                    {"fonte": "Fornecedor A", "valor_unitario": "50.00"},
                    {"fonte": "Fornecedor B", "valor_unitario": "52.00"},
                    {"fonte": "Fornecedor C", "valor_unitario": "48.00"},
                ],
                "metodo_declarado": "media",
                "unitario_declarado": "60.00",
                "total_declarado": "250.00",
            }
        ]
        return json.dumps(linhas)

    def test_calculo_extrai_e_recalcula_localmente(self):
        item = _item(tipo="calculo", peca="MCP")
        resposta = ResultadoItem(
            checklist_id=item.id,
            origem_verificacao="llm",
            documento="ETP",
            seção="",
            de="",
            para=self._tabela_json(),
            parecer="",
            fundamento="",
            classificação="pendente",
            severidade="média",
            risco_jurídico="informativo",
        )
        agente = AgenteFalso({item.id: resposta})
        resultado = executar_item(item, {"MCP": "tabela de preços aqui"}, agente, tabela_vigencia={})
        assert resultado.origem_verificacao == "deterministico"
        assert resultado.classificação == "risco"
        assert "60.00" in resultado.parecer


class TestResiliencia:
    def test_erro_no_agente_nao_interrompe_o_laco(self):
        item1 = _item(id="DVI-GER-001", tipo="presenca")
        item2 = _item(id="DVI-GER-002", tipo="presenca")
        agente = AgenteFalso(
            {
                item1.id: RuntimeError("falha simulada de provedor"),
                item2.id: _resultado_llm(
                    checklist_id=item2.id,
                    de="O objeto é a contratação de serviços continuados de limpeza predial",
                ),
            }
        )
        resultados = executar_checklist([item1, item2], {"ETP": TEXTO_PECA}, agente, tabela_vigencia={})
        assert len(resultados) == 2
        assert resultados[0].classificação == "pendente"
        assert resultados[1].classificação == "conforme"


class TestCheckpointHook:
    def test_ao_concluir_chamado_uma_vez_por_item(self):
        item1 = _item(id="DVI-GER-001", tipo="presenca")
        item2 = _item(id="DVI-GER-002", tipo="vigencia", pergunta="")
        agente = AgenteFalso(
            {
                item1.id: _resultado_llm(
                    checklist_id=item1.id,
                    de="O objeto é a contratação de serviços continuados de limpeza predial",
                )
            }
        )
        concluidos = []
        executar_checklist(
            [item1, item2],
            {"ETP": TEXTO_PECA},
            agente,
            tabela_vigencia={},
            ao_concluir=concluidos.append,
        )
        assert len(concluidos) == 2
