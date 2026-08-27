"""
Testes da fundação Django (`sysdoc_web`): autenticação obrigatória, ausência
de rota de auto-cadastro e cabeçalhos de segurança.

Requer Django instalado; se ausente, todo o módulo é pulado via
`pytest.importorskip`. Os testes que só leem `pyproject.toml` e
`sysdoc_web/settings.py` (sem precisar de Django em tempo de execução) ficam
em `tests/test_web_settings_sem_django.py`, que não faz esse skip.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

pytest.importorskip("django")


@pytest.fixture
def client(django_web):
    from django.test import Client

    return Client()


class TestAutenticacaoObrigatoria:
    def test_raiz_exige_login(self, client):
        resposta = client.get("/")
        assert resposta.status_code == 302
        assert resposta["Location"].startswith("/entrar/")

    def test_login_valido_da_acesso(self, django_web, client):
        from django.contrib.auth import get_user_model

        get_user_model().objects.create_user(username="pregoeiro", password="senha-forte-123")
        client.force_login(get_user_model().objects.get(username="pregoeiro"))

        resposta = client.get("/")
        assert resposta.status_code == 200


class TestSemAutoCadastro:
    def test_nao_existe_rota_de_cadastro(self, client):
        for caminho in ("/cadastro/", "/registro/", "/accounts/signup/"):
            resposta = client.get(caminho)
            assert resposta.status_code == 404, caminho


class TestCabecalhosSeguranca:
    def test_cabecalhos_de_seguranca(self, django_web, client):
        from django.contrib.auth import get_user_model

        get_user_model().objects.create_user(username="pregoeiro2", password="senha-forte-123")
        client.force_login(get_user_model().objects.get(username="pregoeiro2"))

        resposta = client.get("/")
        assert resposta["X-Content-Type-Options"] == "nosniff"
        assert resposta["X-Frame-Options"] == "DENY"
