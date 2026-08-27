"""
Trava um modo de falha silencioso do Django: a forma curta de comentário
(`{#` … `#}`) é de LINHA ÚNICA. Escrita em várias linhas, ela não é tratada
como comentário — o texto inteiro vai renderizado para a tela, sem erro
nenhum no servidor e sem falhar `manage.py check`.

Aconteceu de verdade: um comentário de quatro linhas em
`core/templates/core/_nav_dominio.html` apareceu para o usuário na barra de
navegação, entre "Início" e "Novo processo". Comentário de mais de uma linha
precisa de `{% comment %}` … `{% endcomment %}`.

Este módulo lê os templates como texto e não importa Django, então roda
mesmo sem o extra `web` instalado.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DIRETORIOS = [
    ROOT / "sysdoc_web" / "templates",
    ROOT / "core" / "templates",
]

COMENTARIO_CURTO = re.compile(r"\{#.*?#\}", re.DOTALL)


def _templates() -> list[Path]:
    arquivos: list[Path] = []
    for diretorio in DIRETORIOS:
        if diretorio.exists():
            arquivos.extend(sorted(diretorio.rglob("*.html")))
    return arquivos


def test_existem_templates_para_verificar():
    """Guarda contra o teste virar vacuamente verde se os caminhos mudarem."""
    assert len(_templates()) >= 5


def test_nenhum_comentario_curto_abrange_varias_linhas():
    infratores = []
    for template in _templates():
        conteudo = template.read_text(encoding="utf-8")
        for achado in COMENTARIO_CURTO.finditer(conteudo):
            if "\n" in achado.group(0):
                linha = conteudo[: achado.start()].count("\n") + 1
                infratores.append(f"{template.relative_to(ROOT)}:{linha}")

    assert not infratores, (
        "Comentário `{# #}` de várias linhas RENDERIZA como texto na página. "
        "Troque por `{% comment %}` … `{% endcomment %}` em: "
        + ", ".join(infratores)
    )
