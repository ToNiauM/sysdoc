"""Gate de contraste do par TEXTO+FUNDO da marca (G-02, DS-01/DS-03/DS-06).

Por que este arquivo existe separado de `test_tema.py`: aquele prova que a
derivação de `core/tema.py` bate byte a byte com o padrão de referência —
equivalência de FÓRMULA. Este prova que o resultado RENDERIZADO é legível —
propriedade de ACESSIBILIDADE. Os dois podem passar e falhar
independentemente, e foi exatamente por só existir o primeiro que o G-02
atravessou a fase: `--cor-brand` do escuro estava "correto" em relação ao
padrão e ainda assim ilegível sob `text-white`.

A medida vem de `core/tests/contraste.py` (fonte única da fórmula WCAG 2.x
neste repositório) e os valores de token vêm de `tokens_do_input_css()` — do
arquivo, nunca repetidos à mão aqui. É o mesmo princípio do `_blocos_de_cor`
de `test_tema.py`: teste e fonte que se repetem divergem em silêncio.

Estrutura do defeito que este gate fecha: `familia_marca()` deriva
`brand:escuro` por `com_hsl(cor, 1.00, 0.727)`, que FIXA a luminosidade em
72,7% — sempre uma cor clara, para qualquer `COR_PRIMARIA`. Branco por cima
reprova AA sempre (2,56:1 com o default do template; 1,99:1 com `#003c71`;
1,76:1 no hover). Não é um valor infeliz de paleta, é estrutural — por isso o
gate roda sobre MAIS DE UMA cor, e não sobre a que está configurada.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.test import SimpleTestCase

from core import tema
from core.tests.contraste import contraste, tokens_do_input_css

RAIZ = Path(__file__).resolve().parents[2]
INPUT_CSS = RAIZ / "core" / "static" / "src" / "input.css"

# Três cores de referência, escolhidas para que o gate não dependa da que
# estiver configurada: o default do template, a do padrão de referência (onde
# o defeito do G-02 é PIOR — 1,99:1) e uma quente, de matiz oposto.
CORES_DE_REFERENCIA = ("#1e40af", "#003c71", "#b91c1c")

# WCAG 2.x AA para texto normal. O selo da paginação é `text-xs` (11px), bem
# abaixo do piso de "texto grande", então 3:1 não serviria nem como exceção.
PISO_AA = 4.5

# `bg-brand` EXATO — o lookahead recusa `bg-brand-hover`, `bg-brand-tint` e
# `bg-brand-ink`, que são outros tokens. O lookbehind recusa sufixos de um
# nome maior. `hover:bg-brand` casa de propósito: continua sendo fundo da
# marca.
BG_BRAND_RE = re.compile(r"(?<![\w-])bg-brand(?![\w-])")
TEXT_WHITE_RE = re.compile(r"(?<![\w-])text-white(?![\w-])")
TEXT_BRAND_TX_RE = re.compile(r"(?<![\w-])text-brand-tx(?![\w-])")

_CLASSE_RE = re.compile(r'class="([^"]*)"')
_APPLY_RE = re.compile(r"@apply([^;]*);")


def _linha_de(texto: str, posicao: int) -> int:
    return texto.count("\n", 0, posicao) + 1


def _tag_ao_redor(texto: str, posicao: int) -> str:
    """Trecho da tag HTML que contém `posicao` — usado só para ler
    `aria-hidden`, que é o que distingue fundo de marca DECORATIVO (o filete
    de 2px do item de navegação ativo, que não carrega texto nenhum) de fundo
    de marca com conteúdo."""
    inicio = texto.rfind("<", 0, posicao)
    fim = texto.find(">", posicao)
    if inicio == -1 or fim == -1:
        return ""
    return texto[inicio : fim + 1]


def _declaracoes_com_fundo_de_marca() -> list[tuple[str, int, str, bool]]:
    """Toda declaração de classe (HTML) ou `@apply` (CSS) que pinta `bg-brand`.

    Devolve `(rótulo, linha, declaração, decorativa)`. A varredura é sobre o
    VALOR do atributo `class` / o corpo do `@apply`, não sobre a linha inteira:
    varrer a linha produziria falso positivo em qualquer marcação que tivesse
    `bg-brand` num elemento e `text-white` em outro elemento vizinho. Pelo
    mesmo motivo, `bg-red-600 text-white` (modal de exclusão) e `bg-blue-700
    text-white` (formulário de login) nunca aparecem aqui: não são a marca, são
    a paleta default do Tailwind, e não são o defeito deste gate.
    """
    achados: list[tuple[str, int, str, bool]] = []

    alvos: list[Path] = []
    for diretorio in ("core/templates", "apps"):
        base = RAIZ / diretorio
        if base.exists():
            alvos.extend(sorted(base.rglob("*.html")))

    for caminho in alvos:
        texto = caminho.read_text(encoding="utf-8", errors="ignore")
        for m in _CLASSE_RE.finditer(texto):
            declaracao = m.group(1)
            if not BG_BRAND_RE.search(declaracao):
                continue
            tag = _tag_ao_redor(texto, m.start())
            decorativa = 'aria-hidden="true"' in tag
            achados.append(
                (
                    str(caminho.relative_to(RAIZ)),
                    _linha_de(texto, m.start()),
                    declaracao,
                    decorativa,
                )
            )

    if INPUT_CSS.exists():
        css = INPUT_CSS.read_text(encoding="utf-8")
        for m in _APPLY_RE.finditer(css):
            declaracao = m.group(1)
            if not BG_BRAND_RE.search(declaracao):
                continue
            # Um `@apply` nunca é decorativo por omissão: `.btn--primaria`
            # compõe com `.btn`, que traz `text-[13px] font-semibold`. Se a
            # exceção de `aria-hidden` valesse aqui, apagar o `text-white` sem
            # pôr nada no lugar fecharia o gate deixando o botão herdar a cor
            # do corpo sobre a marca clara.
            achados.append(
                (
                    "core/static/src/input.css",
                    _linha_de(css, m.start()),
                    declaracao,
                    False,
                )
            )

    return achados


class TokenDeTextoDaMarcaTests(SimpleTestCase):
    """`--cor-brand-tx` existe, inverte com o tema e é amarrado à página escura."""

    def setUp(self) -> None:
        self.claro, self.escuro = tokens_do_input_css()

    def test_brand_tx_declarado_nos_dois_blocos(self) -> None:
        self.assertIn(
            "brand-tx",
            self.claro,
            "--cor-brand-tx ausente do bloco :root de core/static/src/input.css — "
            "sem o par de TEXTO declarado, todo fundo de marca depende de um "
            "text-white cravado, que reprova AA no tema escuro (G-02)",
        )
        self.assertIn(
            "brand-tx",
            self.escuro,
            '--cor-brand-tx ausente do bloco [data-tema="escuro"] de '
            "core/static/src/input.css (G-02)",
        )

    def test_brand_tx_claro_e_branco(self) -> None:
        self.assertIn("brand-tx", self.claro, "--cor-brand-tx ausente do :root (G-02)")
        self.assertEqual(self.claro["brand-tx"], "#ffffff")

    def test_brand_tx_escuro_e_a_propria_pagina_escura(self) -> None:
        """T-07-32: os dois valores têm que continuar iguais.

        O par de texto sobre a marca clara é a tinta da página escura. Se
        alguém ajustar `--cor-page` do escuro e esquecer deste, os dois
        divergem em silêncio e a interface fica com dois "pretos" diferentes.
        A asserção lê os DOIS do arquivo — nenhum hex repetido aqui.
        """
        self.assertIn("brand-tx", self.escuro, "--cor-brand-tx ausente do escuro (G-02)")
        self.assertEqual(
            self.escuro["brand-tx"],
            self.escuro["page"],
            "--cor-brand-tx do escuro divergiu de --cor-page do escuro",
        )

    def test_brand_tx_tem_valor_proprio_no_escuro(self) -> None:
        """Não pode ser herança do claro: `tokens_do_input_css` funde os dois
        blocos, então um `brand-tx` só no `:root` apareceria no dict escuro
        valendo branco — e o gate de contraste reprovaria sem dizer por quê."""
        self.assertIn("brand-tx", self.escuro, "--cor-brand-tx ausente do escuro (G-02)")
        self.assertNotEqual(
            self.escuro["brand-tx"],
            self.claro.get("brand-tx"),
            'o escuro precisa declarar --cor-brand-tx próprio em [data-tema="escuro"]',
        )


class ContrasteDoParDaMarcaTests(SimpleTestCase):
    """As doze combinações: 3 `COR_PRIMARIA` × 2 temas × (repouso, hover).

    Cada uma vai em `subTest` com o valor medido na mensagem. Uma falha que só
    diz "False is not true" custa uma rodada inteira de investigação; esta diz
    qual cor, qual tema, qual estado e quantos ":1" faltaram.
    """

    def setUp(self) -> None:
        self.claro, self.escuro = tokens_do_input_css()

    def _brand_tx(self, chave_do_tema: str) -> str:
        bloco = self.claro if chave_do_tema == "claro" else self.escuro
        self.assertIn(
            "brand-tx",
            bloco,
            f"--cor-brand-tx ausente do bloco {chave_do_tema} de "
            "core/static/src/input.css — impossível medir o par texto/fundo "
            "da marca (G-02)",
        )
        return bloco["brand-tx"]

    def test_par_da_marca_passa_aa_nas_doze_combinacoes(self) -> None:
        for cor in CORES_DE_REFERENCIA:
            familia = tema.familia_marca(cor)
            casos = (
                ("claro", "repouso", familia["brand"]),
                ("claro", "hover", familia["brand-hover"]),
                ("escuro", "repouso", familia["brand:escuro"]),
                ("escuro", "hover", familia["brand-hover:escuro"]),
            )
            for tema_, estado, fundo in casos:
                with self.subTest(cor=cor, tema=tema_, estado=estado):
                    texto = self._brand_tx(tema_)
                    medido = contraste(texto, fundo)
                    self.assertGreaterEqual(
                        medido,
                        PISO_AA,
                        f"texto {texto} sobre fundo {fundo} mede {medido:.2f}:1, "
                        f"abaixo do piso AA de {PISO_AA}:1 "
                        f"(COR_PRIMARIA={cor}, tema={tema_}, estado={estado})",
                    )


class SemBrancoCravadoSobreAMarcaTests(SimpleTestCase):
    """A varredura estrutural: o gate numérico acima só vale se nenhum sítio
    escapar dele escrevendo a cor do texto à mão."""

    def test_nenhuma_declaracao_junta_bg_brand_com_text_white(self) -> None:
        violacoes = [
            f"{rotulo}:{linha} → {declaracao.strip()}"
            for rotulo, linha, declaracao, _ in _declaracoes_com_fundo_de_marca()
            if TEXT_WHITE_RE.search(declaracao)
        ]
        self.assertEqual(
            violacoes,
            [],
            "text-white sobre bg-brand reprova AA no tema escuro para qualquer "
            "COR_PRIMARIA (G-02) — use text-brand-tx:\n" + "\n".join(violacoes),
        )

    def test_todo_fundo_de_marca_com_conteudo_declara_text_brand_tx(self) -> None:
        """A simétrica positiva da anterior, e ela é indispensável.

        Sem esta, o gate de cima fecharia com alguém simplesmente APAGANDO o
        `text-white`: o botão passaria a herdar a cor do corpo (`text-ink`, que
        no escuro é `#eeeeee`, quase branco) sobre a marca clara — mesma
        ilegibilidade, agora sem nenhuma classe para grepar.

        Exceção única e explícita: fundo de marca DECORATIVO, marcado
        `aria-hidden="true"` — o filete de 2px do item de navegação ativo não
        contém texto e não tem par de texto para declarar.
        """
        faltando = [
            f"{rotulo}:{linha} → {declaracao.strip()}"
            for rotulo, linha, declaracao, decorativa in _declaracoes_com_fundo_de_marca()
            if not decorativa and not TEXT_BRAND_TX_RE.search(declaracao)
        ]
        self.assertEqual(
            faltando,
            [],
            "declaração com bg-brand e conteúdo textual sem text-brand-tx — o par "
            "de texto do fundo da marca tem que ser declarado, nunca herdado "
            "(G-02):\n" + "\n".join(faltando),
        )

    def test_a_varredura_enxerga_os_sitios_de_marca_do_artefato_de_referencia(self) -> None:
        """Prova da própria guarda: uma varredura que não acha nada passaria
        vazia e pareceria verde. Aqui exigimos que ela tenha encontrado ao menos
        o `.btn--primaria` do `input.css`, que existe em todo derivado —
        inclusive nos gerados sem o app de exemplo."""
        rotulos = {rotulo for rotulo, _, _, _ in _declaracoes_com_fundo_de_marca()}
        self.assertIn(
            "core/static/src/input.css",
            rotulos,
            "a varredura não encontrou nenhum @apply com bg-brand — o gate "
            "estaria passando por não olhar nada",
        )
