"""Deriva a família de marca inteira (claro e escuro) a partir de uma única
cor — `COR_PRIMARIA` do `.env` — e nomeia em Python os dois tokens neutros de
`--cor-page` que precisam existir fora do CSS.

Espelha o precedente de `core/admin_site.py:each_context`, que já monta uma
string `:root { ... }` a partir de `settings.COR_PRIMARIA` e a entrega
`|safe` a um template: o valor é seguro para interpolação em CSS porque
`config/settings/base.py` valida `COR_PRIMARIA` contra o formato `#RRGGBB`
no boot e levanta `ImproperlyConfigured` se o valor não casar. Nenhuma
função deste módulo aceita entrada de request — a única chamada em produção
parte de `settings.COR_PRIMARIA`, já validado.

Convenção de chave em `familia_marca()`: o tema claro usa a chave nua
(`"brand"`), o tema escuro usa a mesma chave com o sufixo `":escuro"`
(`"brand:escuro"`) — estável e documentada aqui para quem consumir o dict.
"""

from __future__ import annotations

import colorsys
from functools import lru_cache

# Tokens neutros — NÃO derivados de COR_PRIMARIA (não são família de marca).
# A fonte física continua sendo core/static/src/input.css (D-79); estas
# constantes são só o nome Python do mesmo valor, amarrado por teste em
# core/tests/test_tema.py para não divergir em silêncio. Existem porque dois
# consumidores precisam do valor FORA do CSS: o background_color do
# manifest (core/views.py) e o <meta theme-color> do tema escuro, escrito
# por um script que roda antes de qualquer CSS existir (D-99) — ali
# getComputedStyle devolveria vazio.
COR_PAGE_CLARO = "#f9f9f7"
COR_PAGE_ESCURO = "#0f0e0d"

# Ordem estável das 7 variáveis de marca — usada tanto para montar
# familia_marca() quanto para gerar css_da_marca() na mesma sequência.
# Atualização do plano 07-13: são 8 chaves desde que a rampa sequencial
# ganhou o degrau `seq-750` (as contagens "7" e "14" citadas nos textos
# acima e abaixo são as de antes desse acréscimo; os comentários herdados
# ficaram intactos de propósito, para que o diff prove que NENHUM
# coeficiente do padrão de referência foi tocado).
_CHAVES_MARCA = (
    "brand",
    "brand-hover",
    "brand-ink",
    "brand-tint",
    "seq-750",
    "seq-600",
    "seq-450",
    "seq-300",
)


def _canais(hex_: str) -> tuple[int, int, int]:
    """Divide `'#RRGGBB'` nos três canais inteiros 0..255."""
    n = int(hex_[1:], 16)
    return (n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF


def _hex(r: float, g: float, b: float) -> str:
    # Meia-para-cima (int(x + 0.5)), não round() do Python — round() usa
    # arredondamento bancário e divergiria da mistura equivalente em
    # JavaScript em caso de empate.
    return "#%02x%02x%02x" % (int(r + 0.5), int(g + 0.5), int(b + 0.5))


def misturar(hex_: str, alvo: int, fator: float) -> str:
    """Mistura sRGB canal a canal com um alvo (`255` = branco, `0` = preto)."""
    return _hex(*(c + (alvo - c) * fator for c in _canais(hex_)))


def com_hsl(hex_: str, fator_sat: float, luz: float) -> str:
    """Preserva o matiz, multiplica a saturação por `fator_sat` e fixa a
    luminosidade em `luz` (0..1) — usado para derivar o tema escuro."""
    r, g, b = (c / 255 for c in _canais(hex_))
    matiz, _luz_atual, sat = colorsys.rgb_to_hls(r, g, b)
    r2, g2, b2 = colorsys.hls_to_rgb(matiz, luz, sat * fator_sat)
    return _hex(r2 * 255, g2 * 255, b2 * 255)


@lru_cache(maxsize=8)
def familia_marca(cor: str) -> dict[str, str]:
    """Deriva as 14 variáveis da família de marca (7 claras + 7 escuras) a
    partir de uma única cor. A cor é imutável durante a vida do processo
    (vem de `settings.COR_PRIMARIA`, fixado no boot), daí o cache."""
    return {
        # claro — fatores medidos contra o padrão de referência
        "brand": cor,
        "brand-hover": misturar(cor, 255, 0.12),  # tom de hover
        "brand-ink": misturar(cor, 0, 0.18),  # tom pressionado / texto de ênfase
        "brand-tint": misturar(cor, 255, 0.92),  # fundo tênue do item ativo
        # Quarto degrau da rampa (07-13/G-03). A rampa do padrão de
        # referência tem TRÊS degraus, mas o donut do app exemplo precisa
        # de quatro cores de DADO (StatusChoices tem quatro valores) — e a
        # quarta era `brand-tint`, um token de FUNDO, invisível sobre o
        # card (1,11:1 no claro, 1,00:1 no escuro). O degrau novo estende a
        # rampa pelo lado FORTE, não na direção do branco: um quarto tom
        # ainda mais claro daria ~1,4:1 contra um card quase branco, ou
        # seja, trocaria um invisível por outro. Daí ser o mais ESCURO no
        # tema claro e o mais CLARO no escuro — nos dois casos, o de maior
        # contraste contra o card do respectivo tema.
        "seq-750": misturar(cor, 0, 0.35),  # degrau MAIS forte da rampa
        "seq-600": cor,  # primeiro degrau da rampa sequencial
        "seq-450": misturar(cor, 255, 0.34),  # segundo degrau da rampa
        "seq-300": misturar(cor, 255, 0.62),  # terceiro degrau da rampa
        # escuro — mesmo matiz (e, onde indicado, saturação escalada);
        # luminosidade recalculada para contraste sobre superfície escura
        "brand:escuro": com_hsl(cor, 1.00, 0.727),
        "brand-hover:escuro": com_hsl(cor, 1.00, 0.827),
        "brand-ink:escuro": com_hsl(cor, 1.00, 0.627),
        "brand-tint:escuro": com_hsl(cor, 0.50, 0.153),
        # Contrapartida escura do degrau novo (ver o comentário do claro):
        # no tema escuro o mais forte é o mais CLARO, acima do `brand`.
        "seq-750:escuro": com_hsl(cor, 1.00, 0.860),
        "seq-600:escuro": com_hsl(cor, 1.00, 0.727),
        "seq-450:escuro": com_hsl(cor, 0.72, 0.567),
        "seq-300:escuro": com_hsl(cor, 0.55, 0.427),
    }


def css_da_marca(cor: str) -> str:
    """Monta o CSS de override da marca: bloco `:root { ... }` seguido do
    bloco `[data-tema="escuro"] { ... }`, só com as 7 variáveis
    `--cor-brand*`/`--cor-seq-*` de cada tema. Nenhuma tag `<style>` aqui —
    isso é responsabilidade de `core/templates/base.html`."""
    familia = familia_marca(cor)
    claro = "\n".join(
        f"  --cor-{chave}: {familia[chave]};" for chave in _CHAVES_MARCA
    )
    escuro = "\n".join(
        f"  --cor-{chave}: {familia[f'{chave}:escuro']};" for chave in _CHAVES_MARCA
    )
    return f':root {{\n{claro}\n}}\n[data-tema="escuro"] {{\n{escuro}\n}}'
