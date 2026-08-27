"""
Testes de `templates/dvi_base.docx` e da semeadura por `sysdoc init` (P6 -
260826-o2d).
"""

from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import sysdoc  # noqa: E402

TEMPLATE_BASE = ROOT / "templates" / "dvi_base.docx"


def _base_dvi_json(**overrides) -> dict:
    payload = {
        "titulo": "Despacho de Verificação Inicial",
        "subtitulo": "Análise comparativa",
        "modelo_ia": "gpt-5",
        "data_análise": "2026-08-26",
        "parecer_executivo": "Parecer executivo consolidado para o processo de teste.",
        "secao_etp": {
            "classificação_documento": "aprovado_com_ressalvas",
            "parecer_documento": "Parecer da seção ETP consolidado.",
            "numero": "01",
        },
        "secao_tr": {
            "classificação_documento": "aprovado",
            "parecer_documento": "Parecer da seção TR consolidado.",
            "numero": "01",
        },
        "itens": [
            {
                "id": "ETP-001",
                "número": 1,
                "item": "Item 1",
                "documento": "ETP",
                "seção": "3.2",
                "de": "texto original",
                "para": "texto revisado",
                "parecer": "Parecer do item 1",
                "fundamento": "Lei 14.133/2021 art. 18",
                "classificação": "ajuste_necessário",
                "severidade": "média",
                "risco_jurídico": "relevante",
                "status_delic": None,
                "alterado_pelo_jurídico": False,
            },
        ],
        "nota_integridade": "Nenhuma inconsistência estrutural identificada.",
    }
    payload.update(overrides)
    return payload


def _placeholders_no_xml(caminho_docx: Path) -> set[str]:
    xml = zipfile.ZipFile(caminho_docx).read("word/document.xml").decode()
    return set(re.findall(r"{{[^}]+}}", xml))


class TestTemplateBaseValido:
    def test_abre_como_zip_valido_com_entradas_essenciais(self):
        with zipfile.ZipFile(TEMPLATE_BASE) as zf:
            nomes = set(zf.namelist())
        assert "[Content_Types].xml" in nomes
        assert "_rels/.rels" in nomes
        assert "word/document.xml" in nomes

    def test_placeholders_integros_e_sem_orfaos(self):
        placeholders = _placeholders_no_xml(TEMPLATE_BASE)
        assert "{{projeto}}" not in placeholders

        dados = _base_dvi_json()
        itens = dados.get("itens", [])
        valores = sysdoc.flatten_json(dados)
        valores["tipo"] = "dvi"
        valores["json"] = "dados_consolidados.json"
        valores["template"] = "referencias/dvi.docx"
        valores["tabela_itens"] = sysdoc.build_tabela_itens(itens)
        valores["total_itens"] = str(len(itens))
        valores["total_bloqueantes"] = "0"
        valores["total_pendentes"] = "0"

        for placeholder in placeholders:
            chave = placeholder[2:-2]
            assert chave in valores, f"placeholder órfão: {placeholder}"

    def test_render_docx_template_remove_todos_os_placeholders(self, tmp_path):
        dados = _base_dvi_json()
        itens = dados.get("itens", [])
        valores = sysdoc.flatten_json(dados)
        valores["tipo"] = "dvi"
        valores["json"] = "dados_consolidados.json"
        valores["template"] = "referencias/dvi.docx"
        valores["tabela_itens"] = sysdoc.build_tabela_itens(itens)
        valores["total_itens"] = str(len(itens))
        valores["total_bloqueantes"] = "0"
        valores["total_pendentes"] = "0"

        saida = tmp_path / "saida.docx"
        sysdoc.render_docx_template(TEMPLATE_BASE, saida, valores)

        xml = zipfile.ZipFile(saida).read("word/document.xml").decode()
        assert "{{" not in xml


class TestSeedDviTemplate:
    def test_init_cria_referencias_dvi_docx_byte_identico(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rc = sysdoc.init_command("ProjetoSemente")
        assert rc == 0

        destino = tmp_path / "ProjetoSemente" / "referencias" / "dvi.docx"
        assert destino.is_file()
        assert destino.read_bytes() == TEMPLATE_BASE.read_bytes()

    def test_init_nao_sobrescreve_quando_rodado_duas_vezes(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sysdoc.init_command("ProjetoDuplicado")
        destino = tmp_path / "ProjetoDuplicado" / "referencias" / "dvi.docx"
        destino.write_bytes(b"conteudo customizado do usuario")

        rc = sysdoc.init_command("ProjetoDuplicado")
        assert rc == 0
        assert destino.read_bytes() == b"conteudo customizado do usuario"

    def test_init_nao_sobrescreve_modelo_dvi_ja_presente(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoComModeloProprio"
        refs = project_dir / "referencias"
        refs.mkdir(parents=True)
        (refs / "modelo_dvi.docx").write_bytes(b"modelo institucional do usuario")

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.init_command("ProjetoComModeloProprio")
        assert rc == 0

        assert (refs / "modelo_dvi.docx").read_bytes() == b"modelo institucional do usuario"
        assert not (refs / "dvi.docx").is_file()

    def test_seed_dvi_template_devolve_none_quando_ja_existe(self, tmp_path):
        paths = sysdoc.project_paths(tmp_path / "ProjetoDireto")
        paths.referencias.mkdir(parents=True)
        (paths.referencias / "dvi.docx").write_bytes(b"ja existe")

        resultado = sysdoc.seed_dvi_template(paths)
        assert resultado is None
        assert (paths.referencias / "dvi.docx").read_bytes() == b"ja existe"


def _escrever_dvi_json(project_dir: Path, **overrides) -> Path:
    project_dir.mkdir(parents=True, exist_ok=True)
    json_file = project_dir / "dados_consolidados.json"
    json_file.write_text(
        json.dumps(_base_dvi_json(**overrides), ensure_ascii=False),
        encoding="utf-8",
    )
    return json_file


class TestCreateAposInit:
    def test_create_dvi_funciona_logo_apos_init(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sysdoc.init_command("ProjetoCriarDvi")
        _escrever_dvi_json(tmp_path / "ProjetoCriarDvi")

        rc = sysdoc.create("ProjetoCriarDvi", "dvi")
        assert rc == 0
        gerados = list((tmp_path / "ProjetoCriarDvi").glob("*_dvi_*.docx"))
        assert len(gerados) == 1

    def test_create_tr_continua_falhando_sem_usar_template_dvi(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sysdoc.init_command("ProjetoCriarTr")
        _escrever_dvi_json(
            tmp_path / "ProjetoCriarTr",
            projeto={
                "órgão": "Secretaria de Teste",
                "processo": "0001/2026",
                "valor_estimado": "R$ 100.000,00",
                "objeto": "Aquisição de materiais de teste",
            },
        )

        with pytest.raises(SystemExit) as excinfo:
            sysdoc.create("ProjetoCriarTr", "tr")
        assert "template" in str(excinfo.value).lower()
