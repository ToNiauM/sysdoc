"""Prova da PWA (CORE-05): manifest parametrizado pelos settings (D-18),
service worker de raiz com estratégia segura de cache (D-19), ícones
placeholder válidos (D-20) e integração no base.html (V3: hx-history
desligado no body).

Asserts de identidade SEMPRE contra settings, nunca strings literais —
o mesmo teste precisa passar em qualquer sistema gerado do template.
"""

import struct
from pathlib import Path

from django.conf import settings
from django.templatetags.static import static
from django.test import Client, TestCase, override_settings

from core.models import Usuario


class ManifestPWATests(TestCase):
    """D-18 — manifest.json por view, público, resolvido via static()."""

    def test_manifest_sem_login_retorna_200_com_content_type_de_manifest(self):
        cliente = Client()  # sem force_login — a rota é pública (T-02-13)

        resposta = cliente.get("/manifest.json")

        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(
            resposta["Content-Type"].startswith("application/manifest+json")
        )

    def test_manifest_identidade_vem_dos_settings(self):
        cliente = Client()

        corpo = cliente.get("/manifest.json").json()

        self.assertEqual(corpo["name"], settings.SISTEMA_NOME)
        self.assertEqual(corpo["short_name"], settings.SISTEMA_SIGLA)
        self.assertEqual(corpo["theme_color"], settings.COR_PRIMARIA)
        self.assertEqual(corpo["start_url"], "/")
        self.assertEqual(corpo["display"], "standalone")

    def test_manifest_icones_src_igual_ao_static_resolvido(self):
        # Pitfall 3: o hashing do WhiteNoise renomeia os PNGs no
        # collectstatic — o src de cada ícone precisa ser exatamente o que
        # static() resolve em runtime, nunca um caminho literal.
        cliente = Client()

        corpo = cliente.get("/manifest.json").json()
        srcs = [icone["src"] for icone in corpo["icons"]]

        self.assertIn(static("img/icon-192.png"), srcs)
        self.assertIn(static("img/icon-512.png"), srcs)
        self.assertIn(static("img/icon-512-maskable.png"), srcs)


class ServiceWorkerPWATests(TestCase):
    """D-19 — sw.js na raiz (fora de /static/), com escopo liberado."""

    def test_sw_sem_login_retorna_200_com_content_type_e_header_de_escopo(self):
        cliente = Client()  # sem force_login — a rota é pública (T-02-13)

        resposta = cliente.get("/sw.js")

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta["Content-Type"], "application/javascript")
        self.assertEqual(resposta["Service-Worker-Allowed"], "/")

    def test_sw_precacheia_offline_e_usa_cache_name_versionado(self):
        cliente = Client()

        corpo = cliente.get("/sw.js").content.decode()

        self.assertIn("static-v1", corpo)
        self.assertIn(static("offline.html"), corpo)
        self.assertIn("skipWaiting", corpo)

    def test_sw_navegacao_usa_fallback_e_nunca_grava_html_em_cache(self):
        # T-02-10: navegações (HTML) usam network-first com fallback para a
        # página offline — o branch de navigate NÃO pode conter cache.put
        # (gravar HTML autenticado no Cache Storage vazaria conteúdo após
        # o logout). O único put permitido fica no branch restrito a
        # /static/.
        cliente = Client()

        corpo = cliente.get("/sw.js").content.decode()

        self.assertIn('"navigate"', corpo)
        inicio = corpo.index('"navigate"')
        # O branch de navegação termina no primeiro `return;` após o if.
        fim = corpo.index("return;", inicio)
        branch_navegacao = corpo[inicio:fim]
        self.assertIn("caches.match(OFFLINE_URL)", branch_navegacao)
        self.assertNotIn(".put(", branch_navegacao)
        # O cache-first com preenchimento existe, mas só sob /static/.
        self.assertIn('startsWith("/static/")', corpo)


class IconesPWATests(TestCase):
    """D-20 — ícones placeholder gerados por ops/gerar_icones_pwa.py.

    Sem depender de Pillow (que não está no container web): lê os 24
    primeiros bytes de cada PNG e decodifica largura/altura do chunk IHDR
    na mão — assinatura de 8 bytes + comprimento de 4 + tipo de chunk de
    4 + largura de 4 + altura de 4.
    """

    DIRETORIO_IMG = Path(settings.BASE_DIR) / "core" / "static" / "img"

    ASSINATURA_PNG = b"\x89PNG\r\n\x1a\n"

    def _dimensoes(self, nome_arquivo):
        caminho = self.DIRETORIO_IMG / nome_arquivo
        with caminho.open("rb") as arquivo:
            dados = arquivo.read(24)
        self.assertEqual(dados[:8], self.ASSINATURA_PNG, nome_arquivo)
        return struct.unpack(">II", dados[16:24])

    def test_icon_192_e_quadrado_de_192(self):
        self.assertEqual(self._dimensoes("icon-192.png"), (192, 192))

    def test_icon_512_e_quadrado_de_512(self):
        self.assertEqual(self._dimensoes("icon-512.png"), (512, 512))

    def test_icon_512_maskable_e_quadrado_de_512(self):
        self.assertEqual(self._dimensoes("icon-512-maskable.png"), (512, 512))


@override_settings(SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class IntegracaoBasePWATests(TestCase):
    """Integração no base.html: manifest linkado e histórico htmx desligado."""

    def setUp(self):
        self.user = Usuario.objects.create_user(
            email="usuario@exemplo.org", password="correta-123"
        )

    def test_shell_autenticado_linka_manifest_e_desliga_historico_htmx(self):
        cliente = Client()
        cliente.force_login(self.user)

        conteudo = cliente.get("/").content.decode("utf-8")

        self.assertIn('rel="manifest"', conteudo)
        # V3 (T-02-11): sem snapshot de HTML autenticado no localStorage.
        self.assertIn('hx-history="false"', conteudo)
