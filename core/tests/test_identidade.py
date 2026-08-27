"""Prova do contrato de identidade (CORE-04 / D-16): settings validados no
boot e context processor `identidade` entregando nome/sigla/cor a todo
template — as plans seguintes (shell, admin, PWA) dependem deste contrato.
"""

from django.conf import settings
from django.test import Client, TestCase, override_settings


@override_settings(SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class IdentidadeTests(TestCase):
    def test_cor_primaria_respeita_formato_rrggbb(self):
        # A validação de boot só deixa passar #RRGGBB — se este teste falhar,
        # a barreira contra CSS injection via .env (T-02-01) foi removida.
        self.assertRegex(settings.COR_PRIMARIA, r"^#[0-9a-fA-F]{6}$")

    def test_context_processor_expoe_identidade_em_qualquer_template(self):
        # /login/ é a única rota pública — se a identidade chega lá sem a
        # view passá-la, o context processor está registrado e funcionando.
        response = Client().get("/login/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["sistema_nome"], settings.SISTEMA_NOME)
        self.assertEqual(response.context["sistema_sigla"], settings.SISTEMA_SIGLA)
        self.assertEqual(response.context["cor_primaria"], settings.COR_PRIMARIA)

    def test_context_processor_registrado_nos_settings(self):
        self.assertIn(
            "core.context_processors.identidade",
            settings.TEMPLATES[0]["OPTIONS"]["context_processors"],
        )
