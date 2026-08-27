"""
Camada de serviço de disco (D-18 — 07-CONTEXT.md).

Este é o único módulo da web que toca a pasta de um processo. Todo caminho
de arquivo aqui é derivado só de `settings.SYSDOC_PROCESSOS_DIR` e do `slug`
já validado — nenhum outro dado de requisição participa da montagem do
caminho. `sysdoc` é sempre chamado como biblioteca (D-03): nenhuma escrita
de YAML ou de estrutura de pastas é feita à mão neste módulo.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from django.conf import settings
from django.core.exceptions import SuspiciousOperation

import sysdoc

_SUFIXO_MAX_TENTATIVAS = 1000
# Mesmo padrão de django.utils.text.slugify / SlugField: só letras, números,
# hífen e underscore. Checado antes de tocar o disco — não é a única defesa
# (ver o `resolver.parent != raiz` abaixo, redundante de propósito), mas é a
# que barra nomes como "..%2Ffora" que não contêm separador de caminho e por
# isso não seriam pegos só pela checagem de contenção.
_SLUG_VALIDO = re.compile(r"^[-a-zA-Z0-9_]+\Z")


def raiz_processos() -> Path:
    raiz = Path(settings.SYSDOC_PROCESSOS_DIR).resolve()
    raiz.mkdir(parents=True, exist_ok=True)
    return raiz


def caminho_do_processo(slug: str) -> Path:
    if not slug or not _SLUG_VALIDO.match(slug):
        raise SuspiciousOperation(f"Slug de processo inválido: {slug!r}")
    raiz = raiz_processos()
    resultado = (raiz / slug).resolve()
    if resultado.parent != raiz:
        raise SuspiciousOperation(f"Caminho de processo fora da raiz esperada: {slug!r}")
    return resultado


def slug_disponivel(nome: str) -> str:
    from .models import Processo

    base = sysdoc.slug(nome)[:60].strip("-._") or "processo"
    candidato = base
    contador = 2
    while (
        Processo.objects.filter(slug=candidato).exists()
        or (raiz_processos() / candidato).exists()
    ):
        sufixo = f"-{contador}"
        candidato = f"{base[: 60 - len(sufixo)]}{sufixo}"
        contador += 1
        if contador > _SUFIXO_MAX_TENTATIVAS:
            raise RuntimeError("Não foi possível gerar um slug disponível para o processo.")
    return candidato


def criar_pasta_do_processo(slug: str) -> Path:
    paths = sysdoc.ensure_project_structure(caminho_do_processo(slug))
    return paths.root


def definir_tipo_verificacao(slug: str, tipo: str) -> None:
    if tipo not in sysdoc.TIPOS_VERIFICACAO:
        raise ValueError(f"tipo de verificação inválido: {tipo!r}")
    paths = sysdoc.project_paths(caminho_do_processo(slug))
    config = sysdoc.load_config(paths)
    config["tipo"] = tipo
    sysdoc.write_config(paths, config)


def gravar_campos_despacho(slug: str, valores: dict[str, str]) -> None:
    paths = sysdoc.project_paths(caminho_do_processo(slug))
    config = sysdoc.load_config(paths)
    bloco = config.get("despacho")
    bloco = dict(bloco) if isinstance(bloco, dict) else {}
    for campo, valor in valores.items():
        if campo in sysdoc.CAMPOS_DESPACHO:
            bloco[campo] = valor
    config["despacho"] = bloco
    sysdoc.write_config(paths, config)


def caminhos(slug: str) -> sysdoc.ProjectPaths:
    return sysdoc.project_paths(caminho_do_processo(slug))


def dados_consolidados(slug: str) -> dict | None:
    paths = caminhos(slug)
    arquivo = paths.root / "dados_consolidados.json"
    if not arquivo.is_file():
        return None
    try:
        return json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
