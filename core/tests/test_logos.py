"""Prova do contrato de logos por arquivo fixo (D-65..D-69): referências
sempre via static(), alt derivado da identidade, placeholders SVG válidos.

Asserts de identidade SEMPRE contra settings, nunca strings literais —
o mesmo teste precisa passar em qualquer sistema gerado do template.
"""

from pathlib import Path

from django.conf import settings
from django.templatetags.static import static
from django.test import Client, TestCase, override_settings

from core.models import Usuario


@override_settings(SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class LogosNoShellTests(TestCase):
    """D-68/D-69 — logos do subsistema e da entidade no shell autenticado."""

    def setUp(self):
        self.user = Usuario.objects.create_user(
            email="usuario@exemplo.org", password="correta-123"
        )

    def test_shell_referencia_logos_via_static(self):
        # D-68: logo do subsistema no cabeçalho da aside e no header mobile;
        # D-69: logo da entidade discreto no rodapé da aside. Sempre via
        # static() — nunca caminho literal (hashing do WhiteNoise).
        cliente = Client()
        cliente.force_login(self.user)

        conteudo = cliente.get("/").content.decode("utf-8")

        self.assertIn(static("img/logo-subsistema.svg"), conteudo)
        self.assertIn(static("img/logo-entidade.svg"), conteudo)

    def test_alt_do_logo_do_subsistema_deriva_da_identidade(self):
        # D-67: o alt vem do context processor identidade (settings), nunca
        # de literal de marca — o logo complementa o texto, não o substitui.
        cliente = Client()
        cliente.force_login(self.user)

        conteudo = cliente.get("/").content.decode("utf-8")

        self.assertIn('alt="Logo de ' + settings.SISTEMA_SIGLA, conteudo)


class LogoNoLoginTests(TestCase):
    """D-69 — logo da entidade acima do formulário de login (anônimo)."""

    def test_login_referencia_logo_da_entidade_via_static(self):
        conteudo = Client().get("/login/").content.decode("utf-8")

        self.assertIn(static("img/logo-entidade.svg"), conteudo)

    def test_login_linka_favicon_do_icone_pwa(self):
        # Favicon por contrato de arquivo existente (D-72): base.html
        # reaproveita o ícone PWA — zero arquivo novo.
        conteudo = Client().get("/login/").content.decode("utf-8")

        self.assertIn('rel="icon"', conteudo)
        self.assertIn(static("img/icon-192.png"), conteudo)


class PlaceholdersSVGTests(TestCase):
    """D-65/D-66 — os caminhos fixos existem com SVGs placeholder válidos."""

    DIRETORIO_IMG = Path(settings.BASE_DIR) / "core" / "static" / "img"

    def test_placeholders_svg_existem_e_sao_svg(self):
        # O contrato de customização é o NOME do arquivo: substituir a arte
        # mantendo nome e extensão, sem editar código.
        for nome in ("logo-entidade.svg", "logo-subsistema.svg"):
            with self.subTest(arquivo=nome):
                texto = (self.DIRETORIO_IMG / nome).read_text(encoding="utf-8")
                self.assertIn("<svg", texto)
                self.assertIn("viewBox", texto)
