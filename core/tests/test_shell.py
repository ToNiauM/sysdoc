"""Prova do shell visual (CORE-04): navegação com item ativo, contrato
`trilha` dos breadcrumbs (D-12), blocos de página (D-11) e a regressão do
login centrado (Pitfall 11 — o centering saiu do body e migrou para o
wrapper do login.html).
"""

from django.conf import settings
from django.template.loader import render_to_string
from django.test import Client, TestCase, override_settings

from core.models import Usuario


@override_settings(SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class ShellTests(TestCase):
    def setUp(self):
        self.email = "usuario@exemplo.org"
        self.user = Usuario.objects.create_user(
            email=self.email, password="correta-123"
        )

    def test_raiz_autenticada_renderiza_nav_com_item_ativo_e_identidade(self):
        client = Client()
        client.force_login(self.user)
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        conteudo = response.content.decode("utf-8")
        # Navegação principal presente, com "Início" marcado como ativo na
        # raiz (request.path == url do shell).
        self.assertIn('aria-label="Navegação principal"', conteudo)
        self.assertIn('aria-current="page"', conteudo)
        # Rodapé da aside mostra o usuário logado; identidade vem do
        # context processor (D-16), nunca hard-coded no template.
        self.assertIn(self.email, conteudo)
        self.assertIn(settings.SISTEMA_NOME, conteudo)

    def test_raiz_sem_sessao_redireciona_para_login(self):
        # LoginRequiredMiddleware intacto (T-02-03) — o shell nunca vaza
        # para anônimos.
        client = Client()
        response = client.get("/")
        self.assertRedirects(
            response, "/login/?next=/", fetch_redirect_response=False
        )

    def test_contrato_trilha_link_no_meio_e_texto_puro_no_ultimo(self):
        # Contrato D-12: itens com `url` viram <a>; o último (sem url) vira
        # <span aria-current="page"> — texto puro, sem link.
        html = render_to_string(
            "core/_breadcrumbs.html",
            {
                "trilha": [
                    {"rotulo": "Início", "url": "/"},
                    {"rotulo": "Atual", "url": None},
                ]
            },
        )
        self.assertIn('<a href="/"', html)
        self.assertIn('<span aria-current="page">Atual</span>', html)
        self.assertNotIn(">Atual</a>", html)

    def test_blocos_do_shell_renderizam_titulo_e_breadcrumb_default(self):
        client = Client()
        client.force_login(self.user)
        conteudo = client.get("/").content.decode("utf-8")
        # Bloco titulo_pagina default dentro do <h1> do cabecalho_pagina.
        self.assertIn("<h1", conteudo)
        self.assertIn("Início</h1>", conteudo)
        # Trilha de exemplo do shell_view: item único, sem url — renderiza
        # como texto puro dentro do include de breadcrumbs.
        self.assertIn('<span aria-current="page">Início</span>', conteudo)

    def test_aside_desktop_visivel_por_css_sem_depender_de_js(self):
        # WR-02: a visibilidade desktop da aside é do CSS (md:!flex), nunca
        # estado Alpine — sem isso, cada full page load piscava a aside e
        # uma falha de JS escondia navegação, identidade e logout no
        # desktop. O Alpine fica só com a gaveta mobile (sidebarAberta).
        client = Client()
        client.force_login(self.user)
        conteudo = client.get("/").content.decode("utf-8")
        self.assertIn("md:!flex", conteudo)
        self.assertIn('x-show="sidebarAberta"', conteudo)
        # Nenhum x-show pode voltar a depender de um estado `desktop` de JS.
        self.assertNotIn('x-show="sidebarAberta || desktop"', conteudo)

    def test_login_continua_centrado_apos_body_perder_o_centering(self):
        # Regressão do Pitfall 11: o wrapper do login.html carrega o
        # centering que antes vivia no <body> do base.html.
        client = Client()
        response = client.get("/login/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("justify-center", response.content.decode("utf-8"))
