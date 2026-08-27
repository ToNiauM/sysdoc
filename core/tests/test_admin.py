"""Testes do admin com identidade do sistema (CORE-03 / D-13 / D-14 / A1)."""

from django.conf import settings
from django.contrib import admin
from django.test import Client, TestCase, override_settings

from core.admin_site import SistemaAdminSite
from core.models import Usuario


@override_settings(SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class SistemaAdminSiteTests(TestCase):
    """Prova que o default_site via AdminConfig substitui `admin.site` sem
    tocar `config/urls.py` (D-13) e que a identidade vem dos settings."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = Usuario.objects.create_superuser(
            email="admin@example.com", password="senha-segura"
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.superuser)

    def test_admin_site_e_instancia_de_sistema_admin_site(self):
        # `admin.site` é LazyObject; isinstance dispara a resolução e prova
        # que SistemaAdminConfig.default_site foi honrado.
        self.assertIsInstance(admin.site, SistemaAdminSite)

    def test_indice_do_admin_exibe_nome_do_sistema(self):
        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, settings.SISTEMA_NOME)

    def test_indice_do_admin_injeta_tema_com_cor_primaria(self):
        response = self.client.get("/admin/")

        # O <style> do bloco extrastyle (override cirúrgico, D-14) carrega a
        # variável --primary com a cor validada no boot.
        self.assertContains(response, f"--primary: {settings.COR_PRIMARIA}")

    def test_changelist_de_usuario_esta_registrada(self):
        response = self.client.get("/admin/core/usuario/")

        self.assertEqual(response.status_code, 200)


@override_settings(SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class GatePadraoDoAdminTests(TestCase):
    """A1: o template mantém o gate padrão do Django (`is_active and
    is_staff`) — sem gate superuser. Este teste trava a decisão: qualquer
    mudança futura de semântica de acesso precisa ser explícita."""

    def test_staff_nao_superuser_acessa_o_admin(self):
        staff = Usuario.objects.create_user(
            email="staff@example.com", password="senha-segura", is_staff=True
        )
        client = Client()
        client.force_login(staff)

        response = client.get("/admin/")

        self.assertEqual(response.status_code, 200)

    def test_anonimo_e_redirecionado_para_login(self):
        response = Client().get("/admin/")

        self.assertEqual(response.status_code, 302)
