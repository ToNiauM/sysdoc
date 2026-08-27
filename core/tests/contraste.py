"""Fonte ÚNICA da fórmula de contraste WCAG 2.x neste repositório.

Quem duplicar a fórmula em outra suíte está criando divergência: dois números
que deveriam ser o mesmo passam a poder discordar em silêncio, e a asserção de
acessibilidade que "passa" deixa de significar alguma coisa. Se você precisa
medir contraste, importe daqui.

Por que este módulo vive em `core/tests/` e não em `.template-tests/`:

1. `.template-tests/` está em `_exclude` do `copier.yml` — nada dali chega ao
   sistema gerado. Um helper lá deixaria TODO derivado sem a guarda de
   contraste, que é justamente o que precisa viajar com o template.
2. Os testes Django (`core/tests/`, `apps/*/tests/`) precisam dele para medir
   em runtime a família derivada de `COR_PRIMARIA` — e só eles têm `core.tema`
   importável.
3. As suítes de `.template-tests/` conseguem carregá-lo por caminho
   (`importlib.util.spec_from_file_location`), então uma única implementação
   serve às duas famílias de teste. `.template-tests/test_07_tokens.py` exerce
   essa ponte num teste dedicado, para que um arquivo movido ou renomeado seja
   descoberto pelo gate e não por um plano futuro.

O módulo é DE TESTE e deliberadamente sem dependências: nada de Django, nada de
`core.tema`, nenhum estado global. É essa ausência de dependência que o torna
carregável por caminho de fora de um projeto Django configurado.

Discovery: o Django coleta `test*.py`; `contraste.py` não casa com o padrão e
portanto não é executado como suíte. A prova dele é `test_contraste.py`.
"""

from __future__ import annotations

import re
from pathlib import Path

__all__ = ["luminancia_relativa", "contraste", "tokens_do_input_css"]


INPUT_CSS_PADRAO = Path(__file__).resolve().parent.parent / "static" / "src" / "input.css"

_HEX_RE = re.compile(r"#[0-9a-fA-F]{6}")
_PADRAO_BLOCO = re.compile(r'(:root|\[data-tema="escuro"\])\s*\{([^}]*)\}')
_PADRAO_VAR = re.compile(r"--cor-([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})")


def _canais_hex(hex_: str) -> tuple[int, int, int]:
    """Valida e decompõe `#rrggbb` nos três canais 0-255.

    A validação é `fullmatch`, não `search`: forma curta (`#abc`), lixo
    (`xyzxyz`) e sobra no fim são recusados com `ValueError` citando a entrada.
    Falhar alto é o comportamento certo num helper de teste — uma cor errada
    nascida em silêncio dentro de uma asserção de acessibilidade produz um
    número que parece medido e não é (fecha, do lado do teste, a mesma porta
    que o IN-10 aponta em `core/tema.py`).
    """
    if not isinstance(hex_, str) or not _HEX_RE.fullmatch(hex_):
        raise ValueError(
            f"cor fora do formato #rrggbb (6 dígitos hexadecimais): {hex_!r}"
        )
    limpo = hex_[1:]
    return tuple(int(limpo[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def luminancia_relativa(hex_: str) -> float:
    """Luminância relativa WCAG 2.x de `#rrggbb`, entre 0,0 (preto) e 1,0 (branco).

    Canal normalizado para 0-1, linearizado por `c/12.92` quando `c <= 0.03928`
    e por `((c + 0.055) / 1.055) ** 2.4` acima disso; soma ponderada
    `0.2126*R + 0.7152*G + 0.0722*B`.
    """
    canais = _canais_hex(hex_)
    lineares = []
    for bruto in canais:
        c = bruto / 255
        lineares.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = lineares
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(hex_a: str, hex_b: str) -> float:
    """Razão de contraste WCAG 2.x entre duas cores: `(Lclara + 0.05) / (Lescura + 0.05)`.

    Simétrico por construção — a função ordena as luminâncias, então qual das
    duas cores é texto e qual é fundo não muda o resultado. Escala: 1,0 (cores
    idênticas) a 21,0 (branco sobre preto). Pisos WCAG AA: 4,5:1 para texto
    normal, 3:1 para texto grande e para elementos de interface.
    """
    la = luminancia_relativa(hex_a)
    lb = luminancia_relativa(hex_b)
    mais_clara, mais_escura = (la, lb) if la >= lb else (lb, la)
    return (mais_clara + 0.05) / (mais_escura + 0.05)


def tokens_do_input_css(
    caminho: Path | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Lê `core/static/src/input.css` e devolve `(claro, escuro)`.

    Cada dict mapeia `sufixo-da-variável -> "#rrggbb"` (a chave de
    `--cor-brand-tint` é `brand-tint`). Ler o arquivo — em vez de repetir hex à
    mão no teste — é o que impede a asserção e a fonte de divergirem em
    silêncio.

    `claro` é o bloco `:root` puro. `escuro` é `{**claro, **overrides}`: o
    bloco `[data-tema="escuro"]` só declara os tokens com valor PRÓPRIO no
    escuro e quem não está lá HERDA o claro — a regra está escrita em
    `input.css:93-96` e depende só da ordem de declaração, já que os dois
    seletores têm a mesma especificidade. Sem essa fusão, medir
    `--cor-destructive`, `--cor-secundaria` ou `--cor-baseline` no escuro daria
    `KeyError` em vez do valor herdado, que é o que a página realmente pinta.
    """
    origem = Path(caminho) if caminho is not None else INPUT_CSS_PADRAO
    texto = origem.read_text(encoding="utf-8")

    blocos: dict[str, dict[str, str]] = {}
    for seletor, corpo in _PADRAO_BLOCO.findall(texto):
        blocos[seletor] = dict(_PADRAO_VAR.findall(corpo))

    faltando = {":root", '[data-tema="escuro"]'} - set(blocos)
    if faltando:
        raise ValueError(f"bloco(s) de token ausente(s) em {origem}: {sorted(faltando)}")

    claro = blocos[":root"]
    escuro = {**claro, **blocos['[data-tema="escuro"]']}
    return claro, escuro
