"""
Configuração de modelos do motor DVI (RF8, D-15, D-16).

`carregar_config_dvi` lê a seção `dvi` de `~/.sysdoc/config.json` para os
alvos `economico`/`forte` e os demais parâmetros do motor. A seção
`api_keys` guarda as credenciais por provedor, com fallback para variáveis
de ambiente. Nenhum modelo é assumido por default: ausência de
configuração levanta `ErroConfiguracaoModelos` com o remédio na própria
mensagem (D-16). A chave de API nunca entra em `ConfigDvi` nem em
qualquer mensagem de erro — só é lida no momento da chamada, por
`chave_do_provedor`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

PROVEDORES_VALIDOS = ("openrouter", "openai", "gemini", "anthropic")

_VAR_AMBIENTE_POR_PROVEDOR = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}

_EXEMPLO_CONFIG = (
    "{\n"
    '  "dvi": {\n'
    '    "economico": "openrouter/deepseek-chat",\n'
    '    "forte": "anthropic/claude-opus-4",\n'
    '    "timeout_s": 120,\n'
    '    "max_retries": 1\n'
    "  },\n"
    '  "api_keys": {"openrouter": "sk-...", "anthropic": "sk-ant-..."}\n'
    "}"
)


class ErroConfiguracaoModelos(Exception):
    """Configuração de modelos ausente, incompleta ou inválida (D-16)."""


@dataclass(frozen=True)
class ConfigDvi:
    economico: str
    forte: str
    limiar_grounding: float
    tolerancia_absoluta: str
    limiar_curadoria_dias: int
    timeout_s: int
    max_retries: int


def _config_path_padrao() -> Path:
    return Path.home() / ".sysdoc" / "config.json"


def _remedio(config_path: Path) -> str:
    return (
        f"Configuração de modelos ausente ou incompleta em {config_path}.\n"
        "Preencha a seção 'dvi' com os alvos 'economico' e 'forte', por exemplo:\n"
        f"{_EXEMPLO_CONFIG}\n"
        "Alternativa: rode 'sysdoc-dvi config --economico <alvo> --forte <alvo>'."
    )


def _ler_json(config_path: Path, exigir_existencia: bool) -> dict:
    if not config_path.is_file():
        if exigir_existencia:
            raise ErroConfiguracaoModelos(_remedio(config_path))
        return {}
    try:
        with config_path.open("r", encoding="utf-8") as fh:
            dados = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ErroConfiguracaoModelos(f"não foi possível ler {config_path}: {exc}") from exc
    if not isinstance(dados, dict):
        raise ErroConfiguracaoModelos(f"{config_path}: conteúdo inválido, esperado objeto JSON")
    return dados


def _validar_alvo(alvo: str, campo: str) -> tuple[str, str]:
    if not isinstance(alvo, str) or "/" not in alvo:
        raise ErroConfiguracaoModelos(
            f"campo '{campo}' com valor inválido: '{alvo}' — formato esperado 'provedor/modelo'"
        )
    provedor, _, modelo = alvo.partition("/")
    if not provedor or not modelo:
        raise ErroConfiguracaoModelos(
            f"campo '{campo}' com valor inválido: '{alvo}' — formato esperado 'provedor/modelo'"
        )
    if provedor not in PROVEDORES_VALIDOS:
        raise ErroConfiguracaoModelos(
            f"campo '{campo}': provedor '{provedor}' não suportado; "
            f"provedores válidos: {', '.join(PROVEDORES_VALIDOS)}"
        )
    return provedor, modelo


def _checar_chave_disponivel(dados: dict, provedor: str, config_path: Path) -> None:
    api_keys = dados.get("api_keys")
    chave = api_keys.get(provedor) if isinstance(api_keys, dict) else None
    var_ambiente = _VAR_AMBIENTE_POR_PROVEDOR[provedor]
    if not chave and not os.environ.get(var_ambiente):
        raise ErroConfiguracaoModelos(
            f"chave de API ausente para o provedor '{provedor}': preencha "
            f"'api_keys.{provedor}' em {config_path} ou defina a variável "
            f"de ambiente '{var_ambiente}'"
        )


def carregar_config_dvi(
    economico: str | None = None,
    forte: str | None = None,
    config_path: Path | None = None,
) -> ConfigDvi:
    path = config_path or _config_path_padrao()
    dados = _ler_json(path, exigir_existencia=True)
    secao_dvi = dados.get("dvi")
    if not isinstance(secao_dvi, dict):
        secao_dvi = {}

    alvo_economico = economico or secao_dvi.get("economico")
    alvo_forte = forte or secao_dvi.get("forte")

    if not alvo_economico:
        raise ErroConfiguracaoModelos(
            f"campo 'economico' ausente na seção 'dvi' de {path}.\n{_remedio(path)}"
        )
    if not alvo_forte:
        raise ErroConfiguracaoModelos(
            f"campo 'forte' ausente na seção 'dvi' de {path}.\n{_remedio(path)}"
        )

    for alvo, campo in ((alvo_economico, "economico"), (alvo_forte, "forte")):
        provedor, _ = _validar_alvo(alvo, campo)
        _checar_chave_disponivel(dados, provedor, path)

    return ConfigDvi(
        economico=alvo_economico,
        forte=alvo_forte,
        limiar_grounding=float(secao_dvi.get("limiar_grounding", 0.85)),
        tolerancia_absoluta=str(secao_dvi.get("tolerancia_absoluta", "0.01")),
        limiar_curadoria_dias=int(secao_dvi.get("limiar_curadoria_dias", 180)),
        timeout_s=int(secao_dvi.get("timeout_s", 120)),
        max_retries=int(secao_dvi.get("max_retries", 1)),
    )


def chave_do_provedor(provedor: str, config_path: Path | None = None) -> str:
    path = config_path or _config_path_padrao()
    dados = _ler_json(path, exigir_existencia=False)
    api_keys = dados.get("api_keys")
    chave = api_keys.get(provedor) if isinstance(api_keys, dict) else None
    if not chave:
        var_ambiente = _VAR_AMBIENTE_POR_PROVEDOR.get(provedor)
        chave = os.environ.get(var_ambiente) if var_ambiente else None
    if not chave:
        raise ErroConfiguracaoModelos(
            f"chave de API ausente para o provedor '{provedor}': preencha "
            f"'api_keys.{provedor}' em {path} ou defina a variável de "
            f"ambiente '{_VAR_AMBIENTE_POR_PROVEDOR.get(provedor, '')}'"
        )
    return chave


def _preco_valido(bruto: object) -> dict[str, float] | None:
    if not isinstance(bruto, dict):
        return None
    try:
        entrada = float(bruto.get("entrada"))
        saida = float(bruto.get("saida"))
    except (TypeError, ValueError):
        return None
    if entrada < 0 or saida < 0:
        return None
    return {"entrada": entrada, "saida": saida}


def carregar_precos_dvi(config_path: Path | None = None) -> dict:
    path = config_path or _config_path_padrao()
    dados = _ler_json(path, exigir_existencia=False)
    secao_dvi = dados.get("dvi")
    if not isinstance(secao_dvi, dict):
        return {}
    precos = secao_dvi.get("precos")
    if not isinstance(precos, dict):
        return {}
    resultado: dict[str, dict[str, float]] = {}
    for alvo, bruto in precos.items():
        preco = _preco_valido(bruto)
        if preco is not None:
            resultado[str(alvo)] = preco
    return resultado
