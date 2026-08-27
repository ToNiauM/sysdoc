"""
Testes de `templates/build_despacho_templates.py` — estabilidade byte a
byte, integridade dos estilos e contrato de placeholders dos templates de
Despacho de Verificação Inicial (P6 - 260827-p66, rodada 1).
"""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "templates"))

import build_despacho_templates  # noqa: E402

_ESTILOS_ESPERADOS = {
    "DviTitulo",
    "DviSubtitulo",
    "DviVocativo",
    "DviCorpo",
    "DviPecaTitulo",
    "DviAlinea",
}

_PLACEHOLDERS_ESPERADOS = {
    "{{projeto.processo}}",
    "{{projeto.objeto}}",
    "{{despacho.vocativo}}",
    "{{despacho.unidade}}",
    "{{despacho.destinatario}}",
    "{{despacho.signatario}}",
    "{{despacho.cargo_signatario}}",
    "{{despacho.autoridade}}",
    "{{despacho.cargo_autoridade}}",
    "{{corpo_apontamentos_xml}}",
}

_PLACEHOLDERS_FORMATO_RELATORIO = (
    "{{parecer_executivo}}",
    "{{tabela_itens}}",
    "{{nota_integridade}}",
    "{{secao_etp.parecer_documento}}",
    "{{secao_tr.parecer_documento}}",
    "{{total_itens}}",
)

_NORMA_IN_94 = "Instrução Normativa SGD/ME nº 94, de 23 de dezembro de 2022"

_NOMES_LITERAIS_DO_MODELO = (
    "Daniel Assunção Silva",
    "Eunice Rosa de Melo dos Santos",
    "Gerente do DELIC",
)


def _document_xml(caminho_docx: Path) -> str:
    return zipfile.ZipFile(caminho_docx).read("word/document.xml").decode()


def _styles_xml(caminho_docx: Path) -> str:
    return zipfile.ZipFile(caminho_docx).read("word/styles.xml").decode()


def _placeholders_no_xml(xml: str) -> set[str]:
    return set(re.findall(r"{{[^}]+}}", xml))


class TestGeracaoDeterministica:
    def test_construir_todas_cria_as_duas_variantes(self, tmp_path):
        caminhos = build_despacho_templates.construir_todas(tmp_path)
        nomes = {caminho.name for caminho in caminhos}
        assert nomes == {"despacho_geral.docx", "despacho_tic.docx"}
        for caminho in caminhos:
            assert caminho.is_file()

    def test_regeracao_e_byte_estavel(self, tmp_path):
        primeira = build_despacho_templates.construir_todas(tmp_path / "run1")
        segunda = build_despacho_templates.construir_todas(tmp_path / "run2")

        for caminho_1, caminho_2 in zip(sorted(primeira), sorted(segunda)):
            assert caminho_1.name == caminho_2.name
            assert caminho_1.read_bytes() == caminho_2.read_bytes()


class TestEstruturaDocx:
    def test_entradas_essenciais_do_zip(self, tmp_path):
        caminho = build_despacho_templates.construir("geral", tmp_path / "despacho_geral.docx")
        with zipfile.ZipFile(caminho) as zf:
            nomes = set(zf.namelist())
        esperadas = {
            "[Content_Types].xml",
            "_rels/.rels",
            "word/document.xml",
            "word/styles.xml",
            "word/_rels/document.xml.rels",
        }
        assert esperadas <= nomes

    def test_estilos_declarados(self, tmp_path):
        for variante in build_despacho_templates.VARIANTES:
            caminho = build_despacho_templates.construir(variante, tmp_path / f"{variante}.docx")
            styles = _styles_xml(caminho)
            for style_id in _ESTILOS_ESPERADOS:
                assert f'w:styleId="{style_id}"' in styles, (variante, style_id)

    def test_todo_pstyle_referencia_estilo_declarado(self, tmp_path):
        for variante in build_despacho_templates.VARIANTES:
            caminho = build_despacho_templates.construir(variante, tmp_path / f"{variante}.docx")
            documento = _document_xml(caminho)
            styles = _styles_xml(caminho)

            referenciados = set(re.findall(r'<w:pStyle w:val="([^"]+)"/>', documento))
            declarados = set(re.findall(r'w:styleId="([^"]+)"', styles))

            orfaos = referenciados - declarados
            assert not orfaos, f"{variante}: w:pStyle órfão(s) {orfaos}"


class TestPlaceholders:
    def test_placeholder_raw_unico_e_isolado(self, tmp_path):
        caminho = build_despacho_templates.construir("geral", tmp_path / "despacho_geral.docx")
        documento = _document_xml(caminho)

        ocorrencias = documento.count("{{corpo_apontamentos_xml}}")
        assert ocorrencias == 1

        paragrafos = re.findall(r"<w:p>.*?</w:p>", documento, flags=re.DOTALL)
        hospedeiro = [p for p in paragrafos if "{{corpo_apontamentos_xml}}" in p]
        assert len(hospedeiro) == 1

        textos = re.findall(r"<w:t[^>]*>(.*?)</w:t>", hospedeiro[0], flags=re.DOTALL)
        assert textos == ["{{corpo_apontamentos_xml}}"]

    def test_placeholders_esperados_presentes(self, tmp_path):
        caminho = build_despacho_templates.construir("geral", tmp_path / "despacho_geral.docx")
        documento = _document_xml(caminho)
        assert _placeholders_no_xml(documento) == _PLACEHOLDERS_ESPERADOS

    def test_sem_placeholders_do_formato_relatorio(self, tmp_path):
        for variante in build_despacho_templates.VARIANTES:
            caminho = build_despacho_templates.construir(variante, tmp_path / f"{variante}.docx")
            documento = _document_xml(caminho)
            for placeholder in _PLACEHOLDERS_FORMATO_RELATORIO:
                assert placeholder not in documento, (variante, placeholder)


class TestVariantes:
    def test_variante_tic_cita_in_94_e_geral_nao(self, tmp_path):
        geral = build_despacho_templates.construir("geral", tmp_path / "geral.docx")
        tic = build_despacho_templates.construir("tic", tmp_path / "tic.docx")

        assert _NORMA_IN_94 in _document_xml(tic)
        assert _NORMA_IN_94 not in _document_xml(geral)

    def test_moldura_reproduz_o_modelo_institucional(self, tmp_path):
        esperados = (
            "DESPACHO DE VERIFICAÇÃO INICIAL - dvi",
            "Observações:",
            "De acordo,",
            "faço as seguintes considerações:",
        )
        for variante in build_despacho_templates.VARIANTES:
            caminho = build_despacho_templates.construir(variante, tmp_path / f"{variante}.docx")
            documento = _document_xml(caminho)
            for trecho in esperados:
                assert trecho in documento, (variante, trecho)

    def test_nenhum_nome_ou_cargo_literal_do_modelo(self, tmp_path):
        for variante in build_despacho_templates.VARIANTES:
            caminho = build_despacho_templates.construir(variante, tmp_path / f"{variante}.docx")
            documento = _document_xml(caminho)
            for literal in _NOMES_LITERAIS_DO_MODELO:
                assert literal not in documento, (variante, literal)
