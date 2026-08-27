"""
Suíte da tela 4: apontamentos, revisão humana bloqueante e downloads
endurecidos (D-06, D-09, D-11, D-12, D-13 — 07-CONTEXT.md / 07-07-PLAN.md).

Requer Django instalado; módulo inteiro pulado via `pytest.importorskip` se
ausente. `sysdoc.criar_documento(..., "dvi")` é exercitado de verdade (não
mockado) contra `templates/dvi/despacho_geral.docx` do repositório — a prova
de que a revisão bloqueante é real precisa passar pelo caminho de produção
inteiro, não por um substituto.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

pytest.importorskip("django")

import sysdoc  # noqa: E402

DADOS_ANALISE = {
    "modelo_ia": "gpt-5-teste-resultado",
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
            "para": "texto sugerido",
            "parecer": "É necessário revisar a cláusula de garantia contratual.",
            "fundamento": "Lei 14.133/2021 art. 18.",
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
            "parecer": "Requisito atendido integralmente.",
            "fundamento": "Nenhuma pendência identificada.",
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
            "parecer": "Risco de sobrepreço identificado na pesquisa de mercado.",
            "fundamento": "Lei 14.133/2021 art. 40.",
            "classificação": "risco",
            "severidade": "crítica",
            "risco_jurídico": "bloqueante",
        },
    ],
}


@pytest.fixture
def usuario(django_web):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user, _ = User.objects.get_or_create(username="pregoeiro-resultado")
    return user


@pytest.fixture
def outro_usuario(django_web):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user, _ = User.objects.get_or_create(username="pregoeiro-resultado-outro")
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


def _criar_processo_com_resultado(usuario, slug, dados=DADOS_ANALISE):
    from sysdoc_web.processos import servicos
    from sysdoc_web.processos.models import AnaliseJob, Processo

    processo = Processo.objects.create(
        nome="Processo Resultado",
        slug=slug,
        tipo_verificacao="geral",
        criado_por=usuario,
    )
    servicos.criar_pasta_do_processo(slug)
    servicos.definir_tipo_verificacao(slug, "geral")
    paths = servicos.caminhos(slug)
    (paths.root / "dados_consolidados.json").write_text(
        json.dumps(dados, ensure_ascii=False), encoding="utf-8"
    )
    AnaliseJob.objects.create(processo=processo, status="concluida")
    return processo


@pytest.fixture
def processo_com_resultado(django_web, usuario, raiz_processos):
    return _criar_processo_com_resultado(usuario, "processo-resultado")


@pytest.fixture
def processo_de_outro_usuario(django_web, outro_usuario, raiz_processos):
    return _criar_processo_com_resultado(outro_usuario, "processo-resultado-outro")


class TestResultado:
    def test_resultado_lista_apontamentos_com_rotulos(self, cliente, processo_com_resultado):
        resposta = cliente.get(f"/processos/{processo_com_resultado.slug}/resultado/")

        assert resposta.status_code == 200
        corpo = resposta.content.decode("utf-8")
        assert "Ajuste necessário" in corpo
        assert "ajuste_necessário" not in corpo

    def test_resultado_nao_expoe_json_nem_modelo(self, cliente, processo_com_resultado):
        resposta = cliente.get(f"/processos/{processo_com_resultado.slug}/resultado/")

        corpo = resposta.content.decode("utf-8")
        assert "dados_consolidados" not in corpo
        assert "modelo_ia" not in corpo
        assert "gpt-5-teste-resultado" not in corpo

    def test_parecer_com_html_e_escapado(self, cliente, usuario, raiz_processos):
        dados = json.loads(json.dumps(DADOS_ANALISE))
        dados["itens"][0]["parecer"] = "<img src=x onerror=alert(1)>"
        processo = _criar_processo_com_resultado(usuario, "processo-xss", dados=dados)

        resposta = cliente.get(f"/processos/{processo.slug}/resultado/")

        corpo = resposta.content.decode("utf-8")
        assert "&lt;img" in corpo
        assert "<img src=x" not in corpo


class TestDespachoBloqueante:
    def test_analise_concluida_nao_gera_docx_sozinha(self, cliente, processo_com_resultado):
        from sysdoc_web.processos import servicos

        cliente.get(f"/processos/{processo_com_resultado.slug}/resultado/")

        paths = servicos.caminhos(processo_com_resultado.slug)
        assert list(paths.root.glob("*.docx")) == []

    def test_despacho_sem_confirmacao_nao_gera(self, cliente, processo_com_resultado):
        from sysdoc_web.processos import servicos

        resposta = cliente.post(
            f"/processos/{processo_com_resultado.slug}/despacho/",
            {"unidade": "SEPAT/COLOG"},
        )

        assert resposta.status_code == 200
        paths = servicos.caminhos(processo_com_resultado.slug)
        assert list(paths.root.glob("*.docx")) == []

    def test_despacho_com_confirmacao_gera_docx(self, cliente, processo_com_resultado):
        from sysdoc_web.processos import servicos

        resposta = cliente.post(
            f"/processos/{processo_com_resultado.slug}/despacho/",
            {"confirmo": "on", "unidade": "SEPAT/COLOG"},
        )

        assert resposta.status_code == 302
        paths = servicos.caminhos(processo_com_resultado.slug)
        docxs = list(paths.root.glob("*.docx"))
        assert docxs
        assert re.match(r"^\d{2}_.*_dvi_\d{4}-\d{2}-\d{2}\.docx$", docxs[0].name)
        config = sysdoc.load_config(paths)
        assert config["despacho"]["unidade"] == "SEPAT/COLOG"

    def test_campo_em_branco_vira_marcador(self, cliente, processo_com_resultado):
        from sysdoc_web.processos import servicos

        cliente.post(
            f"/processos/{processo_com_resultado.slug}/despacho/",
            {"confirmo": "on", "unidade": "SEPAT/COLOG", "signatario": ""},
        )

        paths = servicos.caminhos(processo_com_resultado.slug)
        config = sysdoc.load_config(paths)
        valores = sysdoc.valores_despacho(config)
        assert valores["despacho.signatario"] == "[PREENCHER: signatario]"


class TestDownloads:
    def test_download_html_e_attachment(self, cliente, processo_com_resultado):
        from sysdoc_web.processos import servicos

        paths = servicos.caminhos(processo_com_resultado.slug)
        (paths.root / "analise_gpt-5_2026-08-27.html").write_text(
            "<html></html>", encoding="utf-8"
        )

        resposta = cliente.get(f"/processos/{processo_com_resultado.slug}/baixar/analise/")

        assert resposta.status_code == 200
        assert resposta["Content-Disposition"].startswith("attachment;")
        assert resposta["X-Content-Type-Options"] == "nosniff"
        assert "sandbox" in resposta["Content-Security-Policy"]

    def test_download_docx_tem_tipo_correto(self, cliente, processo_com_resultado):
        from sysdoc_web.processos import servicos

        paths = servicos.caminhos(processo_com_resultado.slug)
        (paths.root / "01_processo-resultado_dvi_2026-08-27.docx").write_bytes(b"PK\x03\x04")

        resposta = cliente.get(f"/processos/{processo_com_resultado.slug}/baixar/despacho/")

        assert resposta.status_code == 200
        assert resposta["Content-Type"] == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    def test_download_sem_arquivo_da_404(self, cliente, processo_com_resultado):
        resposta = cliente.get(f"/processos/{processo_com_resultado.slug}/baixar/analise/")

        assert resposta.status_code == 404

    def test_download_de_outro_usuario_da_404(self, cliente, processo_de_outro_usuario):
        resposta = cliente.get(
            f"/processos/{processo_de_outro_usuario.slug}/baixar/analise/"
        )

        assert resposta.status_code == 404

    def test_nao_existe_rota_para_o_json(self, cliente, processo_com_resultado):
        resposta = cliente.get(f"/processos/{processo_com_resultado.slug}/baixar/dados/")

        assert resposta.status_code == 404


class TestEntregar:
    def test_entregar_recusa_caminho_fora_da_raiz(self, django_web, tmp_path):
        from django.core.exceptions import SuspiciousOperation

        from sysdoc_web.processos import downloads

        raiz = tmp_path / "raiz-permitida"
        raiz.mkdir()

        with pytest.raises(SuspiciousOperation):
            downloads.entregar(Path("/etc/passwd"), raiz, "passwd.txt", "text/plain")
