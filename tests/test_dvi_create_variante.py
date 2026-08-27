"""
Testes de `sysdoc create <pasta> dvi` ponta a ponta: resolução de variante
por `tipo` (D-13), precedência do template do projeto (D-14), conteúdo
filtrado do despacho (D-03/D-06/D-08) e não-injeção de XML cru pelo
`dados_consolidados.json` (D-09), no caminho real do `create()` — não no
nível isolado de `render_docx_template` (esse já é coberto por
`tests/test_dvi_render_raw.py`, Plano 04).
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import sysdoc  # noqa: E402

TEMPLATE_GERAL = ROOT / "templates" / "dvi" / "despacho_geral.docx"
TEMPLATE_TIC = ROOT / "templates" / "dvi" / "despacho_tic.docx"
TEXTO_IN_SGD_TIC = "Instrução Normativa SGD/ME nº 94, de 23 de dezembro de 2022"


def _base_dvi_json(**overrides) -> dict:
    payload = {
        "modelo_ia": "gpt-5",
        "data_análise": "2026-08-27",
        "projeto": {
            "órgão": "Secretaria de Teste",
            "processo": "90796110000007.000039/2025-14",
            "valor_estimado": "R$ 100.000,00",
            "objeto": "Aquisição de materiais de teste",
        },
        "secao_etp": {
            "classificação_documento": "aprovado_com_ressalvas",
            "parecer_documento": "Parecer da seção ETP consolidado.",
            "numero": "1343011",
        },
        "secao_tr": {
            "classificação_documento": "aprovado",
            "parecer_documento": "Parecer da seção TR consolidado.",
            "numero": "1343014",
        },
        "itens": [
            {
                "id": "ETP-001",
                "documento": "ETP",
                "seção": "4.20",
                "de": "texto original",
                "para": "PARA_SENTINELA_NAO_DEVE_APARECER",
                "parecer": "PARECER_AJUSTE_SENTINELA",
                "fundamento": "Lei 14.133/2021 art. 18",
                "classificação": "ajuste_necessário",
                "severidade": "média",
                "risco_jurídico": "relevante",
            },
            {
                "id": "ETP-002",
                "documento": "ETP",
                "seção": "4.30",
                "de": "texto original",
                "para": "outro texto",
                "parecer": "PARECER_CONFORME_SENTINELA",
                "fundamento": "Requisito atendido integralmente.",
                "classificação": "conforme",
                "severidade": "baixa",
                "risco_jurídico": "informativo",
            },
            {
                "id": "TR-001",
                "documento": "TR",
                "seção": "5.1",
                "de": "texto original 2",
                "para": "outro texto 2",
                "parecer": "PARECER_RISCO_SENTINELA",
                "fundamento": "Lei 14.133/2021 art. 40",
                "classificação": "risco",
                "severidade": "crítica",
                "risco_jurídico": "bloqueante",
            },
            {
                "id": "MCP-001",
                "documento": "MCP",
                "seção": "2.1",
                "de": "",
                "para": "",
                "parecer": "PARECER_PENDENCIA_SENTINELA",
                "fundamento": "Cronograma Físico-Financeiro não localizado nos autos.",
                "classificação": "pendente",
                "severidade": "média",
                "risco_jurídico": "informativo",
            },
        ],
    }
    payload.update(overrides)
    return payload


def _escrever_dvi_json(project_dir: Path, **overrides) -> Path:
    project_dir.mkdir(parents=True, exist_ok=True)
    json_file = project_dir / "dados_consolidados.json"
    json_file.write_text(
        json.dumps(_base_dvi_json(**overrides), ensure_ascii=False),
        encoding="utf-8",
    )
    return json_file


def _projeto(
    tmp_path: Path,
    nome: str,
    tipo: str | None = None,
    despacho: dict | None = None,
    **json_overrides,
) -> tuple[Path, "sysdoc.ProjectPaths"]:
    """Roda `sysdoc.init_command(nome)`, opcionalmente reescreve `tipo`/`despacho`
    em `.sysdoc/config.yaml` e escreve um `dados_consolidados.json` válido.

    Devolve `(project_dir, paths)`. Precisa rodar com `monkeypatch.chdir(tmp_path)`
    já ativo no chamador.
    """
    sysdoc.init_command(nome)
    project_dir = tmp_path / nome
    paths = sysdoc.project_paths(project_dir)
    if tipo is not None or despacho is not None:
        config = sysdoc.load_config(paths)
        if tipo is not None:
            config["tipo"] = tipo
        if despacho is not None:
            config["despacho"] = despacho
        sysdoc.write_config(paths, config)
    _escrever_dvi_json(project_dir, **json_overrides)
    return project_dir, paths


def _escrever_template_sintetico(path: Path, marcador: str) -> None:
    """DOCX sintético com o `marcador` num parágrafo e o placeholder raw
    `{{corpo_apontamentos_xml}}` isolado no seu próprio `<w:p>` hospedeiro."""
    document_xml = (
        "<w:document><w:body>"
        f"<w:p><w:r><w:t>{marcador}</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>{{corpo_apontamentos_xml}}</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types></Types>")
        zf.writestr("word/document.xml", document_xml)


def _document_xml(output: Path) -> str:
    with zipfile.ZipFile(output) as zf:
        return zf.read("word/document.xml").decode("utf-8")


class TestResolucaoDeTipo:
    """D-13: `create` resolve a variante do despacho pelo `tipo` do config."""

    def test_tipo_geral_usa_despacho_geral(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir, _ = _projeto(tmp_path, "ProjetoGeral", tipo="geral")

        rc = sysdoc.create("ProjetoGeral", "dvi")

        assert rc == 0
        output = next(project_dir.glob("*_dvi_*.docx"))
        assert TEXTO_IN_SGD_TIC not in _document_xml(output)

    def test_tipo_tic_usa_despacho_tic(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir, _ = _projeto(tmp_path, "ProjetoTic", tipo="tic")

        rc = sysdoc.create("ProjetoTic", "dvi")

        assert rc == 0
        output = next(project_dir.glob("*_dvi_*.docx"))
        assert TEXTO_IN_SGD_TIC in _document_xml(output)

    def test_tipo_invalido_no_config_falha_com_mensagem(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _projeto(tmp_path, "ProjetoTipoInvalido", tipo="xpto")

        with pytest.raises(SystemExit) as excinfo:
            sysdoc.create("ProjetoTipoInvalido", "dvi")

        assert "aplicabilidade inválida" in str(excinfo.value)

    def test_sem_tipo_e_sem_template_no_projeto_falha_com_remedio(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir, paths = _projeto(tmp_path, "ProjetoSemTipo")
        (paths.referencias / "dvi.docx").unlink()

        with pytest.raises(SystemExit) as excinfo:
            sysdoc.create("ProjetoSemTipo", "dvi")

        message = str(excinfo.value)
        assert "aplicabilidade não declarada" in message
        assert ".sysdoc/config.yaml" in message


class TestPrecedenciaDoProjeto:
    """D-14: o template customizado do projeto continua vencendo o do repo."""

    def test_docx_customizado_do_projeto_vence(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir, paths = _projeto(tmp_path, "ProjetoCustom", tipo="tic")
        _escrever_template_sintetico(paths.referencias / "dvi.docx", "TEMPLATE_DO_ORGAO")

        rc = sysdoc.create("ProjetoCustom", "dvi")

        assert rc == 0
        output = next(project_dir.glob("*_dvi_*.docx"))
        assert "TEMPLATE_DO_ORGAO" in _document_xml(output)

    def test_customizado_dispensa_tipo(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir, paths = _projeto(tmp_path, "ProjetoCustomSemTipo")
        _escrever_template_sintetico(paths.referencias / "dvi.docx", "TEMPLATE_DO_ORGAO")

        rc = sysdoc.create("ProjetoCustomSemTipo", "dvi")

        assert rc == 0

    def test_semente_intocada_nao_vence_o_tipo(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir, paths = _projeto(tmp_path, "ProjetoSementeIntocada", tipo="tic")
        # A semente foi copiada por `init_command` ANTES de escrevermos
        # `tipo: tic` acima (com config ainda vazio, portanto TIPO_VERIFICACAO_PADRAO
        # = "geral") — exatamente o cenário de semente intocada + tipo divergente.
        assert (paths.referencias / "dvi.docx").read_bytes() == TEMPLATE_GERAL.read_bytes()

        rc = sysdoc.create("ProjetoSementeIntocada", "dvi")

        assert rc == 0
        output = next(project_dir.glob("*_dvi_*.docx"))
        assert TEXTO_IN_SGD_TIC in _document_xml(output)

    def test_template_arg_vence_tudo(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir, paths = _projeto(tmp_path, "ProjetoTemplateArg", tipo="tic")
        alt_template = tmp_path / "alt_dvi.docx"
        _escrever_template_sintetico(alt_template, "TEMPLATE_EXPLICITO")

        rc = sysdoc.create("ProjetoTemplateArg", "dvi", template_arg=str(alt_template))

        assert rc == 0
        output = next(project_dir.glob("*_dvi_*.docx"))
        assert "TEMPLATE_EXPLICITO" in _document_xml(output)

    def test_modelo_dvi_docx_tambem_e_respeitado(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir, paths = _projeto(tmp_path, "ProjetoModeloDvi", tipo="tic")
        (paths.referencias / "dvi.docx").unlink()
        _escrever_template_sintetico(paths.referencias / "modelo_dvi.docx", "TEMPLATE_MODELO_DVI")

        rc = sysdoc.create("ProjetoModeloDvi", "dvi")

        assert rc == 0
        output = next(project_dir.glob("*_dvi_*.docx"))
        assert "TEMPLATE_MODELO_DVI" in _document_xml(output)


class TestNaoInjecaoPeloJson:
    """D-09: chave homônima em `dados_consolidados.json` nunca alcança o
    canal cru no caminho real de `create()`. A defesa é o canal `raw_xml`
    separado (Plano 04), não a ordem de atribuição."""

    def test_json_com_chave_homonima_nao_injeta_xml_no_create(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir, paths = _projeto(tmp_path, "ProjetoInjecaoTopo", tipo="geral")
        dados = _base_dvi_json()
        dados["corpo_apontamentos_xml"] = "<w:p><w:r><w:t>PAYLOAD_DO_JSON</w:t></w:r></w:p>"
        (project_dir / "dados_consolidados.json").write_text(
            json.dumps(dados, ensure_ascii=False), encoding="utf-8"
        )

        rc = sysdoc.create("ProjetoInjecaoTopo", "dvi")

        assert rc == 0
        output = next(project_dir.glob("*_dvi_*.docx"))
        xml = _document_xml(output)
        assert "<w:t>PAYLOAD_DO_JSON</w:t>" not in xml
        # Checagem forte o bastante para distinguir XML cru real de texto
        # escapado que apenas contém a substring solta: `xml_escape` não
        # escapa aspas, então `w:val="DviPecaTitulo"` sobreviveria mesmo
        # dentro de um <w:t> corrompido — o marcador confiável é a tag de
        # abertura completa, com `<` e `>` que só sobrevivem sem escape.
        assert '<w:pStyle w:val="DviPecaTitulo"/>' in xml
        ElementTree.fromstring(xml)

    def test_json_com_chave_homonima_aninhada_tambem_e_inerte(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir, paths = _projeto(tmp_path, "ProjetoInjecaoAninhada", tipo="geral")
        dados = _base_dvi_json()
        dados["projeto"]["corpo_apontamentos_xml"] = (
            "<w:p><w:r><w:t>PAYLOAD_ANINHADO</w:t></w:r></w:p>"
        )
        (project_dir / "dados_consolidados.json").write_text(
            json.dumps(dados, ensure_ascii=False), encoding="utf-8"
        )

        rc = sysdoc.create("ProjetoInjecaoAninhada", "dvi")

        assert rc == 0
        output = next(project_dir.glob("*_dvi_*.docx"))
        xml = _document_xml(output)
        assert "PAYLOAD_ANINHADO" not in xml
        ElementTree.fromstring(xml)

    def test_payload_de_escape_em_parecer_nao_quebra_o_documento(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir, paths = _projeto(tmp_path, "ProjetoEscapeParecer", tipo="geral")
        dados = _base_dvi_json()
        dados["itens"][0]["parecer"] = "</w:t></w:r></w:p><w:p><w:r><w:t>INJETADO_MAU"
        (project_dir / "dados_consolidados.json").write_text(
            json.dumps(dados, ensure_ascii=False), encoding="utf-8"
        )

        rc = sysdoc.create("ProjetoEscapeParecer", "dvi")

        assert rc == 0
        output = next(project_dir.glob("*_dvi_*.docx"))
        xml = _document_xml(output)
        assert "<w:t>INJETADO_MAU" not in xml
        ElementTree.fromstring(xml)


class TestConteudoDoDespacho:
    """D-03, D-06, D-08: conteúdo filtrado, campos institucionais e estilos."""

    def test_sem_placeholders_remanescentes(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir, _ = _projeto(
            tmp_path,
            "ProjetoSemPlaceholder",
            tipo="geral",
            despacho={"vocativo": "Senhora Coordenadora Administrativa,"},
        )

        rc = sysdoc.create("ProjetoSemPlaceholder", "dvi")

        assert rc == 0
        output = next(project_dir.glob("*_dvi_*.docx"))
        assert "{{" not in _document_xml(output)

    def test_itens_conforme_nao_aparecem(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir, _ = _projeto(tmp_path, "ProjetoConforme", tipo="geral")

        rc = sysdoc.create("ProjetoConforme", "dvi")

        assert rc == 0
        output = next(project_dir.glob("*_dvi_*.docx"))
        assert "PARECER_CONFORME_SENTINELA" not in _document_xml(output)

    def test_ajuste_e_risco_aparecem(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir, _ = _projeto(tmp_path, "ProjetoAjusteRisco", tipo="geral")

        rc = sysdoc.create("ProjetoAjusteRisco", "dvi")

        assert rc == 0
        output = next(project_dir.glob("*_dvi_*.docx"))
        xml = _document_xml(output)
        assert "PARECER_AJUSTE_SENTINELA" in xml
        assert "PARECER_RISCO_SENTINELA" in xml

    def test_campo_para_nao_aparece(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir, _ = _projeto(tmp_path, "ProjetoParaSentinela", tipo="geral")

        rc = sysdoc.create("ProjetoParaSentinela", "dvi")

        assert rc == 0
        output = next(project_dir.glob("*_dvi_*.docx"))
        assert "PARA_SENTINELA_NAO_DEVE_APARECER" not in _document_xml(output)

    def test_campos_institucionais_do_config(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir, _ = _projeto(
            tmp_path,
            "ProjetoCamposInstitucionais",
            tipo="geral",
            despacho={"vocativo": "Senhora Coordenadora Administrativa,"},
        )

        rc = sysdoc.create("ProjetoCamposInstitucionais", "dvi")

        assert rc == 0
        output = next(project_dir.glob("*_dvi_*.docx"))
        xml = _document_xml(output)
        assert "Senhora Coordenadora Administrativa," in xml
        assert "[PREENCHER: signatario]" in xml
        assert "[PREENCHER: unidade]" in xml

    def test_corpo_usa_estilos_nomeados(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir, _ = _projeto(tmp_path, "ProjetoEstilos", tipo="geral")

        rc = sysdoc.create("ProjetoEstilos", "dvi")

        assert rc == 0
        output = next(project_dir.glob("*_dvi_*.docx"))
        xml = _document_xml(output)
        assert '<w:pStyle w:val="DviPecaTitulo"/>' in xml
        assert '<w:pStyle w:val="DviAlinea"/>' in xml

    def test_saida_e_xml_bem_formado(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir, _ = _projeto(tmp_path, "ProjetoXmlValido", tipo="geral")

        rc = sysdoc.create("ProjetoXmlValido", "dvi")

        assert rc == 0
        output = next(project_dir.glob("*_dvi_*.docx"))
        ElementTree.fromstring(_document_xml(output))


class TestSeedPorVariante:
    """D-14: `init` semeia a variante correspondente ao `tipo` do projeto."""

    def test_init_semeia_geral_por_padrao(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sysdoc.init_command("ProjetoSeedGeral")

        destino = tmp_path / "ProjetoSeedGeral" / "referencias" / "dvi.docx"
        assert destino.read_bytes() == TEMPLATE_GERAL.read_bytes()

    def test_init_semeia_tic_quando_config_ja_declara(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir = tmp_path / "ProjetoSeedTic"
        paths = sysdoc.ensure_project_structure(project_dir)
        config = sysdoc.load_config(paths)
        config["tipo"] = "tic"
        sysdoc.write_config(paths, config)

        rc = sysdoc.init_command("ProjetoSeedTic")

        assert rc == 0
        destino = paths.referencias / "dvi.docx"
        assert destino.read_bytes() == TEMPLATE_TIC.read_bytes()

    def test_init_nao_sobrescreve_template_existente(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir = tmp_path / "ProjetoSeedExistente"
        paths = sysdoc.ensure_project_structure(project_dir)
        paths.referencias.mkdir(parents=True, exist_ok=True)
        (paths.referencias / "dvi.docx").write_bytes(b"customizado do usuario")

        rc = sysdoc.init_command("ProjetoSeedExistente")

        assert rc == 0
        assert (paths.referencias / "dvi.docx").read_bytes() == b"customizado do usuario"
