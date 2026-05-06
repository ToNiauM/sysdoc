"""
Testes automatizados do SysDoc.

Cobertura:
  - validate_sysdoc: campos obrigatórios, enums, coerência, modelo_ia, acentuação
  - sysdoc: slug(), extract_date(), detect_process(), sanitize_filename()
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "templates"))

from validate_sysdoc import validate, is_traceable, trace_tokens, word_count  # noqa: E402
from sysdoc import slug, extract_date, detect_process, sanitize_filename  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _base_item(doc="ETP", num=1, **overrides):
    item = {
        "id": f"{doc}-{num:03d}",
        "número": num,
        "item": "Objeto da contratação",
        "documento": doc,
        "seção": "1.1",
        "de": "O objeto desta contratação é a aquisição de combustível.",
        "para": "O objeto desta contratação deve ser detalhado com especificações técnicas.",
        "parecer": "Há omissão de especificações técnicas obrigatórias.",
        "fundamento": "Art. 40 da Lei 14.133/2021.",
        "classificação": "ajuste_necessário",
        "severidade": "média",
        "risco_jurídico": "relevante",
        "status_delic": None,
        "alterado_pelo_jurídico": False,
    }
    item.update(overrides)
    return item


def _base_data(**overrides):
    data = {
        "titulo": "Análise Comparativa",
        "subtitulo": "ETP e TR de Combustível",
        "modelo_ia": "gpt-4o-mini",
        "data_análise": "2026-05-06",
        "projeto": {
            "órgão": "Organização de Exemplo",
            "processo": "12345.000001/2026-01",
            "valor_estimado": "R$ 100.000,00",
            "objeto": "Aquisição de combustível",
        },
        "metadados": [{"label": "Referência", "valor": "SEI 12345"}],
        "documentos_analisados": ["ETP.pdf", "TR.pdf"],
        "parecer_executivo": "Este parecer " + ("palavra " * 460),
        "secao_etp": {
            "classificação_documento": "aprovado_com_ressalvas",
            "parecer_documento": "Documento " + ("palavra " * 130),
            "numero": "ETP-001",
        },
        "secao_tr": {
            "classificação_documento": "aprovado_com_ressalvas",
            "parecer_documento": "Documento " + ("palavra " * 130),
            "numero": "TR-001",
        },
        "itens": [_base_item("ETP", 1), _base_item("TR", 1)],
        "nota_integridade": "Análise gerada automaticamente.",
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# validate_sysdoc — testes de campos obrigatórios
# ---------------------------------------------------------------------------

class TestRequiredFields:
    def test_valid_data_passes(self, tmp_path):
        # Cria arquivos placeholder para que validate_document_paths não recuse
        (tmp_path / "ETP.pdf").write_bytes(b"%PDF-1.4 placeholder")
        (tmp_path / "TR.pdf").write_bytes(b"%PDF-1.4 placeholder")
        data = _base_data()
        json_file = tmp_path / "dados_consolidados.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")
        errors = validate(str(json_file), str(tmp_path))
        assert errors == [], f"Erros inesperados: {errors}"

    def test_missing_titulo(self, tmp_path):
        data = _base_data()
        del data["titulo"]
        json_file = tmp_path / "dados_consolidados.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")
        errors = validate(str(json_file), str(tmp_path))
        assert any("titulo" in e for e in errors)

    def test_missing_modelo_ia(self, tmp_path):
        data = _base_data()
        del data["modelo_ia"]
        json_file = tmp_path / "dados_consolidados.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")
        errors = validate(str(json_file), str(tmp_path))
        assert any("modelo_ia" in e for e in errors)

    def test_missing_item_campo(self, tmp_path):
        data = _base_data()
        del data["itens"][0]["parecer"]
        json_file = tmp_path / "dados_consolidados.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")
        errors = validate(str(json_file), str(tmp_path))
        assert any("parecer" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_sysdoc — modelo_ia
# ---------------------------------------------------------------------------

class TestModeloIA:
    def test_generic_modelo_fails(self, tmp_path):
        data = _base_data(modelo_ia="modelo")
        json_file = tmp_path / "dados_consolidados.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")
        errors = validate(str(json_file), str(tmp_path))
        assert any("modelo_ia" in e for e in errors)

    def test_slug_modelo_passes(self, tmp_path):
        data = _base_data(modelo_ia="claude-sonnet-4-6")
        json_file = tmp_path / "dados_consolidados.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")
        errors = validate(str(json_file), str(tmp_path))
        model_errors = [e for e in errors if "modelo_ia" in e]
        assert model_errors == []

    def test_uppercase_modelo_fails(self, tmp_path):
        data = _base_data(modelo_ia="GPT-4o")
        json_file = tmp_path / "dados_consolidados.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")
        errors = validate(str(json_file), str(tmp_path))
        assert any("modelo_ia" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_sysdoc — coerência de enums
# ---------------------------------------------------------------------------

class TestCoherence:
    def test_risco_conforme_must_be_informativo(self, tmp_path):
        item = _base_item("ETP", 1, classificação="conforme", risco_jurídico="relevante")
        data = _base_data(itens=[item, _base_item("TR", 1)])
        json_file = tmp_path / "dados_consolidados.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")
        errors = validate(str(json_file), str(tmp_path))
        assert any("informativo" in e for e in errors)

    def test_bloqueante_requires_high_severity(self, tmp_path):
        item = _base_item("ETP", 1, classificação="risco", risco_jurídico="bloqueante", severidade="baixa")
        data = _base_data(itens=[item, _base_item("TR", 1)])
        json_file = tmp_path / "dados_consolidados.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")
        errors = validate(str(json_file), str(tmp_path))
        assert any("bloqueante" in e for e in errors)

    def test_invalid_classificacao_enum(self, tmp_path):
        item = _base_item("ETP", 1, classificação="invalido")
        data = _base_data(itens=[item, _base_item("TR", 1)])
        json_file = tmp_path / "dados_consolidados.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")
        errors = validate(str(json_file), str(tmp_path))
        assert any("classificação" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_sysdoc — word count
# ---------------------------------------------------------------------------

class TestWordCount:
    def test_parecer_executivo_short_fails(self, tmp_path):
        data = _base_data(parecer_executivo="curto demais")
        json_file = tmp_path / "dados_consolidados.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")
        errors = validate(str(json_file), str(tmp_path))
        assert any("parecer_executivo" in e for e in errors)

    def test_word_count_utility(self):
        assert word_count("olá mundo") == 2
        assert word_count("") == 0
        assert word_count(None) == 0


# ---------------------------------------------------------------------------
# validate_sysdoc — rastreabilidade
# ---------------------------------------------------------------------------

class TestTraceability:
    def test_is_traceable_with_matching_tokens(self):
        source = "O objeto desta contratação é a aquisição de combustível automotivo"
        excerpt = "aquisição de combustível"
        assert is_traceable(excerpt, source)

    def test_is_traceable_omissao_marker(self):
        assert is_traceable("[OMISSÃO] item não encontrado", "qualquer texto")

    def test_not_traceable_invented_text(self):
        source = "O objeto é comprar papel"
        excerpt = "contratação de serviços de limpeza predial especializada"
        assert not is_traceable(excerpt, source)


# ---------------------------------------------------------------------------
# sysdoc — funções utilitárias
# ---------------------------------------------------------------------------

class TestSlug:
    def test_basic_slug(self):
        assert slug("claude-sonnet-4-6") == "claude-sonnet-4-6"

    def test_slug_with_accents(self):
        assert slug("Análise Técnica") == "analise-tecnica"

    def test_slug_empty(self):
        assert slug("") == "modelo"

    def test_slug_with_slashes(self):
        # provedor/modelo vira provedor-modelo
        assert slug("openai/gpt-4o") == "openai-gpt-4o"


class TestExtractDate:
    def test_iso_date(self):
        assert extract_date("2026-05-06") == "2026-05-06"

    def test_br_date(self):
        assert extract_date("06/05/2026") == "2026-05-06"

    def test_no_date_returns_today(self):
        from datetime import datetime
        result = extract_date("")
        assert result == datetime.now().strftime("%Y-%m-%d")


class TestDetectProcess:
    def test_sei_format(self):
        texts = {"ETP": "Processo SEI 12345.000001/2026-01 instaurado"}
        assert detect_process(texts) == "12345.000001/2026-01"

    def test_no_process(self):
        texts = {"ETP": "Sem número de processo aqui"}
        assert detect_process(texts) == "não identificado"


class TestSanitizeFilename:
    def test_basic(self):
        assert sanitize_filename("hello world") == "hello_world"

    def test_special_chars(self):
        result = sanitize_filename("Análise 2026!")
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-" for c in result)

    def test_empty_returns_arquivo(self):
        assert sanitize_filename("   ") == "arquivo"
