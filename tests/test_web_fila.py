"""
Fila single-slot, saneamento de subida e ponte de biblioteca (D-03, D-14,
D-15, D-16, D-17, D-18 — 07-CONTEXT.md).

Requer Django instalado; módulo inteiro pulado via `pytest.importorskip` se
ausente. Nenhum teste faz chamada de rede real: `sysdoc.prepare` e
`sysdoc_dvi.pipeline.executar_run` são sempre monkeypatchados nos testes que
exercitam o worker.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

pytest.importorskip("django")

import sysdoc  # noqa: E402
from sysdoc_dvi import pipeline  # noqa: E402
from sysdoc_dvi.progresso import EventoProgresso  # noqa: E402


@pytest.fixture
def usuario(django_web):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user, _ = User.objects.get_or_create(email="pregoeiro-fila@exemplo.org")
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
def processo(django_web, usuario, raiz_processos):
    from sysdoc_web.processos.models import Processo

    return Processo.objects.create(
        nome="Processo Teste",
        slug="processo-teste",
        tipo_verificacao="geral",
        criado_por=usuario,
    )


@pytest.fixture
def outro_processo(django_web, usuario, raiz_processos):
    from sysdoc_web.processos.models import Processo

    return Processo.objects.create(
        nome="Outro Processo",
        slug="outro-processo",
        tipo_verificacao="geral",
        criado_por=usuario,
    )


class TestFilaSingleSlot:
    def test_segunda_analise_e_recusada(self, processo, outro_processo):
        from sysdoc_web.processos import fila

        fila.enfileirar(processo)
        with pytest.raises(fila.FilaOcupada):
            fila.enfileirar(outro_processo)

    def test_apos_conclusao_nova_analise_e_aceita(self, processo, outro_processo):
        from sysdoc_web.processos import fila

        job = fila.enfileirar(processo)
        fila.concluir(job, "concluida")

        novo_job = fila.enfileirar(outro_processo)
        assert novo_job.status == "na_fila"

    def test_reivindicacao_e_atomica(self, processo):
        from sysdoc_web.processos import fila

        job = fila.enfileirar(processo)

        primeiro = fila.reivindicar_proximo()
        assert primeiro is not None
        assert primeiro.pk == job.pk
        assert primeiro.status == "em_execucao"

        segundo = fila.reivindicar_proximo()
        assert segundo is None


class TestSaneamento:
    def test_saneamento_marca_interrompida(self, processo):
        from sysdoc_web.processos import fila
        from sysdoc_web.processos.models import AnaliseJob

        job = fila.enfileirar(processo)
        AnaliseJob.objects.filter(pk=job.pk).update(status="em_execucao")

        contagem = fila.sanear_jobs_orfaos()

        job.refresh_from_db()
        assert contagem == 1
        assert job.status == "interrompida"
        assert job.concluido_em is not None
        assert "reiniciado" in job.mensagem_erro


class TestWorkerBibliotecaChamavel:
    def test_worker_executa_pipeline_como_biblioteca(self, processo, monkeypatch):
        from django.core.management import call_command

        from sysdoc_web.processos import fila

        recebido: dict[str, object] = {}

        def _prepare_falso(caminho):
            return 0

        def _executar_run_falso(projeto, tipo=None, progresso=None, **kwargs):
            recebido["progresso"] = progresso
            progresso(EventoProgresso(etapa="itens", mensagem="1/7", atual=3, total=7))
            progresso(EventoProgresso(etapa="itens", mensagem="1/7", atual=3, total=7))
            return 0

        monkeypatch.setattr(sysdoc, "prepare", _prepare_falso)
        monkeypatch.setattr(pipeline, "executar_run", _executar_run_falso)

        job = fila.enfileirar(processo)

        call_command("runworker", "--uma-vez")

        job.refresh_from_db()
        assert job.status == "concluida"
        assert job.itens_concluidos == 3
        assert job.itens_total == 7
        assert "Analisando o processo" in job.etapa
        assert "3 de 7" in job.etapa
        assert recebido["progresso"] is not None

    def test_falha_do_pipeline_nao_vaza_detalhe_tecnico(self, processo, monkeypatch):
        from django.core.management import call_command

        from sysdoc_web.processos import fila
        from sysdoc_web.processos.management.commands.runworker import MENSAGEM_FALHA

        def _prepare_falso(caminho):
            return 0

        def _executar_run_falso(projeto, tipo=None, progresso=None, **kwargs):
            raise RuntimeError("chave de API ausente para o provedor 'openrouter'")

        monkeypatch.setattr(sysdoc, "prepare", _prepare_falso)
        monkeypatch.setattr(pipeline, "executar_run", _executar_run_falso)

        job = fila.enfileirar(processo)

        call_command("runworker", "--uma-vez")

        job.refresh_from_db()
        assert job.status == "falhou"
        assert job.mensagem_erro == MENSAGEM_FALHA
        for proibido in ("openrouter", "Traceback", "RuntimeError", "/"):
            assert proibido not in job.mensagem_erro


class TestPontesDeDisco:
    def test_pasta_do_processo_e_projeto_sysdoc_valido(self, django_web, raiz_processos):
        from sysdoc_web.processos import servicos

        slug = "processo-cli-valido"
        pasta = servicos.criar_pasta_do_processo(slug)
        servicos.definir_tipo_verificacao(slug, "geral")

        tipo = sysdoc.resolver_tipo_verificacao(sysdoc.project_paths(pasta))
        assert tipo == "geral"

    def test_gravar_campos_despacho_ignora_chave_estranha(self, django_web, raiz_processos):
        from sysdoc_web.processos import servicos

        slug = "processo-despacho"
        pasta = servicos.criar_pasta_do_processo(slug)
        servicos.gravar_campos_despacho(
            slug, {"unidade": "SEPAT", "comando_shell": "rm -rf /"}
        )

        config = sysdoc.load_config(sysdoc.project_paths(pasta))
        assert config["despacho"]["unidade"] == "SEPAT"
        assert "comando_shell" not in config["despacho"]

    @pytest.mark.parametrize(
        "slug_malicioso", ["../fora", "..%2Ffora", "a/../../b", "/etc"]
    )
    def test_caminho_do_processo_rejeita_traversal(
        self, django_web, raiz_processos, slug_malicioso
    ):
        from django.core.exceptions import SuspiciousOperation

        from sysdoc_web.processos import servicos

        with pytest.raises(SuspiciousOperation):
            servicos.caminho_do_processo(slug_malicioso)


class TestLockDoBanco:
    def test_lock_do_banco_vira_fila_ocupada(self, processo, monkeypatch):
        from django.db.utils import OperationalError

        from sysdoc_web.processos import fila
        from sysdoc_web.processos.models import AnaliseJob

        chamadas = {"n": 0}

        def _create_sempre_travado(**kwargs):
            chamadas["n"] += 1
            raise OperationalError("database is locked")

        monkeypatch.setattr(AnaliseJob.objects, "create", _create_sempre_travado)
        monkeypatch.setattr(fila.time, "sleep", lambda segundos: None)

        with pytest.raises(fila.FilaOcupada):
            fila.enfileirar(processo)
        assert chamadas["n"] > 1

    def test_lock_do_banco_resolve_na_segunda_tentativa(self, processo, monkeypatch):
        from django.db.utils import OperationalError

        from sysdoc_web.processos import fila
        from sysdoc_web.processos.models import AnaliseJob

        original_create = AnaliseJob.objects.create
        chamadas = {"n": 0}

        def _create_falha_uma_vez(**kwargs):
            chamadas["n"] += 1
            if chamadas["n"] == 1:
                raise OperationalError("database is locked")
            return original_create(**kwargs)

        monkeypatch.setattr(AnaliseJob.objects, "create", _create_falha_uma_vez)
        monkeypatch.setattr(fila.time, "sleep", lambda segundos: None)

        job = fila.enfileirar(processo)
        assert isinstance(job, AnaliseJob)
        assert job.pk is not None
