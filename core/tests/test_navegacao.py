"""Prova da inclusion tag {% item_nav %} (NAV-01/NAV-02/NAV-03): resolve rota
opcional sem quebrar (T-07-08), escapa o rótulo (T-07-05), nunca aceita markup
de ícone como argumento (T-07-06) e decide o estado ativo com desempate
explícito — ver core/templatetags/navegacao.py.

A topologia pai/filho é exercitada contra um urlconf sintético declarado neste
próprio módulo (`urlpatterns`, aplicado por `@override_settings(ROOT_URLCONF)`).
Motivo: o defeito do G-01 só aparece quando um item leva `prefixo` e OUTRO item
do menu tem URL exata sob esse prefixo. Amarrar essa forma às rotas do app
exemplo deixaria a suíte do núcleo dependente de `incluir_app_exemplo=true`; o
urlconf sintético reproduz a mesma forma e roda nas duas variantes de geração.
A prova com o stub REAL que o núcleo semeia vive em
`apps/exemplo/tests/test_nav_ativo.py`.
"""

import re
from unittest import mock

from django.http import HttpResponse
from django.template import Context, Template, TemplateDoesNotExist, engines
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import include, path

TAG_ANCORA = re.compile(r"<a\b[^>]*>", re.S)


def _view_falsa(request):  # pragma: no cover - só existe para o reverse()
    return HttpResponse("")


# Urlconf sintético: `/x/` tem item próprio no menu e `/x/y/` também; `/x/z/`
# e `/x/42/editar/` são rotas-filhas sem item próprio. É a forma mínima em que
# a colisão do G-01 pode acontecer.
_sintetico = (
    [
        path("x/", _view_falsa, name="pai"),
        path("x/y/", _view_falsa, name="filho"),
        path("x/z/", _view_falsa, name="primo"),
        path("x/<int:pk>/editar/", _view_falsa, name="neto"),
    ],
    "sintetico",
)

urlpatterns = [path("", include(_sintetico))]


class ItemNavTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _renderizar(self, request, rota, rotulo, icone="", prefixo="", excecoes=""):
        template = Template(
            "{% load navegacao %}"
            "{% item_nav rota rotulo icone prefixo excecoes %}"
        )
        contexto = Context(
            {
                "request": request,
                "rota": rota,
                "rotulo": rotulo,
                "icone": icone,
                "prefixo": prefixo,
                "excecoes": excecoes,
            }
        )
        return template.render(contexto)

    def test_rota_existente_com_path_igual_a_url_fica_ativo(self):
        request = self.factory.get("/")

        html = self._renderizar(request, "core:shell", "Início", "casa")

        self.assertIn('aria-current="page"', html)
        self.assertIn("bg-brand-tint text-brand-ink", html)

    def test_rota_existente_com_path_diferente_fica_inativo(self):
        request = self.factory.get("/login/")

        html = self._renderizar(request, "core:shell", "Início", "casa")

        self.assertNotIn('aria-current="page"', html)
        self.assertIn("text-ink-2 hover:bg-surface-2", html)

    def test_rota_inexistente_nao_levanta_e_renderiza_vazio(self):
        request = self.factory.get("/")

        html = self._renderizar(request, "inexistente:rota", "Fantasma")

        self.assertEqual(html.strip(), "")
        self.assertNotIn("<a", html)

    def test_icone_desconhecido_renderiza_item_sem_svg_e_sem_erro(self):
        request = self.factory.get("/")

        html = self._renderizar(request, "core:shell", "Início", "nao-existe")

        self.assertIn("<a", html)
        self.assertIn("<span>Início</span>", html)
        self.assertNotIn("<svg", html)

    def test_rotulo_com_script_sai_escapado(self):
        request = self.factory.get("/")

        html = self._renderizar(request, "core:shell", "<script>alert(1)</script>")

        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


@override_settings(ROOT_URLCONF=__name__)
class DesempateDeItemAtivoTests(SimpleTestCase):
    """Exato vence prefixo, e a exceção é declarada no sítio da chamada (G-01).

    O teste antigo `test_prefixo_marca_ativo_em_rota_filha` usava
    `rota="core:shell"` com `prefixo="/exemplo/"` — a única combinação do
    universo em que a colisão é impossível, porque a URL exata do item (`/`)
    nunca está sob o prefixo declarado. Por isso ele passava com o defeito vivo
    (IN-07). Aqui o item DONO do prefixo tem URL sob o prefixo, como no stub
    real.
    """

    def setUp(self):
        self.factory = RequestFactory()

    def _renderizar(self, caminho, rota, prefixo="", excecoes=""):
        template = Template(
            "{% load navegacao %}"
            "{% item_nav rota 'Item' 'lista' prefixo excecoes %}"
        )
        return template.render(
            Context(
                {
                    "request": self.factory.get(caminho),
                    "rota": rota,
                    "prefixo": prefixo,
                    "excecoes": excecoes,
                }
            )
        )

    def _esta_ativo(self, caminho, rota, prefixo="", excecoes=""):
        return 'aria-current="page"' in self._renderizar(
            caminho, rota, prefixo, excecoes
        )

    def test_prefixo_marca_ativo_em_rota_filha(self):
        """O `prefixo` existe para isto e continua fazendo o trabalho."""
        self.assertTrue(
            self._esta_ativo("/x/42/editar/", "sintetico:pai", prefixo="/x/")
        )

    def test_excecao_desativa_o_item_na_rota_irma_que_tem_item_proprio(self):
        self.assertFalse(
            self._esta_ativo(
                "/x/y/", "sintetico:pai", prefixo="/x/", excecoes="/x/y/"
            )
        )

    def test_excecao_nao_alcanca_outra_rota_filha(self):
        self.assertTrue(
            self._esta_ativo(
                "/x/z/", "sintetico:pai", prefixo="/x/", excecoes="/x/y/"
            )
        )

    def test_excecao_nao_alcanca_a_propria_url_do_dono_do_prefixo(self):
        self.assertTrue(
            self._esta_ativo("/x/", "sintetico:pai", prefixo="/x/", excecoes="/x/y/")
        )

    def test_correspondencia_exata_nunca_e_anulada_pela_propria_excecao(self):
        """Uma exceção mal escrita não pode apagar o item dono da rota."""
        self.assertTrue(
            self._esta_ativo(
                "/x/y/", "sintetico:filho", prefixo="/x/", excecoes="/x/y/"
            )
        )

    def test_varias_excecoes_separadas_por_espaco(self):
        self.assertFalse(
            self._esta_ativo(
                "/x/z/", "sintetico:pai", prefixo="/x/", excecoes="/x/y/ /x/z/"
            )
        )

    def test_dois_itens_do_mesmo_prefixo_nao_acendem_juntos(self):
        """A forma do G-01 em miniatura: menu com pai (prefixo + exceção) e
        filho (URL exata sob o prefixo), renderizados no mesmo template."""
        menu = Template(
            "{% load navegacao %}"
            "{% item_nav 'sintetico:filho' 'Filho' 'grafico' %}"
            "{% item_nav 'sintetico:pai' 'Pai' 'lista' '/x/' '/x/y/' %}"
        )
        html = menu.render(Context({"request": self.factory.get("/x/y/")}))

        ativas = [t for t in TAG_ANCORA.findall(html) if 'aria-current="page"' in t]
        self.assertEqual(
            html.count('aria-current="page"'),
            1,
            f"dois itens acesos ao mesmo tempo em /x/y/: {ativas}",
        )
        self.assertIn('href="/x/y/"', ativas[0])


class ItemNavSemRequestTests(SimpleTestCase):
    """WR-02: `context["request"]` levantava `KeyError` em qualquer render fora
    do ciclo de request — `render_to_string()` sem `request=`, template de
    e-mail, geração de PDF, comando de management. Sem request não há caminho
    atual: o item renderiza INATIVO, nunca derruba o render."""

    def test_contexto_sem_request_renderiza_item_inativo(self):
        template = Template(
            "{% load navegacao %}{% item_nav 'core:shell' 'Início' 'casa' %}"
        )

        html = template.render(Context({}))

        self.assertIn("<a", html)
        self.assertIn("<span>Início</span>", html)
        self.assertNotIn('aria-current="page"', html)

    def test_contexto_sem_request_com_prefixo_tambem_nao_levanta(self):
        template = Template(
            "{% load navegacao %}"
            "{% item_nav 'core:shell' 'Itens' 'lista' '/exemplo/' %}"
        )

        html = template.render(Context({}))

        self.assertNotIn('aria-current="page"', html)


class NavDominioTolerantesTests(SimpleTestCase):
    """WR-10: `core/_nav_dominio.html` pertence ao derivado e o stub anuncia
    isso em letras maiúsculas — apagá-lo é um estado previsto. O `{% include %}`
    do Django com string literal levanta `TemplateDoesNotExist` (não existe
    `ignore missing`, isso é Jinja2), o que virava 500 em TODA página que
    estende `shell.html`."""

    def _render(self, contexto=None):
        return Template("{% load navegacao %}{% nav_dominio %}").render(
            Context(contexto or {})
        )

    def test_arquivo_ausente_devolve_vazio_em_vez_de_levantar(self):
        with mock.patch(
            "core.templatetags.navegacao.get_template",
            side_effect=TemplateDoesNotExist("core/_nav_dominio.html"),
        ):
            self.assertEqual(self._render(), "")

    def test_contexto_chega_ao_arquivo_incluido(self):
        """`context.flatten()` é o que faz `request` e o resto do contexto
        alcançarem os `{% item_nav %}` de dentro do arquivo do domínio."""
        alvo = engines["django"].from_string("[{{ marcador }}]")

        with mock.patch(
            "core.templatetags.navegacao.get_template", return_value=alvo
        ):
            html = self._render({"marcador": "ok"})

        self.assertEqual(html, "[ok]")

    def test_markup_do_arquivo_incluido_nao_sai_escapado(self):
        alvo = engines["django"].from_string('<a href="/x/">Item</a>')

        with mock.patch(
            "core.templatetags.navegacao.get_template", return_value=alvo
        ):
            html = self._render()

        self.assertIn('<a href="/x/">Item</a>', html)
        self.assertNotIn("&lt;a", html)
