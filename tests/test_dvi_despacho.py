"""
Testes de sysdoc_dvi.despacho (RF4 — despacho por tipo de verificação; RF5 —
portão de grounding).

`AgenteFalso` substitui qualquer chamada de rede real: cada teste programa
as respostas por item explicitamente. Nenhum teste importa `requests`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sysdoc_dvi.despacho import (  # noqa: E402
    LIMITE_CONTEXTO_PADRAO,
    SCHEMA_ITEM,
    SCHEMA_TABELA_PRECOS,
    SCHEMAS_POR_TIPO,
    executar_checklist,
    executar_item,
)
from sysdoc_dvi.tipos import ItemChecklist, ResultadoItem  # noqa: E402

FIXTURE_MCP_SINTETICO = ROOT / "tests" / "fixtures" / "mcp_sintetico.json"


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

    def test_julgamento_chama_o_agente(self):
        item = _item(tipo="julgamento")
        agente = AgenteFalso(
            {
                item.id: _resultado_llm(
                    de="O objeto é a contratação de serviços continuados de limpeza predial",
                    fundamento="art. 18 da Lei 14.133/2021",
                )
            }
        )
        resultado = executar_item(item, {"ETP": TEXTO_PECA}, agente, tabela_vigencia={})
        assert resultado.classificação == "conforme"
        assert len(agente.chamadas) == 1

    def test_mecanica_nunca_toca_no_agente_e_funciona_com_agente_none(self):
        item = _item(tipo="mecanica", parametros={"verificacao": "catalogo"})
        resultado = executar_item(
            item, {"ETP": "1. Objeto\nCATMAT 123456"}, agente=None, tabela_vigencia={}
        )
        assert resultado.origem_verificacao == "deterministico"
        assert resultado.classificação == "conforme"

    def test_tipo_que_exige_agente_sem_agente_vira_pendente(self):
        item = _item(tipo="julgamento")
        resultado = executar_item(item, {"ETP": TEXTO_PECA}, agente=None, tabela_vigencia={})
        assert resultado.classificação == "pendente"


class TestGrounding:
    def test_de_fabricado_reclassifica_para_pendente(self):
        item = _item(tipo="presenca")
        agente = AgenteFalso({item.id: _resultado_llm(de="cláusula totalmente inexistente sobre prazo estendido")})
        resultado = executar_item(item, {"ETP": TEXTO_PECA}, agente, tabela_vigencia={})
        assert resultado.classificação == "pendente"
        assert resultado.falha_grounding is True

    def test_de_fabricado_em_julgamento_tambem_reclassifica(self):
        item = _item(tipo="julgamento")
        agente = AgenteFalso(
            {item.id: _resultado_llm(de="dispositivo inventado que não existe na peça analisada")}
        )
        resultado = executar_item(item, {"ETP": TEXTO_PECA}, agente, tabela_vigencia={})
        assert resultado.classificação == "pendente"
        assert resultado.falha_grounding is True

    def test_de_ancorado_preserva_classificacao_original(self):
        item = _item(tipo="presenca")
        agente = AgenteFalso(
            {
                item.id: _resultado_llm(
                    de="O objeto é a contratação de serviços continuados de limpeza predial",
                    classificação="conforme",
                )
            }
        )
        resultado = executar_item(item, {"ETP": TEXTO_PECA}, agente, tabela_vigencia={})
        assert resultado.classificação == "conforme"
        assert resultado.falha_grounding is False


class TestFundamentacao:
    def test_citacao_fora_da_base_legal_vira_pendente(self):
        item = _item(
            tipo="julgamento",
            base_legal_texto="Lei 14.133/2021, art. 18.",
            referencia="art. 18 da Lei 14.133/2021",
        )
        agente = AgenteFalso(
            {
                item.id: _resultado_llm(
                    de="O objeto é a contratação de serviços continuados de limpeza predial",
                    classificação="risco",
                    risco="relevante",
                    fundamento="Acórdão 1234/2020 do TCU",
                )
            }
        )
        resultado = executar_item(item, {"ETP": TEXTO_PECA}, agente, tabela_vigencia={})
        assert resultado.classificação == "pendente"
        assert "fora da base legal" in resultado.parecer.lower()

    def test_citacao_dentro_da_base_legal_preserva_classificacao(self):
        item = _item(
            tipo="julgamento",
            base_legal_texto="Lei 14.133/2021, art. 18.",
            referencia="art. 18 da Lei 14.133/2021",
        )
        agente = AgenteFalso(
            {
                item.id: _resultado_llm(
                    de="O objeto é a contratação de serviços continuados de limpeza predial",
                    classificação="conforme",
                    fundamento="art. 18 da Lei 14.133/2021",
                )
            }
        )
        resultado = executar_item(item, {"ETP": TEXTO_PECA}, agente, tabela_vigencia={})
        assert resultado.classificação == "conforme"

    def test_fundamento_vazio_nao_e_penalizado(self):
        item = _item(tipo="presenca")
        agente = AgenteFalso(
            {
                item.id: _resultado_llm(
                    de="O objeto é a contratação de serviços continuados de limpeza predial",
                    fundamento="",
                )
            }
        )
        resultado = executar_item(item, {"ETP": TEXTO_PECA}, agente, tabela_vigencia={})
        assert resultado.classificação == "conforme"


class TestCalculo:
    def _tabela_json(self):
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

    def _resposta_fixture(self, checklist_id):
        dados = json.loads(FIXTURE_MCP_SINTETICO.read_text(encoding="utf-8"))
        return (
            ResultadoItem(
                checklist_id=checklist_id,
                origem_verificacao="llm",
                documento="ETP",
                seção="",
                de="",
                para=json.dumps(dados["linhas"]),
                parecer="",
                fundamento="",
                classificação="pendente",
                severidade="média",
                risco_jurídico="informativo",
            ),
            dados,
        )

    def test_erros_plantados_do_mcp_sintetico_aparecem_todos_na_memoria_de_calculo(self):
        item = _item(tipo="calculo", peca="MCP")
        resposta, dados = self._resposta_fixture(item.id)
        agente = AgenteFalso({item.id: resposta})
        resultado = executar_item(
            item, {"MCP": "anexo de pesquisa de preços sintético"}, agente, tabela_vigencia={}
        )
        assert resultado.classificação == "risco"
        assert resultado.origem_verificacao == "deterministico"
        for linha in dados["linhas"]:
            if linha["divergencia_esperada"] is not None:
                assert linha["descricao"] in resultado.parecer

    def test_linhas_de_controle_do_mcp_sintetico_nao_aparecem_como_divergencia(self):
        item = _item(tipo="calculo", peca="MCP")
        resposta, dados = self._resposta_fixture(item.id)
        agente = AgenteFalso({item.id: resposta})
        resultado = executar_item(
            item, {"MCP": "anexo de pesquisa de preços sintético"}, agente, tabela_vigencia={}
        )
        linha_de_divergencia = resultado.de
        for linha in dados["linhas"]:
            if linha["divergencia_esperada"] is None:
                assert linha["descricao"] not in linha_de_divergencia

    def test_tabela_extraida_malformada_vira_pendente_sem_excecao(self):
        item = _item(tipo="calculo", peca="MCP")
        resposta = ResultadoItem(
            checklist_id=item.id,
            origem_verificacao="llm",
            documento="ETP",
            seção="",
            de="",
            para="não é um JSON válido",
            parecer="",
            fundamento="",
            classificação="pendente",
            severidade="média",
            risco_jurídico="informativo",
        )
        agente = AgenteFalso({item.id: resposta})
        resultado = executar_item(item, {"MCP": "tabela"}, agente, tabela_vigencia={})
        assert resultado.classificação == "pendente"


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

    def test_parametro_mecanico_invalido_vira_pendente_sem_derrubar_o_laco(self):
        item1 = _item(id="DVI-GER-001", tipo="mecanica", parametros={"verificacao": "inexistente"})
        item2 = _item(id="DVI-GER-002", tipo="vigencia", pergunta="")
        resultados = executar_checklist(
            [item1, item2], {"ETP": TEXTO_PECA}, agente=None, tabela_vigencia={}
        )
        assert len(resultados) == 2
        assert resultados[0].classificação == "pendente"

    def test_excecao_inesperada_no_despacho_ainda_produz_pendente(self, monkeypatch):
        import sysdoc_dvi.despacho as despacho_mod

        def _levanta(*args, **kwargs):
            raise RuntimeError("falha interna inesperada")

        monkeypatch.setattr(despacho_mod, "_recortar_contexto", _levanta)
        item = _item(tipo="presenca")
        agente = AgenteFalso({item.id: _resultado_llm()})
        resultados = executar_checklist([item], {"ETP": TEXTO_PECA}, agente, tabela_vigencia={})
        assert len(resultados) == 1
        assert resultados[0].classificação == "pendente"


class TestContexto:
    def test_contexto_contem_apenas_a_peca_do_item(self):
        item = _item(tipo="presenca", peca="ETP")
        agente = AgenteFalso(
            {
                item.id: _resultado_llm(
                    de="O objeto é a contratação de serviços continuados de limpeza predial"
                )
            }
        )
        textos = {"ETP": TEXTO_PECA, "TR": "texto do TR que nunca deve aparecer no contexto do item"}
        executar_item(item, textos, agente, tabela_vigencia={})
        assert len(agente.chamadas) == 1
        _, contexto_recebido = agente.chamadas[0]
        assert "texto do TR" not in contexto_recebido
        assert "limpeza predial" in contexto_recebido

    def test_peca_grande_e_recortada_respeitando_o_limite(self):
        filler = "Disposição contratual genérica sobre execução do objeto. "
        texto_grande = filler * 5000
        alvo = "\nO objeto é a contratação de serviços continuados de limpeza predial.\n"
        meio = len(texto_grande) // 2
        texto_peca = texto_grande[:meio] + alvo + texto_grande[meio:]
        assert len(texto_peca) > LIMITE_CONTEXTO_PADRAO

        item = _item(tipo="presenca", peca="ETP", pergunta="limpeza predial contratação")
        agente = AgenteFalso(
            {
                item.id: _resultado_llm(
                    de="O objeto é a contratação de serviços continuados de limpeza predial"
                )
            }
        )
        resultado = executar_item(item, {"ETP": texto_peca}, agente, tabela_vigencia={})
        _, contexto_recebido = agente.chamadas[0]
        assert len(contexto_recebido) <= LIMITE_CONTEXTO_PADRAO
        assert "recortado" in resultado.parecer.lower()


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

    def test_ao_concluir_e_chamado_mesmo_quando_item_degrada_para_pendente(self):
        item = _item(id="DVI-GER-001", tipo="presenca")
        agente = AgenteFalso({item.id: RuntimeError("falha simulada")})
        concluidos = []
        executar_checklist(
            [item], {"ETP": TEXTO_PECA}, agente, tabela_vigencia={}, ao_concluir=concluidos.append
        )
        assert len(concluidos) == 1
        assert concluidos[0].classificação == "pendente"
