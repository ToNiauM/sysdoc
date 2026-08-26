"""
Testes de `sysdoc create dvi` (tipo dvi no comando create).
"""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import sysdoc  # noqa: E402


DVI_DOCUMENT_XML = (
    "<w:document>"
    "{{projeto.órgão}} {{projeto.processo}} {{projeto.objeto}} "
    "{{parecer_executivo}} {{secao_etp.parecer_documento}} {{secao_tr.parecer_documento}} "
    "{{tabela_itens}}"
    "</w:document>"
)


def write_synthetic_template(path: Path, document_xml: str = DVI_DOCUMENT_XML) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types></Types>")
        zf.writestr("word/document.xml", document_xml)


def base_dvi_json(**overrides) -> dict:
    payload = {
        "modelo_ia": "gpt-5",
        "data_análise": "2026-08-26",
        "projeto": {
            "órgão": "Secretaria de Teste",
            "processo": "0001/2026",
            "valor_estimado": "R$ 100.000,00",
            "objeto": "Aquisição de materiais de teste",
        },
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
            {
                "id": "TR-001",
                "número": 2,
                "item": "Item 2",
                "documento": "TR",
                "seção": "5.1",
                "de": "texto original 2",
                "para": "texto revisado 2",
                "parecer": "Parecer do item 2",
                "fundamento": "Lei 14.133/2021 art. 40",
                "classificação": "risco",
                "severidade": "crítica",
                "risco_jurídico": "bloqueante",
                "status_delic": None,
                "alterado_pelo_jurídico": False,
            },
        ],
    }
    payload.update(overrides)
    return payload


def write_dvi_json(project_dir: Path, **overrides) -> Path:
    project_dir.mkdir(parents=True, exist_ok=True)
    json_file = project_dir / "dados_consolidados.json"
    json_file.write_text(
        json.dumps(base_dvi_json(**overrides), ensure_ascii=False),
        encoding="utf-8",
    )
    return json_file


class TestDviCreate:
    def test_create_dvi_generates_docx(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoDvi"
        refs = project_dir / "referencias"
        write_dvi_json(project_dir)
        write_synthetic_template(refs / "dvi.docx")

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.create("ProjetoDvi", "dvi")

        assert rc == 0
        output = project_dir / "01_projetodvi_dvi_2026-08-26.docx"
        assert output.is_file()

    def test_create_dvi_output_name_matches_pattern(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoNomeDvi"
        refs = project_dir / "referencias"
        write_dvi_json(project_dir)
        write_synthetic_template(refs / "dvi.docx")

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.create("ProjetoNomeDvi", "dvi")

        assert rc == 0
        matches = list(project_dir.glob("*_dvi_*.docx"))
        assert len(matches) == 1
        import re

        assert re.match(r"^\d{2}_[a-z0-9-]+_dvi_\d{4}-\d{2}-\d{2}\.docx$", matches[0].name)

    def test_create_dvi_contains_pareceres_and_tabela(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoPareceresDvi"
        refs = project_dir / "referencias"
        write_dvi_json(project_dir)
        write_synthetic_template(refs / "dvi.docx")

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.create("ProjetoPareceresDvi", "dvi")

        assert rc == 0
        output = next(project_dir.glob("*_dvi_*.docx"))
        with zipfile.ZipFile(output) as zf:
            xml = zf.read("word/document.xml").decode("utf-8")
        assert "Parecer executivo consolidado para o processo de teste." in xml
        assert "Parecer da seção ETP consolidado." in xml
        assert "Parecer da seção TR consolidado." in xml
        assert "ETP-001" in xml
        assert "TR-001" in xml
        assert "Parecer do item 1" in xml
        assert "Parecer do item 2" in xml

    def test_create_dvi_escapes_special_characters(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoEscapeDvi"
        refs = project_dir / "referencias"
        write_dvi_json(
            project_dir,
            parecer_executivo="Parecer com <tag> & aspas \"teste\" & sinal < e >.",
        )
        write_synthetic_template(refs / "dvi.docx")

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.create("ProjetoEscapeDvi", "dvi")

        assert rc == 0
        output = next(project_dir.glob("*_dvi_*.docx"))
        with zipfile.ZipFile(output) as zf:
            xml = zf.read("word/document.xml").decode("utf-8")
        assert "<tag>" not in xml
        assert "&lt;tag&gt;" in xml
        assert " & " not in xml
        assert "&amp;" in xml

    def test_create_dvi_second_generation_increments_prefix(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoSeqDvi"
        refs = project_dir / "referencias"
        write_dvi_json(project_dir)
        write_synthetic_template(refs / "dvi.docx")

        monkeypatch.chdir(tmp_path)
        rc1 = sysdoc.create("ProjetoSeqDvi", "dvi")
        rc2 = sysdoc.create("ProjetoSeqDvi", "dvi")

        assert rc1 == 0
        assert rc2 == 0
        assert (project_dir / "01_projetoseqdvi_dvi_2026-08-26.docx").is_file()
        assert (project_dir / "02_projetoseqdvi_dvi_2026-08-26.docx").is_file()

    def test_create_dvi_missing_template_fails_with_instructions(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoSemTemplateDvi"
        refs = project_dir / "referencias"
        refs.mkdir(parents=True)
        write_dvi_json(project_dir)

        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            sysdoc.create("ProjetoSemTemplateDvi", "dvi")

        message = str(exc_info.value)
        assert "dvi.docx" in message
        assert "referencias" in message

    def test_create_dvi_respects_explicit_template(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoTemplateExplicitoDvi"
        refs = project_dir / "referencias"
        write_dvi_json(project_dir)
        write_synthetic_template(refs / "outro_nome.docx")

        alt_template = tmp_path / "alt_dvi.docx"
        write_synthetic_template(alt_template, "<w:document>ALT {{parecer_executivo}}</w:document>")

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.create("ProjetoTemplateExplicitoDvi", "dvi", template_arg=str(alt_template))

        assert rc == 0
        output = next(project_dir.glob("*_dvi_*.docx"))
        with zipfile.ZipFile(output) as zf:
            xml = zf.read("word/document.xml").decode("utf-8")
        assert xml.startswith("<w:document>ALT")

    def test_create_dvi_does_not_modify_input_json(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoJsonImutavelDvi"
        refs = project_dir / "referencias"
        json_file = write_dvi_json(project_dir)
        write_synthetic_template(refs / "dvi.docx")

        before_hash = hashlib.sha256(json_file.read_bytes()).hexdigest()

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.create("ProjetoJsonImutavelDvi", "dvi")

        after_hash = hashlib.sha256(json_file.read_bytes()).hexdigest()

        assert rc == 0
        assert before_hash == after_hash

    def test_create_dvi_selects_template_by_name_variants(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoTemplateVariantDvi"
        refs = project_dir / "referencias"
        write_dvi_json(project_dir)
        write_synthetic_template(refs / "modelo_dvi.docx")

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.create("ProjetoTemplateVariantDvi", "dvi")

        assert rc == 0
        output = next(project_dir.glob("*_dvi_*.docx"))
        assert output.is_file()

    def test_create_dvi_rejects_template_with_zip_path_traversal(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoZipMaliciosoDvi"
        refs = project_dir / "referencias"
        write_dvi_json(project_dir)
        refs.mkdir(parents=True, exist_ok=True)
        malicious = refs / "dvi.docx"
        with zipfile.ZipFile(malicious, "w") as zf:
            zf.writestr("[Content_Types].xml", "<Types></Types>")
            zf.writestr("../evil.txt", "payload")

        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            sysdoc.create("ProjetoZipMaliciosoDvi", "dvi")

        assert ".." in str(exc_info.value)
