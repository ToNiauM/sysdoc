"""
Suíte da tela 3: disparo da análise, progresso por polling e tradução de
falha (D-14, D-15, D-16, D-17 — 07-CONTEXT.md / 07-06-PLAN.md).

Requer Django instalado; módulo inteiro pulado via `pytest.importorskip` se
ausente. Nenhum teste faz chamada de rede real: o worker (`manage.py
runworker`) nunca é acionado aqui — os jobs são manipulados diretamente pelo
ORM ou por `sysdoc_web.processos.fila`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

pytest.importorskip("django")


@pytest.fixture
def usuario(django_web):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user, _ = User.objects.get_or_create(username="pregoeiro-progresso")
    return user


@pytest.fixture
def outro_usuario(django_web):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user, _ = User.objects.get_or_create(username="pregoeiro-progresso-outro")
    return user


@pytest.fixture(autouse=True)
def _banco_limpo(django_web):
    from sysdoc_web.processos.models import AnaliseJob, Processo

    AnaliseJob.objects.all().delete()
    Processo.objects.all().delete()
    yield
    AnaliseJob.objects.all().delete()
    Processo.objects.all().delete()


@pytest.fixture
def raiz_processos(tmp_path, monkeypatch):
    from django.conf import settings

    destino = tmp_path / "sysdoc_processos"
    destino.mkdir()
    monkeypatch.setattr(settings, "SYSDOC_PROCESSOS_DIR", destino)
    return destino


@pytest.fixture
def cliente(django_web, usuario, raiz_processos):
    from django.test import Client

    cliente = Client()
    cliente.force_login(usuario)
    return cliente


@pytest.fixture
def processo(django_web, usuario, raiz_processos):
    from sysdoc_web.processos.models import Processo

    return Processo.objects.create(
        nome="Processo Progresso",
        slug="processo-progresso",
        tipo_verificacao="geral",
        criado_por=usuario,
    )


@pytest.fixture
def processo_sem_tipo(django_web, usuario, raiz_processos):
    from sysdoc_web.processos.models import Processo

    return Processo.objects.create(
        nome="Processo Sem Tipo",
        slug="processo-sem-tipo",
        criado_por=usuario,
    )


@pytest.fixture
def outro_processo(django_web, usuario, raiz_processos):
    from sysdoc_web.processos.models import Processo

    return Processo.objects.create(
        nome="Outro Processo Progresso",
        slug="outro-processo-progresso",
        tipo_verificacao="geral",
        criado_por=usuario,
    )


@pytest.fixture
def processo_de_outro_usuario(django_web, outro_usuario, raiz_processos):
    from sysdoc_web.processos.models import Processo

    return Processo.objects.create(
        nome="Processo de Outro Usuário",
        slug="processo-de-outro-usuario",
        tipo_verificacao="geral",
        criado_por=outro_usuario,
    )


class TestIniciarAnalise:
    def test_iniciar_sem_tipo_e_recusado(self, cliente, processo_sem_tipo):
        from sysdoc_web.processos.models import AnaliseJob

        resposta = cliente.post(
            f"/processos/{processo_sem_tipo.slug}/analise/iniciar/", follow=True
        )

        assert resposta.status_code == 200
        assert resposta.redirect_chain[0][1] == 302
        assert AnaliseJob.objects.count() == 0
        assert "tipo de contratação" in resposta.content.decode("utf-8")

    def test_iniciar_cria_job_na_fila(self, cliente, processo):
        from sysdoc_web.processos.models import AnaliseJob

        resposta = cliente.post(f"/processos/{processo.slug}/analise/iniciar/")

        assert resposta.status_code == 302
        assert AnaliseJob.objects.count() == 1
        job = AnaliseJob.objects.get()
        assert job.status == "na_fila"
        assert job.processo_id == processo.pk

    def test_segunda_analise_mostra_aviso_e_nao_500(
        self, cliente, processo, outro_processo
    ):
        from sysdoc_web.processos import fila

        fila.enfileirar(processo)

        resposta = cliente.post(
            f"/processos/{outro_processo.slug}/analise/iniciar/", follow=True
        )

        assert resposta.redirect_chain[0][1] == 302
        assert resposta.status_code == 200
        assert "análise em andamento" in resposta.content.decode("utf-8")

    def test_iniciar_por_get_e_recusado(self, cliente, processo):
        resposta = cliente.get(f"/processos/{processo.slug}/analise/iniciar/")

        assert resposta.status_code == 405


class TestSituacaoAnalise:
    def test_situacao_devolve_json_em_portugues(self, cliente, processo):
        from sysdoc_web.processos.models import AnaliseJob

        AnaliseJob.objects.create(
            processo=processo,
            status="em_execucao",
            etapa="Analisando o processo (3 de 7)",
            itens_concluidos=3,
            itens_total=7,
        )

        resposta = cliente.get(f"/processos/{processo.slug}/analise/situacao/")

        assert resposta.status_code == 200
        assert resposta["Content-Type"].startswith("application/json")
        dados = resposta.json()
        assert set(dados.keys()) == {
            "status",
            "situacao",
            "etapa",
            "percentual",
            "concluida",
            "sucesso",
            "mensagem",
            "url_resultado",
        }
        assert dados["percentual"] == 42
        assert "3 de 7" in dados["etapa"]

    def test_situacao_nao_vaza_dado_tecnico(self, cliente, processo):
        from sysdoc_web.processos.management.commands.runworker import MENSAGEM_FALHA
        from sysdoc_web.processos.models import AnaliseJob

        AnaliseJob.objects.create(
            processo=processo, status="falhou", mensagem_erro=MENSAGEM_FALHA
        )

        resposta = cliente.get(f"/processos/{processo.slug}/analise/situacao/")

        corpo = resposta.content.decode("utf-8").lower()
        for proibido in (
            "openrouter",
            "anthropic",
            "gpt",
            "claude",
            "traceback",
            "sysdoc_dvi",
            "/dados",
            ".json",
        ):
            assert proibido not in corpo

    def test_situacao_marca_conclusao_com_url_de_resultado(self, cliente, processo):
        from sysdoc_web.processos.models import AnaliseJob

        AnaliseJob.objects.create(processo=processo, status="concluida")

        resposta = cliente.get(f"/processos/{processo.slug}/analise/situacao/")

        dados = resposta.json()
        assert dados["concluida"] is True
        assert dados["sucesso"] is True
        assert dados["url_resultado"].startswith("/processos/")

    def test_job_interrompido_e_reportado_como_tal(self, cliente, processo):
        from sysdoc_web.processos import fila
        from sysdoc_web.processos.models import AnaliseJob

        job = fila.enfileirar(processo)
        AnaliseJob.objects.filter(pk=job.pk).update(status="em_execucao")

        fila.sanear_jobs_orfaos()

        resposta = cliente.get(f"/processos/{processo.slug}/analise/situacao/")

        dados = resposta.json()
        assert dados["sucesso"] is False
        assert dados["concluida"] is True
        assert "reiniciado" in dados["mensagem"]

    def test_situacao_de_outro_usuario_da_404(
        self, cliente, processo_de_outro_usuario
    ):
        resposta = cliente.get(
            f"/processos/{processo_de_outro_usuario.slug}/analise/situacao/"
        )

        assert resposta.status_code == 404

    def test_situacao_nao_e_cacheavel(self, cliente, processo):
        resposta = cliente.get(f"/processos/{processo.slug}/analise/situacao/")

        assert "no-store" in resposta["Cache-Control"]
