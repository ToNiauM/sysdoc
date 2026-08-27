"""Testes da auditoria padrão com django-simple-history (CORE-06 / D-21/D-22)."""

from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from core.models import Usuario


class HistoricoDeUsuarioTests(TestCase):
    """Prova que a tabela HistoricalUsuario está viva: toda escrita via ORM
    gera um registro histórico (register(Usuario) em core/admin.py — D-22)."""

    def test_criar_usuario_gera_registro_historico_de_criacao(self):
        usuario = Usuario.objects.create_user(
            email="auditado@example.com", password="senha-segura"
        )

        self.assertEqual(usuario.history.count(), 1)
        # "+" = criação no vocabulário do simple-history.
        self.assertEqual(usuario.history.first().history_type, "+")

    def test_historico_nunca_snapshota_password_nem_last_login(self):
        # WR-01: `excluded_fields` em core/admin.py. Sem a exclusão, todo
        # save (inclusive o `update_last_login` de cada login) copiaria o
        # hash Argon2 para core_historicalusuario — um dump do banco
        # exporia o histórico completo de hashes (senhas antigas, atacáveis
        # offline mesmo após rotação). Este teste trava a ausência das duas
        # colunas no modelo histórico.
        campos = {
            campo.name for campo in Usuario.history.model._meta.get_fields()
        }
        self.assertNotIn("password", campos)
        self.assertNotIn("last_login", campos)


@override_settings(SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class HistoryRequestMiddlewareTests(TestCase):
    """Prova que mudanças via request registram o autor (history_user) —
    contrato do HistoryRequestMiddleware posicionado após o auth (T-02-08)."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = Usuario.objects.create_superuser(
            email="admin@example.com", password="senha-segura"
        )
        cls.alvo = Usuario.objects.create_user(
            email="alvo@example.com", password="senha-segura"
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.superuser)

    def test_edicao_via_admin_registra_history_user(self):
        # POST completo do change form do UserAdmin: campos dos fieldsets
        # reescritos (sem campo de login padrão); date_joined usa o widget
        # SplitDateTime do admin (dois inputs _0/_1).
        data_entrada = timezone.localtime(self.alvo.date_joined)
        response = self.client.post(
            f"/admin/core/usuario/{self.alvo.pk}/change/",
            {
                "email": self.alvo.email,
                "first_name": "Alterado",
                "last_name": "",
                "is_active": "on",
                "date_joined_0": data_entrada.strftime("%d/%m/%Y"),
                "date_joined_1": data_entrada.strftime("%H:%M:%S"),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.alvo.refresh_from_db()
        self.assertEqual(self.alvo.first_name, "Alterado")

        registro = self.alvo.history.first()  # mais recente primeiro
        self.assertEqual(registro.history_type, "~")
        self.assertEqual(registro.history_user, self.superuser)

    def test_middleware_posicionado_depois_do_auth(self):
        indice_auth = settings.MIDDLEWARE.index(
            "django.contrib.auth.middleware.AuthenticationMiddleware"
        )
        indice_history = settings.MIDDLEWARE.index(
            "simple_history.middleware.HistoryRequestMiddleware"
        )

        # Sem o auth antes, request.user não existiria na hora de gravar o
        # autor — a ordem relativa é parte do contrato de auditoria.
        self.assertLess(indice_auth, indice_history)
