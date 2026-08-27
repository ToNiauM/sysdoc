"""Regressão contra vazamento de comentários de template no HTML servido.

O lexer do Django casa `{#...#}` sem re.DOTALL: um comentário inline que
abre e fecha em linhas diferentes é emitido como TEXTO LITERAL na página —
foi assim que racional interno de segurança (CR-01, T-02-11) apareceu na
tela de login e no shell. Comentários multilinha devem usar
{% comment %}...{% endcomment %}; estes testes travam a invariante de que
nenhum `{#`/`#}` literal chega ao HTML renderizado.
"""

from django.test import Client, TestCase, override_settings

from core.models import Usuario


@override_settings(SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class ComentariosNaoVazamTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            email="usuario@exemplo.org", password="correta-123"
        )

    def test_login_renderizado_sem_delimitadores_de_comentario(self):
        client = Client()
        response = client.get("/login/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertNotIn("{#", html)
        self.assertNotIn("#}", html)

    def test_shell_autenticado_sem_delimitadores_de_comentario(self):
        client = Client()
        client.force_login(self.user)
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertNotIn("{#", html)
        self.assertNotIn("#}", html)

    def test_fragmento_htmx_do_login_sem_delimitadores_de_comentario(self):
        # O partial _login_form.html também volta sozinho no swap htmx do
        # POST inválido — o comentário vazado morava dentro do <form>, então
        # este caminho de render precisa da mesma garantia.
        client = Client()
        response = client.post(
            "/login/",
            {"email": "errado@exemplo.org", "password": "errada"},
            headers={"HX-Request": "true"},
        )
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertNotIn("{#", html)
        self.assertNotIn("#}", html)
