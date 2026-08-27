"""
Testes de `sysdoc_docx/corpo_dvi.py` — builder do corpo de apontamentos do
Despacho de Verificação Inicial (DVI). Cobre D-03 a D-08 do CONTEXT.md da
fase 6: filtro de classificação, seções dinâmicas por peça, seção de
pendências, texto da alínea (sem o campo `para`), referência cruzada e,
principalmente, a segurança do escape de XML.
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sysdoc_docx.corpo_dvi import (  # noqa: E402
    TEXTO_SEM_APONTAMENTOS,
    TITULO_PENDENCIAS,
    build_corpo_despacho_xml,
    montar_apontamentos,
)

PROCESSO_TESTE_JSON = ROOT / "processo-teste" / "dados_consolidados.json"


def _item(**overrides) -> dict:
    item = {
        "id": "ETP-001",
        "número": 1,
        "item": "Item de teste",
        "documento": "ETP",
        "seção": "4.20",
        "de": "texto original",
        "para": "texto revisado",
        "parecer": "Parecer de teste",
        "fundamento": "Fundamento de teste",
        "classificação": "ajuste_necessário",
        "severidade": "média",
        "risco_jurídico": "relevante",
        "status_delic": None,
        "alterado_pelo_jurídico": False,
    }
    item.update(overrides)
    return item


def _dados(itens, **overrides) -> dict:
    dados = {
        "secao_etp": {
            "classificação_documento": "aprovado_com_ressalvas",
            "parecer_documento": "Parecer da seção ETP.",
            "numero": "não informado",
        },
        "secao_tr": {
            "classificação_documento": "aprovado",
            "parecer_documento": "Parecer da seção TR.",
            "numero": "não informado",
        },
        "itens": itens,
    }
    dados.update(overrides)
    return dados


def _contar_paragrafos(xml: str) -> int:
    return xml.count('<w:pPr><w:pStyle w:val="')


class TestFiltroDeClassificacao:
    def test_conforme_nunca_entra(self):
        conforme = _item(id="ETP-001", classificação="conforme", parecer="Parecer conforme")
        ajuste = _item(id="ETP-002", classificação="ajuste_necessário", parecer="Parecer ajuste")
        xml = build_corpo_despacho_xml(_dados([conforme, ajuste]))
        assert "Parecer conforme" not in xml
        assert "Parecer ajuste" in xml

    def test_apenas_ajuste_e_risco_no_corpo(self):
        ajuste = _item(id="ETP-001", classificação="ajuste_necessário", parecer="Ajuste")
        risco = _item(id="ETP-002", classificação="risco", parecer="Risco")
        pendente = _item(id="ETP-003", classificação="pendente", parecer="Pendente aqui")
        secoes = montar_apontamentos(_dados([ajuste, risco, pendente]))
        secao_peca = secoes[0]
        assert len(secao_peca["alineas"]) == 2
        textos = " ".join(a["texto"] for a in secao_peca["alineas"])
        assert "Pendente aqui" not in textos

    def test_sem_apontamentos_devolve_paragrafo_unico(self):
        conforme = _item(id="ETP-001", classificação="conforme", parecer="Parecer conforme")
        xml = build_corpo_despacho_xml(_dados([conforme]))
        assert TEXTO_SEM_APONTAMENTOS in xml
        assert "{{" not in xml


class TestSecoesDinamicas:
    def test_peca_sem_apontamento_nao_aparece(self):
        tr_item = _item(id="TR-001", documento="TR", classificação="risco", parecer="Risco TR")
        secoes = montar_apontamentos(_dados([tr_item]))
        assert len(secoes) == 1
        assert secoes[0]["numero"] == 1
        assert "TERMO DE REFERÊNCIA - TR" in secoes[0]["titulo"]

    def test_ordem_canonica_etp_antes_de_tr(self):
        tr_item = _item(id="TR-001", documento="TR", classificação="risco", parecer="Risco TR")
        etp_item = _item(id="ETP-001", documento="ETP", classificação="risco", parecer="Risco ETP")
        secoes = montar_apontamentos(_dados([tr_item, etp_item]))
        assert secoes[0]["numero"] == 1
        assert "ESTUDO TÉCNICO PRELIMINAR - ETP" in secoes[0]["titulo"]
        assert secoes[1]["numero"] == 2
        assert "TERMO DE REFERÊNCIA - TR" in secoes[1]["titulo"]

    def test_ordem_das_alineas_segue_o_array(self):
        itens = [
            _item(id="ETP-001", severidade="baixa", parecer="Parecer baixa"),
            _item(id="ETP-002", severidade="crítica", parecer="Parecer crítica"),
            _item(id="ETP-003", severidade="média", parecer="Parecer média"),
        ]
        secoes = montar_apontamentos(_dados(itens))
        alineas = secoes[0]["alineas"]
        assert [a["letra"] for a in alineas] == ["a", "b", "c"]
        assert "Parecer baixa" in alineas[0]["texto"]
        assert "Parecer crítica" in alineas[1]["texto"]
        assert "Parecer média" in alineas[2]["texto"]

    def test_sei_no_cabecalho_quando_numero_informado(self):
        item = _item(id="ETP-001")
        dados = _dados([item], secao_etp={
            "classificação_documento": "aprovado",
            "parecer_documento": "Parecer",
            "numero": "1343011",
        })
        secoes = montar_apontamentos(dados)
        assert secoes[0]["titulo"] == "1) ESTUDO TÉCNICO PRELIMINAR - ETP (SEI 1343011)"

    def test_sei_omitido_quando_nao_informado(self):
        item = _item(id="ETP-001")
        dados = _dados([item], secao_etp={
            "classificação_documento": "aprovado",
            "parecer_documento": "Parecer",
            "numero": "não informado",
        })
        secoes = montar_apontamentos(dados)
        assert "(SEI" not in secoes[0]["titulo"]


class TestPendencias:
    def test_pendencias_viram_secao_propria_ao_final(self):
        etp = _item(id="ETP-001", documento="ETP", parecer="Ajuste ETP")
        tr = _item(id="TR-001", documento="TR", parecer="Ajuste TR")
        pendente = _item(id="TR-002", documento="TR", classificação="pendente", parecer="Falta doc")
        secoes = montar_apontamentos(_dados([etp, tr, pendente]))
        assert secoes[-1]["titulo"] == TITULO_PENDENCIAS
        assert secoes[-1]["numero"] == max(s["numero"] for s in secoes)

    def test_sem_pendencias_nao_cria_secao(self):
        etp = _item(id="ETP-001", parecer="Ajuste ETP")
        secoes = montar_apontamentos(_dados([etp]))
        titulos = [s["titulo"] for s in secoes]
        assert TITULO_PENDENCIAS not in titulos

    def test_pendencia_nao_vira_referencia_cruzada(self):
        pendente_etp = _item(
            id="ETP-001", documento="ETP", classificação="pendente",
            parecer="Falta o mesmo documento", fundamento="Fundamento comum",
        )
        pendente_tr = _item(
            id="TR-001", documento="TR", classificação="pendente",
            parecer="Falta o mesmo documento", fundamento="Fundamento comum",
        )
        xml = build_corpo_despacho_xml(_dados([pendente_etp, pendente_tr]))
        assert "Vide apontamento" not in xml
        assert xml.count("Falta o mesmo documento") == 2


class TestTextoDaAlinea:
    def test_alinea_concatena_parecer_e_fundamento(self):
        item = _item(parecer="PARECER-X", fundamento="FUNDAMENTO-Y")
        secoes = montar_apontamentos(_dados([item]))
        texto = secoes[0]["alineas"][0]["texto"]
        assert texto.index("PARECER-X") < texto.index("FUNDAMENTO-Y")

    def test_campo_para_nunca_aparece(self):
        item = _item(para="REDACAO_SUGERIDA_SENTINELA")
        xml = build_corpo_despacho_xml(_dados([item]))
        assert "REDACAO_SUGERIDA_SENTINELA" not in xml

    def test_prefixo_de_secao(self):
        item = _item(seção="4.20")
        secoes = montar_apontamentos(_dados([item]))
        assert secoes[0]["alineas"][0]["texto"].startswith("4.20: ")

    def test_secao_vazia_nao_gera_prefixo(self):
        item = _item(seção="")
        secoes = montar_apontamentos(_dados([item]))
        assert not secoes[0]["alineas"][0]["texto"].startswith(": ")


class TestReferenciaCruzada:
    def test_repetido_entre_pecas_vira_referencia(self):
        etp = _item(id="ETP-001", documento="ETP", parecer="Parecer repetido", fundamento="F1")
        tr = _item(id="TR-001", documento="TR", parecer="Parecer repetido", fundamento="F2", seção="")
        secoes = montar_apontamentos(_dados([etp, tr]))
        texto_tr = secoes[1]["alineas"][0]["texto"]
        assert texto_tr == 'Vide apontamento constante na alínea "a" do item 1 do presente documento.'

    def test_referencia_aponta_para_a_letra_correta(self):
        etp_itens = [
            _item(id="ETP-001", documento="ETP", parecer="Parecer A"),
            _item(id="ETP-002", documento="ETP", parecer="Parecer B"),
            _item(id="ETP-003", documento="ETP", parecer="Parecer repetido"),
        ]
        tr_item = _item(id="TR-001", documento="TR", parecer="Parecer repetido", seção="")
        secoes = montar_apontamentos(_dados(etp_itens + [tr_item]))
        texto_tr = secoes[1]["alineas"][0]["texto"]
        assert 'alínea "c"' in texto_tr
        assert "item 1" in texto_tr

    def test_equivalencia_ignora_espacamento_e_caixa(self):
        etp = _item(id="ETP-001", documento="ETP", parecer="Parecer  Repetido   Aqui")
        tr = _item(id="TR-001", documento="TR", parecer="parecer repetido aqui", seção="")
        secoes = montar_apontamentos(_dados([etp, tr]))
        texto_tr = secoes[1]["alineas"][0]["texto"]
        assert "Vide apontamento" in texto_tr

    def test_pareceres_diferentes_nao_cruzam(self):
        etp = _item(id="ETP-001", documento="ETP", parecer="Parecer completamente distinto A")
        tr = _item(id="TR-001", documento="TR", parecer="Parecer completamente distinto B")
        xml = build_corpo_despacho_xml(_dados([etp, tr]))
        assert "Vide apontamento" not in xml


class TestSegurancaXml:
    def test_payload_de_tag_e_escapado(self):
        payload = "</w:t></w:r></w:p><w:p><w:r><w:t>INJETADO"
        item = _item(parecer=payload, fundamento="Fundamento normal")
        xml = build_corpo_despacho_xml(_dados([item]))
        assert "&lt;/w:t&gt;" in xml
        assert "<w:p><w:r><w:t>INJETADO" not in xml
        assert _contar_paragrafos(xml) == 2

    def test_ampersand_e_cdata_escapados(self):
        item = _item(parecer="A & B ]]> fim", fundamento="")
        xml = build_corpo_despacho_xml(_dados([item]))
        assert "&amp;" in xml
        assert "A & B" not in xml
        assert "fim" in xml

    def test_xml_gerado_e_bem_formado(self):
        tag_payload = _item(
            id="ETP-001", parecer="</w:t></w:r></w:p><w:p><w:r><w:t>INJETADO", fundamento="F"
        )
        amp_payload = _item(
            id="ETP-002", parecer="A & B ]]> fim", fundamento="<script>ainda mais</script>"
        )
        xml = build_corpo_despacho_xml(_dados([tag_payload, amp_payload]))
        envelope = (
            '<w:body xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"{xml}</w:body>"
        )
        ET.fromstring(envelope)

    def test_seção_e_fundamento_tambem_escapados(self):
        item = _item(seção="<script>alt</script>", fundamento="<script>fund</script>")
        xml = build_corpo_despacho_xml(_dados([item]))
        assert "&lt;script&gt;" in xml
        assert "<script>alt</script>" not in xml
        assert "<script>fund</script>" not in xml


@pytest.mark.skipif(not PROCESSO_TESTE_JSON.is_file(), reason="projeto processo-teste ausente")
class TestIntegracaoProcessoTeste:
    @staticmethod
    def _carregar():
        return json.loads(PROCESSO_TESTE_JSON.read_text(encoding="utf-8"))

    def test_contagem_de_secoes_no_dataset_real(self):
        dados = self._carregar()
        secoes = montar_apontamentos(dados)
        assert [len(s["alineas"]) for s in secoes] == [5, 6, 14]

    def test_duas_referencias_cruzadas_no_dataset_real(self):
        dados = self._carregar()
        xml = build_corpo_despacho_xml(dados)
        assert xml.count("Vide apontamento constante na alínea") == 2

    def test_nenhum_conforme_no_dataset_real(self):
        dados = self._carregar()
        xml = build_corpo_despacho_xml(dados)
        for item in dados["itens"]:
            if item["classificação"] != "conforme":
                continue
            trecho = escape(str(item["parecer"]).strip())[:60]
            if trecho:
                assert trecho not in xml
