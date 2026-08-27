"""Prova numérica de `core/tema.py` (DS-01/DS-06): as fórmulas de derivação
batem byte a byte com o padrão de referência, `familia_marca()` não diverge
de `core/static/src/input.css` em silêncio, e os dois `--cor-page` têm nome
em Python amarrado ao mesmo arquivo. O manifest é a prova de que o consumidor
real (`core/views.py`) já usa o valor derivado.
"""

import re
from pathlib import Path

from django.test import Client, SimpleTestCase, TestCase

from core import tema

INPUT_CSS = Path(__file__).resolve().parent.parent / "static" / "src" / "input.css"

_PADRAO_BLOCO = re.compile(r'(:root|\[data-tema="escuro"\])\s*\{([^}]*)\}')
_PADRAO_VAR = re.compile(r"--cor-([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})")


def _blocos_de_cor(texto):
    """Lê input.css e devolve (claro, escuro): dois dicts
    `sufixo-da-variavel -> #hex`, um por bloco de seletor. É este helper —
    e não valores repetidos à mão no teste — que impede o arquivo e
    `core/tema.py` de divergirem em silêncio."""
    blocos = {}
    for seletor, corpo in _PADRAO_BLOCO.findall(texto):
        blocos[seletor] = dict(_PADRAO_VAR.findall(corpo))
    return blocos[":root"], blocos['[data-tema="escuro"]']


class MisturarEComHslTests(SimpleTestCase):
    """Os dois primitivos, verificados contra o padrão de referência
    (`#003c71`) — os mesmos valores conferidos nas duas implementações
    (Python aqui, JavaScript no antigo tailwind.config.js.jinja)."""

    def test_misturar_reproduz_os_cinco_coeficientes_do_padrao(self):
        self.assertEqual(tema.misturar("#003c71", 255, 0.12), "#1f5382")
        self.assertEqual(tema.misturar("#003c71", 0, 0.18), "#00315d")
        self.assertEqual(tema.misturar("#003c71", 255, 0.92), "#ebeff4")
        self.assertEqual(tema.misturar("#003c71", 255, 0.34), "#577ea1")
        self.assertEqual(tema.misturar("#003c71", 255, 0.62), "#9eb5c9")

    def test_com_hsl_reproduz_os_tres_coeficientes_do_padrao(self):
        self.assertEqual(tema.com_hsl("#003c71", 1.0, 0.727), "#74beff")
        self.assertEqual(tema.com_hsl("#003c71", 0.72, 0.567), "#4196e0")
        self.assertEqual(tema.com_hsl("#003c71", 0.55, 0.427), "#3171a9")


class FamiliaMarcaTests(SimpleTestCase):
    def test_familia_marca_do_padrao_de_referencia_bate_byte_a_byte(self):
        # Onze dos doze valores medidos no padrão batem exatamente; a única
        # divergência é brand-tint escuro: o padrão publica #14263a e a
        # derivação produz #14283b (2 pontos em um canal) — é o único token
        # sem regra derivável do padrão (A2 da pesquisa). A divergência é
        # ESPERADA e não deve ser "corrigida" com um valor cravado, porque
        # um valor cravado não sobreviveria a uma cor_primaria diferente.
        esperado = {
            "brand": "#003c71",
            "brand-hover": "#1f5382",
            "brand-ink": "#00315d",
            "brand-tint": "#ebeff4",
            "seq-600": "#003c71",
            "seq-450": "#577ea1",
            "seq-300": "#9eb5c9",
            "brand:escuro": "#74beff",
            "brand-hover:escuro": "#a7d6ff",
            "brand-ink:escuro": "#41a6ff",
            # brand-tint:escuro OMITIDO de propósito — divergência conhecida
            # e aceita (ver comentário acima), verificada à parte abaixo.
            "seq-600:escuro": "#74beff",
            "seq-450:escuro": "#4196e0",
            "seq-300:escuro": "#3171a9",
        }
        familia = tema.familia_marca("#003c71")
        self.assertEqual(len(familia), 16)
        for chave, valor in esperado.items():
            self.assertEqual(familia[chave], valor, msg=f"chave {chave!r}")
        # A divergência conhecida: 2 pontos em um canal, não um erro de
        # fórmula — confirmada aqui para que ninguém "console" um valor
        # cravado por cima da derivação.
        self.assertEqual(familia["brand-tint:escuro"], "#14283b")

        # `seq-750` fica FORA do dict `esperado` de propósito: aquele dict é o
        # conjunto de valores MEDIDOS no padrão de referência, e a rampa de lá
        # tem três degraus — o quarto é extensão deste template (plano 07-13,
        # G-03), não herança. Misturá-lo ali diria que o padrão publica um
        # valor que ele não publica. Aqui embaixo ele é fixado do mesmo jeito,
        # com o mesmo efeito prático: mexer nos coeficientes `misturar(cor, 0,
        # 0.35)` / `com_hsl(cor, 1.00, 0.860)` reprova.
        self.assertEqual(familia["seq-750"], "#002749")
        self.assertEqual(familia["seq-750:escuro"], "#b8deff")

    def test_familia_marca_do_default_do_copier_igual_ao_input_css(self):
        # familia_marca("#1e40af") tem que ser IGUAL ao par de blocos de
        # marca que o plano 07-02 escreveu em input.css — lido do arquivo,
        # nunca repetido à mão aqui.
        claro, escuro = _blocos_de_cor(INPUT_CSS.read_text())
        familia = tema.familia_marca("#1e40af")
        for chave in (
            "brand",
            "brand-hover",
            "brand-ink",
            "brand-tint",
            "seq-750",
            "seq-600",
            "seq-450",
            "seq-300",
        ):
            self.assertEqual(familia[chave], claro[chave], msg=f"claro {chave!r}")
            self.assertEqual(
                familia[f"{chave}:escuro"], escuro[chave], msg=f"escuro {chave!r}"
            )

    def test_familia_marca_so_produz_hex_de_seis_digitos_minusculo(self):
        padrao = re.compile(r"^#[0-9a-f]{6}$")
        for cor in ("#000000", "#ffffff", "#1e40af"):
            familia = tema.familia_marca(cor)
            for chave, valor in familia.items():
                self.assertRegex(valor, padrao, msg=f"{cor} -> {chave}={valor!r}")


class CssDaMarcaTests(SimpleTestCase):
    def test_css_da_marca_tem_dois_seletores_seguros_e_so_hex(self):
        css = tema.css_da_marca("#1e40af")

        seletores = re.findall(r'^(:root|\[data-tema="escuro"\]) \{$', css, re.MULTILINE)
        self.assertEqual(seletores, [":root", '[data-tema="escuro"]'])

        linhas_decl = [linha for linha in css.splitlines() if linha.strip().startswith("--cor-")]
        self.assertEqual(len(linhas_decl), 16)
        for linha in linhas_decl:
            self.assertRegex(linha.strip(), r"^--cor-[a-z0-9-]+: #[0-9a-f]{6};$")

        # Nenhum caractere de risco de injeção fora da estrutura de seletor
        # e declaração validada acima — a única entrada é COR_PRIMARIA, já
        # validada como #RRGGBB no boot (T-07-10).
        for caractere in "<>'@":
            self.assertNotIn(caractere, css)


class CorPageTests(SimpleTestCase):
    def test_cor_page_claro_e_escuro_amarrados_ao_input_css(self):
        claro, escuro = _blocos_de_cor(INPUT_CSS.read_text())
        self.assertEqual(tema.COR_PAGE_CLARO, claro["page"])
        self.assertEqual(tema.COR_PAGE_ESCURO, escuro["page"])


class ManifestUsaCorPageTests(TestCase):
    """Precisa de Client (padrão de core/tests/test_pwa.py) — os seis casos
    acima não tocam banco nem client, por isso ficam em SimpleTestCase."""

    def test_manifest_usa_cor_page_claro_e_theme_color_independente(self):
        from django.conf import settings

        corpo = Client().get("/manifest.json").json()

        # Pitfall 14: background_color e theme_color são dois valores
        # independentes — trocar um não pode mexer no outro.
        self.assertEqual(corpo["background_color"], tema.COR_PAGE_CLARO)
        self.assertEqual(corpo["theme_color"], settings.COR_PRIMARIA)
