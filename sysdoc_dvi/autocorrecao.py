"""
Autocorreção determinística de acentuação (P2 - 260826-o2d).

O passo 8 do pipeline DVI (`sysdoc_dvi.pipeline`) roda o validador imutável
(`templates/validate_sysdoc.py`) contra o JSON consolidado. Quando a única
falha é acentuação ausente em texto gerado deterministicamente pelo próprio
motor (não pelo modelo), este módulo aplica a correção apontada pelo próprio
validador e regrava o JSON, numa única passada, antes de declarar falha.

Nenhuma função aqui chama modelo. `coletar_erros_validacao` roda o validador
em subprocesso via `--json` (canal estruturado já documentado em
`templates/validate_sysdoc.py`); as demais funções são puras.
"""

from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import sysdoc

_ERRO_ACENTUACAO = re.compile(
    r"^(?P<label>[^:]+): termo sem acentuação `(?P<encontrado>[^`]+)`; use `(?P<acentuado>[^`]+)`$"
)

_LABEL_ITEM = re.compile(r"^itens\[(\d+)\]\.(.+)$")
_LABEL_METADADO = re.compile(r"^metadados\[(\d+)\]\.(.+)$")
_LABEL_SECAO = re.compile(r"^(secao_etp|secao_tr)\.(.+)$")
_LABEL_PROJETO = re.compile(r"^projeto\.(.+)$")
_LABEL_RAIZ = re.compile(r"^raiz\.(.+)$")


def coletar_erros_validacao(project_dir: Path, json_path: Path) -> list[str]:
    try:
        resultado = subprocess.run(
            [
                sys.executable,
                str(sysdoc.ROOT / "templates" / "validate_sysdoc.py"),
                str(json_path),
                str(project_dir),
                "--json",
            ],
            capture_output=True,
            text=True,
            cwd=sysdoc.ROOT,
        )
    except OSError:
        return []

    if resultado.returncode == 2:
        return []

    saida = (resultado.stdout or "").strip()
    if not saida:
        return []

    try:
        dados = json.loads(saida)
    except json.JSONDecodeError:
        return []

    erros = dados.get("errors")
    if not isinstance(erros, list):
        return []
    return [str(erro) for erro in erros]


def parsear_erros_acentuacao(erros: list[str]) -> list[tuple[str, str, str]]:
    correcoes: list[tuple[str, str, str]] = []
    for erro in erros:
        match = _ERRO_ACENTUACAO.match(str(erro).strip())
        if not match:
            continue
        correcoes.append((match.group("label"), match.group("encontrado"), match.group("acentuado")))
    return correcoes


def _resolver_alvo(dados: dict, label: str) -> tuple[dict, str] | None:
    match = _LABEL_ITEM.match(label)
    if match:
        indice = int(match.group(1)) - 1
        campo = match.group(2)
        itens = dados.get("itens")
        if not isinstance(itens, list) or not (0 <= indice < len(itens)):
            return None
        item = itens[indice]
        if not isinstance(item, dict):
            return None
        return item, campo

    match = _LABEL_METADADO.match(label)
    if match:
        indice = int(match.group(1)) - 1
        campo = match.group(2)
        metadados = dados.get("metadados")
        if not isinstance(metadados, list) or not (0 <= indice < len(metadados)):
            return None
        meta = metadados[indice]
        if not isinstance(meta, dict):
            return None
        return meta, campo

    match = _LABEL_SECAO.match(label)
    if match:
        secao_key, campo = match.group(1), match.group(2)
        secao = dados.get(secao_key)
        if not isinstance(secao, dict):
            return None
        return secao, campo

    match = _LABEL_PROJETO.match(label)
    if match:
        campo = match.group(1)
        projeto = dados.get("projeto")
        if not isinstance(projeto, dict):
            return None
        return projeto, campo

    match = _LABEL_RAIZ.match(label)
    if match:
        campo = match.group(1)
        return dados, campo

    return None


def _forma_com_caixa(ocorrencia: str, acentuado: str) -> str:
    if any(char.isupper() for char in acentuado):
        return acentuado
    if ocorrencia.isupper():
        return acentuado.upper()
    if ocorrencia[:1].isupper() and ocorrencia[1:].islower():
        return acentuado.capitalize()
    return acentuado


def aplicar_correcoes_acentuacao(
    dados: dict, correcoes: list[tuple[str, str, str]]
) -> tuple[dict, list[str]]:
    resultado = copy.deepcopy(dados)
    descricoes: list[str] = []
    for label, encontrado, acentuado in correcoes:
        alvo = _resolver_alvo(resultado, label)
        if alvo is None:
            continue
        objeto, campo = alvo
        if campo == "de":
            continue
        valor = objeto.get(campo)
        if not isinstance(valor, str):
            continue
        novo_valor = re.sub(
            rf"\b{re.escape(encontrado)}\b",
            lambda correspondencia: _forma_com_caixa(correspondencia.group(0), acentuado),
            valor,
            flags=re.IGNORECASE,
        )
        if novo_valor == valor:
            continue
        objeto[campo] = novo_valor
        descricoes.append(f"{label}: {encontrado} → {acentuado}")
    return resultado, descricoes


def autocorrigir_json(project_dir: Path, json_path: Path) -> list[str]:
    erros = coletar_erros_validacao(project_dir, json_path)
    correcoes = parsear_erros_acentuacao(erros)
    if not correcoes:
        return []

    dados = json.loads(json_path.read_text(encoding="utf-8"))
    dados_corrigidos, descricoes = aplicar_correcoes_acentuacao(dados, correcoes)
    if not descricoes:
        return []

    json_path.write_text(
        json.dumps(dados_corrigidos, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return descricoes
