"""
E2E do despacho DVI sobre `processo-teste/` — o processo real de 49 itens
(24 `conforme`, 14 `pendente`, 7 `ajuste_necessário`, 4 `risco`), medido no
planejamento da fase (`06-CONTEXT.md`). Prova o critério de sucesso 5 da
Rodada 1: `sysdoc create <pasta> dvi` produz o despacho, nas duas variantes,
sem nenhum `{{` remanescente — cobrindo as duas variantes (`geral`/`tic`,
D-13), o override de template do projeto (D-14) e a exclusão de itens
`conforme` do corpo (D-03), no processo real, não em fixture sintética
(que já é coberta por `tests/test_dvi_create_variante.py`, Plano 05).

Isolamento (T-06-06-01): todo teste roda sobre uma cópia de `processo-teste`
em `tmp_path` (`shutil.copytree`, ignorando `output/`, `.sysdoc/cache/` e
qualquer `.docx` já gerado — inclusive `referencias/dvi.docx`, que hoje é
um DOCX no formato relatório legado, anterior a esta fase). O projeto real
do usuário nunca é lido para escrita nem modificado por esta suíte.

`processo-teste/` não é rastreado pelo git — módulo inteiro pula (`skipif`)
quando `dados_consolidados.json` não existe (checkout limpo, CI, etc.).
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import sysdoc  # noqa: E402

PROJETO = ROOT / "processo-teste"
DADOS_JSON = PROJETO / "dados_consolidados.json"

pytestmark = pytest.mark.skipif(
    not DADOS_JSON.is_file(),
    reason="processo-teste/dados_consolidados.json ausente (projeto não rastreado pelo git)",
)

TEXTO_IN_SGD_TIC = "Instrução Normativa SGD/ME nº 94, de 23 de dezembro de 2022"
PADRAO_NOME_ARTEFATO = re.compile(r"^\d{2}_[a-z0-9-]+_dvi_\d{4}-\d{2}-\d{2}\.docx$")


def _copiar_projeto(tmp_path: Path) -> Path:
    """Copia `processo-teste` para `tmp_path`, sem `output/`, `.sysdoc/cache/`
    nem qualquer `.docx` já gerado (raiz ou `referencias/dvi.docx` — formato
    legado, anterior à Rodada 1). Devolve o caminho da cópia."""
    destino = tmp_path / "processo-teste"
    shutil.copytree(
        PROJETO,
        destino,
        ignore=shutil.ignore_patterns("output", "cache", "*.docx"),
    )
    return destino


def _definir_tipo(projeto: Path, tipo: str) -> None:
    paths = sysdoc.project_paths(projeto)
    config = sysdoc.load_config(paths)
    config["tipo"] = tipo
    sysdoc.write_config(paths, config)


def _rodar_create(projeto: Path) -> Path:
    rc = sysdoc.create(str(projeto), "dvi")
    assert rc == 0
    saidas = sorted(projeto.glob("*_dvi_*.docx"))
    assert saidas, "sysdoc create dvi não gerou nenhum .docx"
    return saidas[-1]


def _document_xml(caminho: Path) -> str:
    with zipfile.ZipFile(caminho) as zf:
        return zf.read("word/document.xml").decode("utf-8")


def _texto_do_docx(caminho: Path) -> str:
    """Concatena todo o conteúdo de `<w:t>` do `word/document.xml` gerado,
    para asserções sobre texto legível em vez de XML cru."""
    xml = _document_xml(caminho)
    return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml))


def _dados_reais() -> dict:
    return json.loads(DADOS_JSON.read_text(encoding="utf-8"))


class TestDespachoGeral:
    """Variante `tipo: geral` (já definida em `processo-teste/.sysdoc/config.yaml`)."""

    def test_create_gera_docx_sem_placeholder(self, tmp_path):
        projeto = _copiar_projeto(tmp_path)
        saida = _rodar_create(projeto)
        xml = _document_xml(saida)
        assert "{{" not in xml

    def test_tres_secoes_numeradas(self, tmp_path):
        projeto = _copiar_projeto(tmp_path)
        saida = _rodar_create(projeto)
        texto = _texto_do_docx(saida)
        assert "1) ESTUDO TÉCNICO PRELIMINAR - ETP" in texto
        assert "2) TERMO DE REFERÊNCIA - TR" in texto
        assert "3) PENDÊNCIAS DE DOCUMENTAÇÃO" in texto

    def test_contagem_de_alineas(self, tmp_path):
        projeto = _copiar_projeto(tmp_path)
        saida = _rodar_create(projeto)
        xml = _document_xml(saida)

        secoes = re.split(r'(?=<w:pStyle w:val="DviPecaTitulo"/>)', xml)
        secoes_com_titulo = [s for s in secoes if 'w:val="DviPecaTitulo"' in s]
        assert len(secoes_com_titulo) == 3

        contagens = [s.count('w:val="DviAlinea"') for s in secoes_com_titulo]
        assert contagens == [5, 6, 14]

    def test_duas_referencias_cruzadas(self, tmp_path):
        projeto = _copiar_projeto(tmp_path)
        saida = _rodar_create(projeto)
        texto = _texto_do_docx(saida)
        assert texto.count("Vide apontamento constante na alínea") == 2

    def test_nenhum_item_conforme(self, tmp_path):
        projeto = _copiar_projeto(tmp_path)
        saida = _rodar_create(projeto)
        xml = _document_xml(saida)

        dados = _dados_reais()
        conformes = [item for item in dados["itens"] if item.get("classificação") == "conforme"]
        assert len(conformes) == 24

        from xml.sax.saxutils import escape

        for item in conformes:
            trecho = escape(str(item.get("parecer", ""))[:60])
            assert trecho not in xml, f"item conforme {item.get('id')} vazou para o despacho"

    def test_cabecalho_sem_sei_quando_nao_informado(self, tmp_path):
        projeto = _copiar_projeto(tmp_path)
        dados = _dados_reais()
        assert dados["secao_etp"]["numero"] == "não informado"
        assert dados["secao_tr"]["numero"] == "não informado"

        saida = _rodar_create(projeto)
        texto = _texto_do_docx(saida)
        assert "(SEI" not in texto
        assert "não informado" not in texto

    def test_marcadores_de_campo_ausente(self, tmp_path):
        projeto = _copiar_projeto(tmp_path)
        saida = _rodar_create(projeto)
        texto = _texto_do_docx(saida)

        assert "[PREENCHER: vocativo]" in texto
        assert "[PREENCHER: signatario]" in texto
        assert "[PREENCHER: autoridade]" in texto
        assert "DELIC" in texto
        assert "À COLOG" in texto

    def test_observacoes_presentes(self, tmp_path):
        projeto = _copiar_projeto(tmp_path)
        saida = _rodar_create(projeto)
        texto = _texto_do_docx(saida)

        assert "Observações:" in texto
        assert "não abordou as particularidades da execução do serviço" in texto
        assert "verificação da presença dos elementos e requisitos exigidos" in texto
        assert "Visando preservar o histórico do processo" in texto

    def test_xml_bem_formado(self, tmp_path):
        projeto = _copiar_projeto(tmp_path)
        saida = _rodar_create(projeto)
        xml = _document_xml(saida)
        ElementTree.fromstring(xml)


class TestDespachoTic:
    def test_variante_tic_via_config(self, tmp_path):
        projeto = _copiar_projeto(tmp_path)
        _definir_tipo(projeto, "tic")
        (projeto / "referencias" / "dvi.docx").unlink(missing_ok=True)

        saida = _rodar_create(projeto)
        xml = _document_xml(saida)
        texto = _texto_do_docx(saida)

        assert TEXTO_IN_SGD_TIC in texto
        assert "{{" not in xml

    def test_geral_e_tic_diferem(self, tmp_path):
        projeto_geral = _copiar_projeto(tmp_path)
        saida_geral = _rodar_create(projeto_geral)
        xml_geral = _document_xml(saida_geral)

        projeto_tic = tmp_path / "processo-teste-tic"
        shutil.copytree(
            PROJETO,
            projeto_tic,
            ignore=shutil.ignore_patterns("output", "cache", "*.docx"),
        )
        _definir_tipo(projeto_tic, "tic")
        (projeto_tic / "referencias" / "dvi.docx").unlink(missing_ok=True)
        saida_tic = _rodar_create(projeto_tic)
        xml_tic = _document_xml(saida_tic)

        assert xml_geral != xml_tic


class TestOverrideDoProjeto:
    def test_referencias_dvi_docx_customizado_vence(self, tmp_path):
        projeto = _copiar_projeto(tmp_path)
        _definir_tipo(projeto, "tic")

        document_xml = (
            "<w:document><w:body>"
            "<w:p><w:r><w:t>MODELO_DO_ORGAO_E2E</w:t></w:r></w:p>"
            "<w:p><w:r><w:t>{{corpo_apontamentos_xml}}</w:t></w:r></w:p>"
            "</w:body></w:document>"
        )
        custom = projeto / "referencias" / "dvi.docx"
        custom.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(custom, "w") as zf:
            zf.writestr("[Content_Types].xml", "<Types></Types>")
            zf.writestr("word/document.xml", document_xml)

        saida = _rodar_create(projeto)
        xml = _document_xml(saida)

        assert "MODELO_DO_ORGAO_E2E" in xml
        assert "DviPecaTitulo" in xml
        assert "{{" not in xml


class TestNomeDoArtefato:
    def test_padrao_de_nome(self, tmp_path):
        projeto = _copiar_projeto(tmp_path)
        saida = _rodar_create(projeto)
        assert PADRAO_NOME_ARTEFATO.match(saida.name), saida.name
