"""Contrato executável do tema escuro (critérios 1 e 2 do ROADMAP, plano 07-05).

Cobre o que é fácil de quebrar por edição descuidada: a ordem do script
síncrono no `<head>` (D-99), a ausência de nomes com o prefixo do padrão de
referência (D-93), a sobrevivência da chave de tema ao logout, e o
mapeamento de elevação escrito no próprio `shell.html`.

Onde a asserção depende de classe utilitária, o teste roda sobre a FONTE do
template (leitura do arquivo) ou sobre o HTML servido pelo Django — nunca
sobre o CSS compilado: com `darkMode: ["selector", '[data-tema="escuro"]']`
o Tailwind emite `:where([data-tema="escuro"], …)` e a forma da regra varia
entre variante e bloco de variável (RESEARCH.md, Pitfall 4).
"""

import re
from pathlib import Path

from django.conf import settings
from django.test import Client, TestCase, override_settings

from core.models import Usuario
from core.tema import COR_PAGE_ESCURO

BASE_HTML = Path(settings.BASE_DIR) / "core" / "templates" / "base.html"
SHELL_HTML = Path(settings.BASE_DIR) / "core" / "templates" / "core" / "shell.html"
LOGIN_HTML = Path(settings.BASE_DIR) / "core" / "templates" / "core" / "login.html"

# O prefixo do padrão de referência é montado a partir de partes soltas
# (nunca escrito por extenso neste arquivo-fonte): este teste é copiado
# verbatim para todo sistema gerado, e a palavra por extenso aqui entraria
# na própria varredura de neutralidade que audita esse prefixo
# (.template-tests/test_copier_copy.sh) — o caçador viraria o caçado.
_PREFIXO_HERDADO = "".join(["p", "c", "a"])
RE_PREFIXO_HERDADO = re.compile(rf"(?i)(?<!\w){_PREFIXO_HERDADO}(?!\w)")


def _corpo_limpar_cache_pwa(html: str) -> str:
    """Extrai o corpo de `limparCachePwa` do HTML servido, no mesmo padrão
    de `core/tests/test_pwa.py` (busca por índice, sem depender de parser
    de JS)."""
    inicio = html.index("function limparCachePwa")
    fim = html.index("\n    }", inicio)
    return html[inicio:fim]


@override_settings(SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class OrdemDoScriptDeTemaTests(TestCase):
    """D-99 — o script que grava data-tema tem que rodar ANTES de qualquer
    CSS existir, senão o usuário vê um flash de tema a cada carregamento."""

    def test_data_tema_vem_antes_do_link_do_tailwind(self):
        cliente = Client()

        corpo = cliente.get("/login/").content.decode("utf-8")

        self.assertIn("data-tema", corpo)
        self.assertIn("dist/tailwind.css", corpo)
        self.assertLess(
            corpo.index("data-tema"),
            corpo.index("dist/tailwind.css"),
            "O script que grava data-tema tem que vir ANTES do <link> do "
            "Tailwind (D-99) — senão a primeira pintura sai sempre no tema "
            "claro e o usuário vê um flash branco antes do escuro aparecer.",
        )

    def test_data_tema_vem_antes_do_tema_css_injetado(self):
        # --cor-brand: só existe no <style> de tema_css (plano 07-04); é um
        # marcador que não aparece no script de tema (que só grava o
        # ATRIBUTO data-tema, nunca a string "--cor-brand:").
        cliente = Client()

        corpo = cliente.get("/login/").content.decode("utf-8")

        self.assertIn("--cor-brand:", corpo)
        self.assertLess(corpo.index("data-tema"), corpo.index("--cor-brand:"))

    def test_script_de_tema_nao_e_deferido_nem_assincrono(self):
        cliente = Client()

        corpo = cliente.get("/login/").content.decode("utf-8")

        # Volta da ocorrência de "aplicarTema" até a tag <script> mais
        # próxima e confere que ELA (a tag de abertura, não o corpo) não
        # tem defer nem async.
        indice_aplicar_tema = corpo.index("aplicarTema")
        trecho_antes = corpo[max(0, indice_aplicar_tema - 200) : indice_aplicar_tema]
        abertura = trecho_antes.rfind("<script")
        self.assertNotEqual(abertura, -1, "não encontrei a tag <script> que contém aplicarTema")
        tag_completa = trecho_antes[abertura:]
        self.assertNotIn("defer", tag_completa)
        self.assertNotIn("async", tag_completa)


@override_settings(SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class NomesNeutrosTests(TestCase):
    """D-93 — todo identificador com o prefixo do padrão de referência
    tem que ter sido renomeado neste template."""

    def setUp(self):
        self.user = Usuario.objects.create_user(
            email="usuario@exemplo.org", password="correta-123"
        )

    def test_html_do_login_nao_contem_prefixo_herdado(self):
        cliente = Client()

        corpo = cliente.get("/login/").content.decode("utf-8")

        self.assertNotRegex(corpo, RE_PREFIXO_HERDADO)

    def test_html_autenticado_nao_contem_prefixo_herdado(self):
        cliente = Client()
        cliente.force_login(self.user)

        corpo = cliente.get("/").content.decode("utf-8")

        self.assertNotRegex(corpo, RE_PREFIXO_HERDADO)

    def test_chave_de_localstorage_e_literalmente_tema(self):
        cliente = Client()

        corpo = cliente.get("/login/").content.decode("utf-8")

        self.assertIn('localStorage.setItem("tema"', corpo)
        self.assertIn('localStorage.getItem("tema")', corpo)


@override_settings(SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class ChaveDeTemaSobreviveAoLogoutTests(TestCase):
    """A preferência de tema não é dado de sessão (D-99, T-07-14) — apagá-la
    no logout faria o usuário perder o tema escuro a cada saída."""

    def setUp(self):
        self.user = Usuario.objects.create_user(
            email="usuario@exemplo.org", password="correta-123"
        )

    def test_limpar_cache_pwa_nao_remove_a_chave_de_tema(self):
        cliente = Client()
        cliente.force_login(self.user)

        corpo = cliente.get("/").content.decode("utf-8")
        corpo_funcao = _corpo_limpar_cache_pwa(corpo)

        self.assertNotIn(
            '"tema"',
            corpo_funcao,
            "limparCachePwa() passou a mexer na chave de tema — a "
            "preferência visual não é dado de sessão (D-99); removê-la no "
            "logout é regressão, não simetria.",
        )


@override_settings(SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class MetaThemeColorTests(TestCase):
    """O <meta theme-color> tem id fixo e acompanha o tema; o theme_color do
    MANIFEST (core/views.py, travado por core/tests/test_pwa.py) é outro
    valor, independente (Pitfall 14)."""

    def test_meta_tem_id_e_valor_claro_por_default(self):
        cliente = Client()

        corpo = cliente.get("/login/").content.decode("utf-8")

        self.assertIn(
            f'<meta name="theme-color" id="meta-theme-cor" content="{settings.COR_PRIMARIA}">',
            corpo,
        )


class SemHexLiteralNoBaseHtmlTests(TestCase):
    """A cor escura do <meta theme-color> vem de {{ cor_page_escuro }},
    NUNCA de um hex literal — core/templates é a árvore inteiramente livre
    de hex que o gate do critério 3 (plano 07-06) vai exigir."""

    def test_fonte_de_base_html_nao_tem_hex_literal(self):
        fonte = BASE_HTML.read_text(encoding="utf-8")

        self.assertFalse(
            re.search(r"#[0-9a-fA-F]{6}", fonte),
            "base.html ganhou um hex literal — a cor escura do <meta "
            "theme-color> tem que vir de {{ cor_page_escuro }} (canal do "
            "plano 07-04), senão o gate do critério 3 no plano 07-06 "
            "reprova (! grep -rnE \"#[0-9a-fA-F]{6}\" core/templates apps).",
        )
        self.assertIn("cor_page_escuro", fonte)

    def test_canal_cor_page_escuro_chega_de_ponta_a_ponta_no_html_servido(self):
        # Prova que o valor de core.tema.COR_PAGE_ESCURO (não um hex
        # qualquer) está de fato interpolado dentro do script servido.
        cliente = Client()

        corpo = cliente.get("/login/").content.decode("utf-8")

        self.assertIn(COR_PAGE_ESCURO, corpo)


@override_settings(SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class ControleDeTemaAcessivelTests(TestCase):
    """O controle de 3 estados no rodapé da aside precisa ser localizável
    por leitor de tela: role="group", aria-label e aria-pressed por botão."""

    def setUp(self):
        self.user = Usuario.objects.create_user(
            email="usuario@exemplo.org", password="correta-123"
        )

    def test_shell_autenticado_tem_grupo_de_tema_com_tres_botoes_marcados(self):
        cliente = Client()
        cliente.force_login(self.user)

        corpo = cliente.get("/").content.decode("utf-8")

        self.assertIn('role="group"', corpo)
        self.assertIn('aria-label="Tema"', corpo)
        # Alpine renderiza :aria-pressed como atributo LITERAL no HTML
        # servido (a diretiva não é avaliada no servidor) — é isso que
        # provamos aqui; a avaliação em tempo de execução (true/false)
        # acontece só no navegador.
        self.assertEqual(corpo.count(":aria-pressed"), 3)


class ElevacaoEscuraDeclaradaTests(TestCase):
    """Critério 1 — elevação no escuro é luminosidade, não sombra; os
    consumidores do `core` (card do shell, card do login) sobem para o
    nível Elevado com o par dark:bg-surface-2 / sem sombra."""

    def test_card_do_shell_tem_elevacao_escura(self):
        html = SHELL_HTML.read_text(encoding="utf-8")
        self.assertIn("dark:bg-surface-2", html)

    def test_card_do_login_tem_elevacao_escura(self):
        html = LOGIN_HTML.read_text(encoding="utf-8")
        self.assertIn("dark:bg-surface-2", html)

    def test_mapeamento_de_elevacao_esta_documentado_no_shell(self):
        html = SHELL_HTML.read_text(encoding="utf-8")
        self.assertIn("Flutuante", html)

    @override_settings(SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
    def test_variante_dark_aparece_no_html_servido(self):
        user = Usuario.objects.create_user(
            email="usuario@exemplo.org", password="correta-123"
        )
        cliente = Client()
        cliente.force_login(user)

        corpo = cliente.get("/").content.decode("utf-8")

        self.assertIn("dark:", corpo)
