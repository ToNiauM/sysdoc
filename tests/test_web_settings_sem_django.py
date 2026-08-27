"""
Testes de leitura de arquivo sobre o empacotamento e as settings da web que
rodam mesmo em ambiente sem Django instalado — nenhum destes dois testes
importa `django`, só leem `pyproject.toml` e `sysdoc_web/settings.py` como
texto. Complementam `tests/test_web_base.py`, que pula inteiro sem Django.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_django_nao_e_dependencia_base():
    dados = tomllib.loads((ROOT / "pyproject.toml").read_text())
    dependencias = " ".join(dados["project"]["dependencies"]).lower()
    assert "django" not in dependencias

    web_extra = dados["project"]["optional-dependencies"]["web"]
    assert any(pacote.lower().startswith("django") for pacote in web_extra)


def test_settings_nao_expoem_credencial():
    texto = (ROOT / "sysdoc_web" / "settings.py").read_text()
    for proibido in (
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        assert proibido not in texto
