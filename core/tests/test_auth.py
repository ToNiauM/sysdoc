"""Testes unitários de `core.models.UsuarioManager` (CORE-01)."""

from django.test import TestCase

from core.models import Usuario


class UsuarioManagerTests(TestCase):
    def test_create_user_sem_email_levanta_value_error(self):
        with self.assertRaises(ValueError):
            Usuario.objects.create_user(email="", password="qualquer")

    def test_create_user_normaliza_email_e_grava_senha_com_set_password(self):
        user = Usuario.objects.create_user(
            email="Usuario@Exemplo.ORG", password="senha_em_texto_claro"
        )

        self.assertEqual(user.email, "Usuario@exemplo.org")
        # Nunca texto plano — `set_password` sempre grava um hash.
        self.assertNotEqual(user.password, "senha_em_texto_claro")
        self.assertTrue(user.check_password("senha_em_texto_claro"))

    def test_create_superuser_com_is_staff_false_explicito_levanta_value_error(
        self,
    ):
        with self.assertRaises(ValueError):
            Usuario.objects.create_superuser(
                email="admin@exemplo.org",
                password="qualquer",
                is_staff=False,
            )
