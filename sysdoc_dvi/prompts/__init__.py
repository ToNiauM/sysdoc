"""
Carregador de templates curtos de prompt do motor DVI (RNF1).

Nenhuma regra de negócio vive aqui — apenas o carregamento Jinja restrito à
própria pasta `sysdoc_dvi/prompts/`. Os templates `.jinja` em si são criados
pelos planos que despacham verificações `presenca`/`julgamento`/`calculo`.
"""

from __future__ import annotations

from pathlib import Path

import jinja2

PROMPTS_DIR = Path(__file__).resolve().parent

_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(PROMPTS_DIR)),
    autoescape=False,
    undefined=jinja2.StrictUndefined,
)


def montar_prompt(nome: str, **contexto: object) -> str:
    template = _ENVIRONMENT.get_template(f"{nome}.jinja")
    return template.render(**contexto)
