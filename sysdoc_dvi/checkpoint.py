"""
Checkpoint incremental de retomada do motor DVI (D-04, T-05-36, T-05-38).

Grava um `ResultadoItem` por vez em `.sysdoc/cache/dvi_checkpoint.json`,
com escrita atômica (arquivo temporário no mesmo diretório + `os.replace`)
para sobreviver a uma queda de energia no meio de uma execução longa.
`carregar_checkpoint` só reaproveita o arquivo se o `checklist_hash`
gravado bater com o hash atual — checklist alterado invalida a retomada
inteira e o arquivo antigo é descartado — e nunca propaga exceção: um
arquivo corrompido devolve dicionário vazio e emite um aviso.
"""

from __future__ import annotations

import json
import os
import tempfile
import warnings
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sysdoc_dvi.tipos import ResultadoItem, UsoModelo

NOME_ARQUIVO_CHECKPOINT = "dvi_checkpoint.json"


def _caminho_checkpoint(projeto: Path) -> Path:
    return Path(projeto) / ".sysdoc" / "cache" / NOME_ARQUIVO_CHECKPOINT


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reconstruir_resultado(bruto: dict) -> ResultadoItem:
    dados: dict[str, Any] = dict(bruto)
    uso = dados.get("uso")
    if isinstance(uso, dict):
        dados["uso"] = UsoModelo(**uso)
    return ResultadoItem(**dados)


def _ler_dados_existentes(caminho: Path) -> dict | None:
    if not caminho.is_file():
        return None
    try:
        with caminho.open("r", encoding="utf-8") as fh:
            dados = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        warnings.warn(
            f"checkpoint corrompido em {caminho}: {exc}; descartando conteúdo salvo",
            UserWarning,
            stacklevel=2,
        )
        return None
    if not isinstance(dados, dict):
        warnings.warn(
            f"checkpoint em {caminho} não é um objeto JSON válido; descartando conteúdo salvo",
            UserWarning,
            stacklevel=2,
        )
        return None
    return dados


def _escrever_atomico(caminho: Path, dados: dict) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    descritor, nome_temporario = tempfile.mkstemp(
        dir=str(caminho.parent), prefix=".dvi_checkpoint_", suffix=".tmp"
    )
    try:
        with os.fdopen(descritor, "w", encoding="utf-8") as fh:
            json.dump(dados, fh, ensure_ascii=False, indent=2)
        os.replace(nome_temporario, caminho)
    except BaseException:
        Path(nome_temporario).unlink(missing_ok=True)
        raise


def carregar_checkpoint(projeto: Path, checklist_hash: str) -> dict[str, ResultadoItem]:
    caminho = _caminho_checkpoint(projeto)
    dados = _ler_dados_existentes(caminho)
    if dados is None:
        return {}

    if dados.get("checklist_hash") != checklist_hash:
        caminho.unlink(missing_ok=True)
        return {}

    itens_brutos = dados.get("itens")
    if not isinstance(itens_brutos, dict):
        return {}

    resultado: dict[str, ResultadoItem] = {}
    for checklist_id, bruto in itens_brutos.items():
        if not isinstance(bruto, dict):
            continue
        try:
            resultado[checklist_id] = _reconstruir_resultado(bruto)
        except TypeError as exc:
            warnings.warn(
                f"item '{checklist_id}' do checkpoint em {caminho} está incompleto: {exc}; ignorando",
                UserWarning,
                stacklevel=2,
            )
    return resultado


def registrar_item(projeto: Path, checklist_hash: str, resultado: ResultadoItem) -> None:
    caminho = _caminho_checkpoint(projeto)
    dados = _ler_dados_existentes(caminho)

    if not isinstance(dados, dict) or dados.get("checklist_hash") != checklist_hash:
        dados = {
            "checklist_hash": checklist_hash,
            "iniciado_em": _agora_iso(),
            "itens": {},
        }
    if not isinstance(dados.get("itens"), dict):
        dados["itens"] = {}

    dados["itens"][resultado.checklist_id] = asdict(resultado)

    _escrever_atomico(caminho, dados)


def limpar_checkpoint(projeto: Path) -> None:
    _caminho_checkpoint(projeto).unlink(missing_ok=True)
