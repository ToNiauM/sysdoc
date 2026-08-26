"""
Cliente HTTP multi-provedor com saída estruturada e medição de uso.

RF8 nível código, D-15 (roteamento OpenRouter/OpenAI/Gemini/Anthropic via
`requests`), D-17 (saída estruturada com um retry, degradação tratada pelo
chamador) e RNF2/RNF3 (temperatura 0, custo/duração medidos, prompt
caching do prefixo estável quando o provedor suportar).

Acrescentar um provedor é acrescentar uma entrada em `PROVEDORES` e uma
função `_executar_<provedor>` — `chamar_modelo` nunca muda.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Callable

import requests

from sysdoc_dvi.config import carregar_precos_dvi, chave_do_provedor
from sysdoc_dvi.tipos import UsoModelo

PRECOS_PADRAO: dict[str, dict[str, float]] = {}

_INSTRUCAO_JSON = "Responda apenas com um JSON válido, sem texto adicional fora do JSON."

REGISTRO_CHAMADAS: list[dict] = []


class ErroProvedor(Exception):
    """Erro de comunicação ou de resposta de um provedor de LLM."""


@dataclass(frozen=True)
class RespostaModelo:
    conteudo: dict
    bruto: str
    uso: UsoModelo
    tokens_cache_leitura: int = 0
    tokens_cache_escrita: int = 0


def _instrucao_com_schema(schema: dict | None) -> str:
    if schema is None:
        return _INSTRUCAO_JSON
    return f"{_INSTRUCAO_JSON} O JSON deve seguir este schema: {json.dumps(schema, ensure_ascii=False)}"


def _executar_openrouter(
    modelo: str,
    prompt: str,
    schema: dict | None,
    prefixo_cacheavel: str | None,
    chave: str,
    timeout_s: int,
) -> tuple[str, int, int, int, int]:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {chave}", "Content-Type": "application/json"}
    conteudo_prompt = f"{prefixo_cacheavel}\n\n{prompt}" if prefixo_cacheavel else prompt
    payload = {
        "model": modelo,
        "messages": [{"role": "user", "content": conteudo_prompt}],
        "temperature": 0,
    }
    if schema is not None:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "resposta_item", "strict": True, "schema": schema},
        }
    try:
        resposta = requests.post(url, headers=headers, json=payload, timeout=timeout_s)
    except requests.RequestException as exc:
        raise ErroProvedor(f"falha de comunicação com 'openrouter': {exc}") from exc
    if not resposta.ok:
        raise ErroProvedor(
            f"erro HTTP {resposta.status_code} do provedor 'openrouter' para o modelo '{modelo}'"
        )
    dados = resposta.json()
    conteudo_bruto = dados["choices"][0]["message"]["content"]
    uso = dados.get("usage", {}) or {}
    return conteudo_bruto, uso.get("prompt_tokens", 0), uso.get("completion_tokens", 0), 0, 0


def _executar_openai(
    modelo: str,
    prompt: str,
    schema: dict | None,
    prefixo_cacheavel: str | None,
    chave: str,
    timeout_s: int,
) -> tuple[str, int, int, int, int]:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {chave}", "Content-Type": "application/json"}
    conteudo_prompt = f"{prefixo_cacheavel}\n\n{prompt}" if prefixo_cacheavel else prompt
    payload = {
        "model": modelo,
        "messages": [{"role": "user", "content": conteudo_prompt}],
        "temperature": 0,
    }
    if schema is not None:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "resposta_item", "strict": True, "schema": schema},
        }
    try:
        resposta = requests.post(url, headers=headers, json=payload, timeout=timeout_s)
    except requests.RequestException as exc:
        raise ErroProvedor(f"falha de comunicação com 'openai': {exc}") from exc
    if not resposta.ok:
        raise ErroProvedor(
            f"erro HTTP {resposta.status_code} do provedor 'openai' para o modelo '{modelo}'"
        )
    dados = resposta.json()
    conteudo_bruto = dados["choices"][0]["message"]["content"]
    uso = dados.get("usage", {}) or {}
    return conteudo_bruto, uso.get("prompt_tokens", 0), uso.get("completion_tokens", 0), 0, 0


def _executar_gemini(
    modelo: str,
    prompt: str,
    schema: dict | None,
    prefixo_cacheavel: str | None,
    chave: str,
    timeout_s: int,
) -> tuple[str, int, int, int, int]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": chave}
    conteudo_prompt = f"{prefixo_cacheavel}\n\n{prompt}" if prefixo_cacheavel else prompt
    generation_config = {"temperature": 0, "responseMimeType": "application/json"}
    if schema is not None:
        generation_config["responseSchema"] = schema
    payload = {
        "contents": [{"role": "user", "parts": [{"text": conteudo_prompt}]}],
        "generationConfig": generation_config,
    }
    try:
        resposta = requests.post(url, headers=headers, json=payload, timeout=timeout_s)
    except requests.RequestException as exc:
        raise ErroProvedor(f"falha de comunicação com 'gemini': {exc}") from exc
    if not resposta.ok:
        raise ErroProvedor(
            f"erro HTTP {resposta.status_code} do provedor 'gemini' para o modelo '{modelo}'"
        )
    dados = resposta.json()
    candidatos = dados.get("candidates", []) or []
    texto = ""
    if candidatos:
        partes = (candidatos[0].get("content", {}) or {}).get("parts", []) or []
        texto = "".join(p.get("text", "") for p in partes if isinstance(p, dict))
    uso = dados.get("usageMetadata", {}) or {}
    return texto, uso.get("promptTokenCount", 0), uso.get("candidatesTokenCount", 0), 0, 0


def _executar_anthropic(
    modelo: str,
    prompt: str,
    schema: dict | None,
    prefixo_cacheavel: str | None,
    chave: str,
    timeout_s: int,
) -> tuple[str, int, int, int, int]:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": chave,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    system_blocos = []
    if prefixo_cacheavel:
        system_blocos.append(
            {"type": "text", "text": prefixo_cacheavel, "cache_control": {"type": "ephemeral"}}
        )
    system_blocos.append({"type": "text", "text": _instrucao_com_schema(schema)})
    payload = {
        "model": modelo,
        "max_tokens": 4096,
        "temperature": 0,
        "system": system_blocos,
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        resposta = requests.post(url, headers=headers, json=payload, timeout=timeout_s)
    except requests.RequestException as exc:
        raise ErroProvedor(f"falha de comunicação com 'anthropic': {exc}") from exc
    if not resposta.ok:
        raise ErroProvedor(
            f"erro HTTP {resposta.status_code} do provedor 'anthropic' para o modelo '{modelo}'"
        )
    dados = resposta.json()
    blocos = dados.get("content", []) or []
    texto = "".join(b.get("text", "") for b in blocos if isinstance(b, dict))
    uso = dados.get("usage", {}) or {}
    return (
        texto,
        uso.get("input_tokens", 0),
        uso.get("output_tokens", 0),
        uso.get("cache_read_input_tokens", 0),
        uso.get("cache_creation_input_tokens", 0),
    )


@dataclass(frozen=True)
class AdaptadorProvedor:
    suporta_cache: bool
    executar: Callable[[str, str, dict | None, str | None, str, int], tuple[str, int, int, int, int]]


PROVEDORES: dict[str, AdaptadorProvedor] = {
    "openrouter": AdaptadorProvedor(suporta_cache=False, executar=_executar_openrouter),
    "openai": AdaptadorProvedor(suporta_cache=False, executar=_executar_openai),
    "gemini": AdaptadorProvedor(suporta_cache=False, executar=_executar_gemini),
    "anthropic": AdaptadorProvedor(suporta_cache=True, executar=_executar_anthropic),
}


def _preco_estimado(alvo: str, tokens_entrada: int, tokens_saida: int) -> float:
    tabela = dict(PRECOS_PADRAO)
    tabela.update(carregar_precos_dvi())
    precos = tabela.get(alvo)
    if not precos:
        return 0.0
    preco_entrada = precos.get("entrada", 0.0)
    preco_saida = precos.get("saida", 0.0)
    return (tokens_entrada / 1_000_000) * preco_entrada + (tokens_saida / 1_000_000) * preco_saida


def _registro_serializavel(alvo: str, resposta: RespostaModelo) -> dict:
    return {
        "provedor": resposta.uso.provedor,
        "modelo": resposta.uso.modelo,
        "tokens_entrada": resposta.uso.tokens_entrada,
        "tokens_saida": resposta.uso.tokens_saida,
        "tokens_cache_leitura": resposta.tokens_cache_leitura,
        "tokens_cache_escrita": resposta.tokens_cache_escrita,
        "custo_estimado": resposta.uso.custo_estimado,
        "duracao_s": resposta.uso.duracao_s,
    }


def limpar_registro_chamadas() -> None:
    REGISTRO_CHAMADAS.clear()


def chamar_modelo(
    alvo: str,
    prompt: str,
    schema: dict | None = None,
    timeout_s: int = 120,
    prefixo_cacheavel: str | None = None,
    max_retries: int = 1,
) -> RespostaModelo:
    provedor, _, modelo = alvo.partition("/")
    if provedor not in PROVEDORES:
        raise ErroProvedor(
            f"provedor não suportado: '{provedor}'; provedores válidos: {', '.join(sorted(PROVEDORES))}"
        )
    adaptador = PROVEDORES[provedor]
    chave = chave_do_provedor(provedor)

    erro_parsing: str | None = None
    ultima_excecao: ErroProvedor | None = None
    tentativas = max(1, max_retries + 1)

    for _tentativa in range(tentativas):
        prompt_tentativa = prompt
        if erro_parsing:
            prompt_tentativa = (
                f"{prompt}\n\n[A resposta anterior não era um JSON válido: {erro_parsing}. "
                "Responda novamente apenas com o JSON solicitado.]"
            )
        inicio = time.monotonic()
        conteudo_bruto, tokens_entrada, tokens_saida, tokens_cache_leitura, tokens_cache_escrita = (
            adaptador.executar(modelo, prompt_tentativa, schema, prefixo_cacheavel, chave, timeout_s)
        )
        duracao_s = time.monotonic() - inicio
        try:
            conteudo = json.loads(conteudo_bruto)
        except json.JSONDecodeError as exc:
            erro_parsing = str(exc)
            ultima_excecao = ErroProvedor(
                f"resposta inválida do provedor '{provedor}' para o modelo '{modelo}': {erro_parsing}"
            )
            continue

        uso = UsoModelo(
            provedor=provedor,
            modelo=modelo,
            tokens_entrada=tokens_entrada,
            tokens_saida=tokens_saida,
            custo_estimado=_preco_estimado(alvo, tokens_entrada, tokens_saida),
            duracao_s=duracao_s,
        )
        resposta = RespostaModelo(
            conteudo=conteudo,
            bruto=conteudo_bruto,
            uso=uso,
            tokens_cache_leitura=tokens_cache_leitura,
            tokens_cache_escrita=tokens_cache_escrita,
        )
        REGISTRO_CHAMADAS.append(_registro_serializavel(alvo, resposta))
        return resposta

    assert ultima_excecao is not None
    raise ultima_excecao
