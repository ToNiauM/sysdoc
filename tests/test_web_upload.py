"""
Suíte de upload e autorização por objeto (D-08, D-09, D-10, T-07-05-* —
07-CONTEXT.md / 07-05-PLAN.md).

Requer Django instalado; módulo inteiro pulado via `pytest.importorskip` se
ausente. O import de `sysdoc_web.processos.forms` no topo do módulo é, por
si só, a asserção de que o par MultipleFileInput/MultipleFileField não
reintroduz o `ValueError` de `ClearableFileInput` com múltiplos arquivos em
tempo de import (o blocker travado pelo plan-checker desta fase).
"""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

pytest.importorskip("django")

from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402

import sysdoc  # noqa: E402

# Nota: `sysdoc_web.processos.forms` importa `.models`, que exige o registro
# de apps do Django já populado (`django.setup()`). Isso só acontece dentro
# do fixture `django_web` — pytest importa todos os módulos de teste na fase
# de coleta, antes de qualquer fixture rodar, então um `import` deste módulo
# aqui no topo do arquivo levantaria `AppRegistryNotReady` mesmo com Django
# instalado. A assertão de import fica em `test_duas_pecas_separadas_chegam_
# ao_disco`, depois que `cliente`/`django_web` já inicializaram o Django —
# mesma restrição já documentada no 07-02-SUMMARY.md sobre
# `pytest.importorskip` em nível de módulo.


def _pdf(nome: str, tamanho: int = 32) -> SimpleUploadedFile:
    conteudo = b"%PDF-1.4\n" + b"0" * max(0, tamanho - 9)
    return SimpleUploadedFile(nome, conteudo, content_type="application/pdf")


def _docx_valido(nome: str) -> SimpleUploadedFile:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as pacote:
        pacote.writestr(
            "word/document.xml",
            "<w:document xmlns:w='ns'><w:body><w:p/></w:body></w:document>",
        )
        pacote.writestr("[Content_Types].xml", "<Types/>")
    return SimpleUploadedFile(
        nome,
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


def _docx_com_entrada_hostil(nome: str) -> SimpleUploadedFile:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as pacote:
        pacote.writestr("word/document.xml", "<w:document/>")
        pacote.writestr("../fora.xml", "conteudo hostil")
    return SimpleUploadedFile(
        nome,
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


def _docx_sem_document_xml(nome: str) -> SimpleUploadedFile:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as pacote:
        pacote.writestr("outro/arquivo.xml", "<a/>")
    return SimpleUploadedFile(
        nome,
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@pytest.fixture
def usuario(django_web):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user, _ = User.objects.get_or_create(username="pregoeiro-upload")
    return user


@pytest.fixture
def outro_usuario(django_web):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user, _ = User.objects.get_or_create(username="pregoeiro-upload-outro")
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


class TestPdfUnico:
    def test_pdf_unico_cria_processo_e_pasta(self, cliente, raiz_processos):
        from sysdoc_web.processos.models import Processo

        resposta = cliente.post(
            "/processos/novo/",
            {"nome": "Processo PDF único", "documento_unico": _pdf("processo.pdf")},
        )

        assert resposta.status_code == 302
        assert "/verificacao/" in resposta["Location"]

        processo = Processo.objects.get(nome="Processo PDF único")
        assert processo.criado_por.username == "pregoeiro-upload"

        pasta_documentos = raiz_processos / processo.slug / "documentos"
        arquivos = list(pasta_documentos.iterdir())
        assert len(arquivos) == 1


class TestRecusas:
    def test_extensao_nao_suportada_e_recusada(self, cliente, raiz_processos):
        from sysdoc_web.processos.models import Processo

        arquivo = SimpleUploadedFile(
            "malicioso.exe", b"MZ\x90\x00conteudo", content_type="application/octet-stream"
        )
        resposta = cliente.post(
            "/processos/novo/", {"nome": "Processo Hostil", "documento_unico": arquivo}
        )

        assert resposta.status_code == 200
        assert Processo.objects.count() == 0
        assert not any(raiz_processos.iterdir())
        assert b"Traceback" not in resposta.content

    def test_arquivo_acima_do_limite_e_recusado(self, cliente, raiz_processos, monkeypatch):
        from django.conf import settings

        from sysdoc_web.processos.models import Processo

        monkeypatch.setattr(settings, "SYSDOC_WEB_MAX_UPLOAD_MB", 1)
        arquivo = _pdf("grande.pdf", tamanho=2 * 1024 * 1024)

        resposta = cliente.post(
            "/processos/novo/", {"nome": "Processo Grande", "documento_unico": arquivo}
        )

        assert resposta.status_code == 200
        assert Processo.objects.count() == 0
        assert b"1 MB" in resposta.content

    def test_nome_com_traversal_e_sanitizado(self, cliente, raiz_processos):
        from sysdoc_web.processos.models import Processo

        arquivo = _pdf("../../../etc/passwd.pdf")
        resposta = cliente.post(
            "/processos/novo/", {"nome": "Processo Traversal", "documento_unico": arquivo}
        )

        assert resposta.status_code == 302
        processo = Processo.objects.get(nome="Processo Traversal")
        pasta_documentos = raiz_processos / processo.slug / "documentos"
        arquivos = list(pasta_documentos.iterdir())
        assert len(arquivos) == 1
        nome_gravado = arquivos[0].name
        assert "/" not in nome_gravado
        assert ".." not in nome_gravado
        assert arquivos[0].parent == pasta_documentos

    def test_docx_com_entrada_hostil_e_recusado(self, cliente, raiz_processos):
        from sysdoc_web.processos.models import Processo

        arquivo = _docx_com_entrada_hostil("modelo.docx")
        resposta = cliente.post(
            "/processos/novo/", {"nome": "Processo Docx Hostil", "documento_unico": arquivo}
        )

        assert resposta.status_code == 200
        assert Processo.objects.count() == 0

    def test_docx_sem_document_xml_e_recusado(self, cliente, raiz_processos):
        from sysdoc_web.processos.models import Processo

        arquivo = _docx_sem_document_xml("modelo.docx")
        resposta = cliente.post(
            "/processos/novo/", {"nome": "Processo Docx Vazio", "documento_unico": arquivo}
        )

        assert resposta.status_code == 200
        assert Processo.objects.count() == 0

    def test_quantidade_acima_do_maximo_e_recusada(
        self, cliente, raiz_processos, monkeypatch
    ):
        from django.conf import settings

        from sysdoc_web.processos.models import Processo

        monkeypatch.setattr(settings, "SYSDOC_WEB_MAX_ARQUIVOS", 2)
        pecas = [_pdf(f"peca-{i}.pdf") for i in range(3)]

        resposta = cliente.post(
            "/processos/novo/", {"nome": "Processo Muitas Peças", "pecas": pecas}
        )

        assert resposta.status_code == 200
        assert Processo.objects.count() == 0

    def test_as_duas_vias_juntas_sao_recusadas(self, cliente, raiz_processos):
        from sysdoc_web.processos.models import Processo

        resposta = cliente.post(
            "/processos/novo/",
            {
                "nome": "Processo Duas Vias",
                "documento_unico": _pdf("unico.pdf"),
                "pecas": [_pdf("etp.pdf"), _pdf("tr.pdf")],
            },
        )

        assert resposta.status_code == 200
        assert Processo.objects.count() == 0
        assert "não os dois" in resposta.content.decode("utf-8")


class TestVerificacao:
    def test_verificacao_grava_tipo_no_config_do_projeto(self, cliente, raiz_processos):
        from sysdoc_web.processos import servicos
        from sysdoc_web.processos.models import Processo

        resposta_criacao = cliente.post(
            "/processos/novo/",
            {"nome": "Processo TIC", "documento_unico": _pdf("processo.pdf")},
        )
        assert resposta_criacao.status_code == 302

        processo = Processo.objects.get(nome="Processo TIC")

        resposta = cliente.post(
            f"/processos/{processo.slug}/verificacao/", {"tipo": "tic"}
        )
        assert resposta.status_code == 302

        processo.refresh_from_db()
        assert processo.tipo_verificacao == "tic"

        paths = servicos.caminhos(processo.slug)
        assert sysdoc.resolver_tipo_verificacao(paths) == "tic"


class TestAutorizacaoPorObjeto:
    def test_processo_de_outro_usuario_da_404(
        self, cliente, outro_usuario, raiz_processos
    ):
        from django.test import Client

        from sysdoc_web.processos import servicos
        from sysdoc_web.processos.models import Processo

        slug = "processo-de-outro"
        servicos.criar_pasta_do_processo(slug)
        Processo.objects.create(
            nome="Processo de outro dono", slug=slug, criado_por=outro_usuario
        )

        resposta = cliente.get(f"/processos/{slug}/verificacao/")
        assert resposta.status_code == 404

    def test_anonimo_e_redirecionado_para_login(self, django_web, raiz_processos):
        from django.test import Client

        cliente_anonimo = Client()
        resposta = cliente_anonimo.get("/processos/novo/")
        assert resposta.status_code == 302
        assert resposta["Location"].startswith("/entrar/")

    def test_post_sem_csrf_e_recusado(self, django_web, usuario, raiz_processos):
        from django.test import Client

        cliente_estrito = Client(enforce_csrf_checks=True)
        cliente_estrito.force_login(usuario)

        resposta = cliente_estrito.post(
            "/processos/novo/",
            {"nome": "Processo Sem Csrf", "documento_unico": _pdf("processo.pdf")},
        )
        assert resposta.status_code == 403


class TestPecasSeparadas:
    def test_duas_pecas_separadas_chegam_ao_disco(self, cliente, raiz_processos):
        # O import por si só é a asserção de que o par MultipleFileInput/
        # MultipleFileField não reintroduz o ValueError de
        # ClearableFileInput com múltiplos arquivos.
        import sysdoc_web.processos.forms  # noqa: F401
        from sysdoc_web.processos.models import Processo

        pecas = [_pdf("ETP.pdf"), _pdf("TR.pdf")]
        resposta = cliente.post(
            "/processos/novo/", {"nome": "Processo Peças Separadas", "pecas": pecas}
        )

        assert resposta.status_code == 302
        processo = Processo.objects.get(nome="Processo Peças Separadas")
        pasta_documentos = raiz_processos / processo.slug / "documentos"
        nomes = sorted(arquivo.name for arquivo in pasta_documentos.iterdir())
        assert nomes == ["ETP.pdf", "TR.pdf"]
