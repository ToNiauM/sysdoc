"""
Suíte de segurança do canal `raw_xml` de `render_docx_template` (D-09,
06-CONTEXT.md). Prova, de forma autocontida — sem depender de `create()`
nem de código de outra wave —, que o XML cru só entra pelo parâmetro
`raw_xml`, estruturalmente separado do dicionário `values` derivado do
JSON, e que uma chave de `values` homônima à allowlist `RAW_XML_KEYS`
nunca alcança o canal cru.
"""

from __future__ import annotations

import inspect
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import sysdoc  # noqa: E402


def _template_com_hospedeiro(path: Path, chave: str = "corpo_apontamentos_xml") -> None:
    """Escreve um DOCX sintético com um parágrafo `{{parecer}}` e um
    parágrafo hospedeiro cujo único `<w:t>` é `{{chave}}`."""
    document_xml = (
        "<w:document><w:body>"
        "<w:p><w:r><w:t>{{parecer}}</w:t></w:r></w:p>"
        f"<w:p><w:r><w:t>{{{{{chave}}}}}</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types></Types>")
        zf.writestr("word/document.xml", document_xml)


class TestCanalSeparado:
    """O coração do threat model (D-09, T-06-04-02)."""

    def test_chave_homonima_no_values_sai_escapada(self, tmp_path):
        template = tmp_path / "tpl.docx"
        _template_com_hospedeiro(template)
        dados = {"corpo_apontamentos_xml": "<w:p><w:r><w:t>DO_JSON</w:t></w:r></w:p>"}
        values = sysdoc.flatten_json(dados)
        values["parecer"] = "x"

        saida = tmp_path / "saida.docx"
        sysdoc.render_docx_template(template, saida, values)

        xml = zipfile.ZipFile(saida).read("word/document.xml").decode()
        assert "<w:t>DO_JSON</w:t>" not in xml
        assert "&lt;w:p&gt;" in xml

    def test_chave_homonima_no_values_perde_para_o_canal_raw(self, tmp_path):
        template = tmp_path / "tpl.docx"
        _template_com_hospedeiro(template)
        dados = {"corpo_apontamentos_xml": "<w:p><w:r><w:t>DO_JSON</w:t></w:r></w:p>"}
        values = sysdoc.flatten_json(dados)
        values["parecer"] = "x"
        raw_xml = {"corpo_apontamentos_xml": "<w:p><w:r><w:t>DO_BUILDER</w:t></w:r></w:p>"}

        saida = tmp_path / "saida.docx"
        sysdoc.render_docx_template(template, saida, values, raw_xml=raw_xml)

        xml = zipfile.ZipFile(saida).read("word/document.xml").decode()
        assert "<w:t>DO_BUILDER</w:t>" in xml
        assert "DO_JSON" not in xml

    def test_values_nunca_e_fonte_de_chave_crua(self):
        parametros = inspect.signature(sysdoc.render_docx_template).parameters
        assert "raw_xml" in parametros
        assert parametros["raw_xml"].default is None

        # Invariante estrutural que fecha o vetor homônimo: a montagem de
        # `replacements` a partir de `values` não pode, em hipótese
        # alguma, consultar RAW_XML_KEYS. A allowlist só é consultada
        # dentro de `_validar_chave_raw`, nunca no corpo desta função.
        fonte = inspect.getsource(sysdoc.render_docx_template)
        assert "RAW_XML_KEYS" not in fonte

    def test_assinatura_posicional_de_tres_argumentos_preservada(self, tmp_path):
        template = tmp_path / "tpl.docx"
        _template_com_hospedeiro(template)
        saida = tmp_path / "saida.docx"
        sysdoc.render_docx_template(template, saida, {"parecer": "x"})
        xml = zipfile.ZipFile(saida).read("word/document.xml").decode()
        assert ">x<" in xml


class TestAllowlist:
    def test_chave_da_allowlist_injeta_xml_cru(self, tmp_path):
        template = tmp_path / "tpl.docx"
        _template_com_hospedeiro(template)
        saida = tmp_path / "saida.docx"
        sysdoc.render_docx_template(
            template,
            saida,
            {"parecer": "x"},
            raw_xml={"corpo_apontamentos_xml": "<w:p><w:r><w:t>INJETADO_OK</w:t></w:r></w:p>"},
        )
        xml = zipfile.ZipFile(saida).read("word/document.xml").decode()
        assert "<w:t>INJETADO_OK</w:t>" in xml

    def test_chave_fora_da_allowlist_no_raw_xml_levanta_systemexit(self, tmp_path):
        template = tmp_path / "tpl.docx"
        _template_com_hospedeiro(template, chave="malicioso_xml")
        saida = tmp_path / "saida.docx"
        with pytest.raises(SystemExit, match="malicioso_xml"):
            sysdoc.render_docx_template(
                template, saida, {"parecer": "x"}, raw_xml={"malicioso_xml": "<w:p/>"}
            )

    def test_chave_sem_sufixo_no_raw_xml_levanta_systemexit(self, tmp_path):
        template = tmp_path / "tpl.docx"
        _template_com_hospedeiro(template)
        saida = tmp_path / "saida.docx"
        with pytest.raises(SystemExit):
            sysdoc.render_docx_template(
                template, saida, {"parecer": "x"}, raw_xml={"corpo": "<w:p/>"}
            )

    def test_toda_chave_da_allowlist_tem_o_sufixo(self):
        for chave in sysdoc.RAW_XML_KEYS:
            assert chave.endswith(sysdoc.RAW_XML_SUFFIX)

    def test_allowlist_tem_exatamente_uma_chave(self):
        assert sysdoc.RAW_XML_KEYS == {"corpo_apontamentos_xml"}


class TestEscapeDeCamposDoJson:
    def test_payload_de_fechamento_de_tag_em_campo_do_json(self, tmp_path):
        template = tmp_path / "tpl.docx"
        _template_com_hospedeiro(template)
        saida = tmp_path / "saida.docx"
        values = {
            "parecer": "</w:t></w:r></w:p><w:p><w:r><w:t>INJETADO_MAU",
            "corpo_apontamentos_xml": "",
        }
        sysdoc.render_docx_template(template, saida, values)
        xml = zipfile.ZipFile(saida).read("word/document.xml").decode()
        assert "&lt;/w:t&gt;" in xml
        assert "<w:t>INJETADO_MAU" not in xml

    def test_ampersand_e_cdata_em_campo_do_json(self, tmp_path):
        template = tmp_path / "tpl.docx"
        _template_com_hospedeiro(template)
        saida = tmp_path / "saida.docx"
        values = {"parecer": "A & B ]]> <fim>", "corpo_apontamentos_xml": ""}
        sysdoc.render_docx_template(template, saida, values)
        xml = zipfile.ZipFile(saida).read("word/document.xml").decode()
        assert "&amp;" in xml
        assert "&lt;fim&gt;" in xml

    def test_saida_e_xml_bem_formado_com_payload(self, tmp_path):
        template = tmp_path / "tpl.docx"
        _template_com_hospedeiro(template)
        saida = tmp_path / "saida.docx"
        values = {
            "parecer": "</w:t></w:r></w:p><w:p><w:r><w:t>INJETADO_MAU & ]]> <fim>",
            "corpo_apontamentos_xml": "",
        }
        sysdoc.render_docx_template(template, saida, values)
        xml = zipfile.ZipFile(saida).read("word/document.xml").decode()
        # O documento sintético não declara o namespace `w:` no root (não é
        # necessário para testar a substituição de placeholder); injeta a
        # declaração só para o parse confirmar boa formação da árvore XML.
        xml_com_namespace = xml.replace(
            "<w:document>",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
            1,
        )
        ElementTree.fromstring(xml_com_namespace)


class TestValidacaoDoXmlBruto:
    def test_xml_malformado_levanta_systemexit(self, tmp_path):
        template = tmp_path / "tpl.docx"
        _template_com_hospedeiro(template)
        saida = tmp_path / "saida.docx"
        with pytest.raises(SystemExit, match="corpo_apontamentos_xml"):
            sysdoc.render_docx_template(
                template,
                saida,
                {"parecer": "x"},
                raw_xml={"corpo_apontamentos_xml": "<w:p><w:r>"},
            )

    def test_falha_nao_deixa_arquivo_de_saida(self, tmp_path):
        template = tmp_path / "tpl.docx"
        _template_com_hospedeiro(template)
        saida = tmp_path / "saida.docx"
        with pytest.raises(SystemExit):
            sysdoc.render_docx_template(
                template,
                saida,
                {"parecer": "x"},
                raw_xml={"corpo_apontamentos_xml": "<w:p><w:r>"},
            )
        assert not saida.exists()

    def test_placeholder_nao_isolado_levanta_systemexit(self, tmp_path):
        template = tmp_path / "tpl.docx"
        template.parent.mkdir(parents=True, exist_ok=True)
        document_xml = (
            "<w:document><w:body>"
            "<w:p><w:r><w:t>texto {{corpo_apontamentos_xml}} texto</w:t></w:r></w:p>"
            "</w:body></w:document>"
        )
        with zipfile.ZipFile(template, "w") as zf:
            zf.writestr("[Content_Types].xml", "<Types></Types>")
            zf.writestr("word/document.xml", document_xml)
        saida = tmp_path / "saida.docx"
        with pytest.raises(SystemExit, match="parágrafo hospedeiro"):
            sysdoc.render_docx_template(
                template,
                saida,
                {},
                raw_xml={"corpo_apontamentos_xml": "<w:p/>"},
            )

    def test_valor_raw_vazio_nao_deixa_placeholder_orfao(self, tmp_path):
        template = tmp_path / "tpl.docx"
        _template_com_hospedeiro(template)
        saida = tmp_path / "saida.docx"
        sysdoc.render_docx_template(
            template, saida, {"parecer": "x"}, raw_xml={"corpo_apontamentos_xml": ""}
        )
        xml = zipfile.ZipFile(saida).read("word/document.xml").decode()
        assert "{{" not in xml


class TestNaoRegressao:
    def test_fluxo_sem_raw_xml_inalterado(self, tmp_path):
        template = tmp_path / "tpl.docx"
        document_xml = "<w:document><w:body><w:p><w:r><w:t>{{parecer}}</w:t></w:r></w:p></w:body></w:document>"
        with zipfile.ZipFile(template, "w") as zf:
            zf.writestr("[Content_Types].xml", "<Types></Types>")
            zf.writestr("word/document.xml", document_xml)
        saida = tmp_path / "saida.docx"
        sysdoc.render_docx_template(template, saida, {"parecer": "linha1\nlinha2"})
        xml = zipfile.ZipFile(saida).read("word/document.xml").decode()
        assert "linha1<w:br/>linha2" in xml
        assert "{{" not in xml
