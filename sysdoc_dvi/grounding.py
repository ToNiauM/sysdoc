"""
Grounding check do campo `de` (RF5) do motor DVI.

Todo item produzido por LLM com veredicto diferente de `pendente` precisa
trazer, no campo `de`, um trecho literal localizável no texto extraído da
peça indicada. Este módulo valida essa ancoragem com correspondência
aproximada (`difflib.SequenceMatcher`, biblioteca padrão — nenhuma
dependência nova) e reclassifica como `pendente` quando o trecho não é
encontrado, preservando o `de` original para o relatório de execução (RF9).

A lógica aqui é deliberadamente mais estrita que `templates/validate_sysdoc.py`
(`is_traceable`) — não a substitui.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import replace

from sysdoc_dvi.tipos import ResultadoItem

LIMIAR_GROUNDING_DEFAULT = 0.85

_MARCADOR_OMISSAO = "[OMISSÃO]"

_STOPWORDS = {
    "a", "o", "e", "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
    "um", "uma", "para", "por", "com", "sem", "que", "se", "ao", "aos", "as", "os",
}

_MAX_POSICOES_CANDIDATAS = 200


def normalizar_texto(texto: str) -> str:
    texto = str(texto or "")
    texto = re.sub(r"-\s*\n\s*", "", texto)
    normalizado = unicodedata.normalize("NFKD", texto)
    sem_acentos = "".join(char for char in normalizado if not unicodedata.combining(char))
    minusculo = sem_acentos.lower()
    return re.sub(r"\s+", " ", minusculo).strip()


def _tokens_significativos(texto_normalizado: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", texto_normalizado)
    return [token for token in tokens if len(token) >= 3 and token not in _STOPWORDS]


def verificar_trecho(
    de: str, texto_peca: str, limiar: float = LIMIAR_GROUNDING_DEFAULT
) -> tuple[bool, float]:
    bruto = str(de or "").strip()
    if bruto.startswith(_MARCADOR_OMISSAO):
        return True, 1.0

    trecho_norm = normalizar_texto(bruto)
    tokens = _tokens_significativos(trecho_norm)
    if len(tokens) < 3:
        return False, 0.0

    texto_norm = normalizar_texto(texto_peca)
    if not texto_norm:
        return False, 0.0

    tamanho = len(trecho_norm)
    primeiro_token = tokens[0]
    posicoes = [match.start() for match in re.finditer(re.escape(primeiro_token), texto_norm)]
    if not posicoes:
        return False, 0.0
    if len(posicoes) > _MAX_POSICOES_CANDIDATAS:
        posicoes = posicoes[:_MAX_POSICOES_CANDIDATAS]

    margem = max(10, tamanho // 3)
    passo = max(1, tamanho // 8)
    melhor_score = 0.0

    for pos in posicoes:
        candidatos = {pos}
        candidatos.update(range(max(0, pos - margem), pos + margem + 1, passo))
        for inicio in candidatos:
            if inicio < 0:
                continue
            janela = texto_norm[inicio : inicio + tamanho]
            if not janela:
                continue
            score = difflib.SequenceMatcher(None, trecho_norm, janela).ratio()
            if score > melhor_score:
                melhor_score = score
        if melhor_score >= 0.999:
            break

    return melhor_score >= limiar, melhor_score


def aplicar_grounding(
    resultado: ResultadoItem, texto_peca: str, limiar: float = LIMIAR_GROUNDING_DEFAULT
) -> ResultadoItem:
    if resultado.origem_verificacao in ("deterministico", "lookup"):
        return resultado

    ancorado, score = verificar_trecho(resultado.de, texto_peca, limiar)
    if ancorado:
        return resultado

    novo_parecer = (
        f"{resultado.parecer} [REJEITADO PELO GROUNDING: trecho citado em `de` não foi "
        f"localizado no texto extraído da peça (score={score:.2f} < limiar={limiar:.2f}); "
        "item reclassificado como pendente]"
    ).strip()

    return replace(
        resultado,
        classificação="pendente",
        risco_jurídico="informativo",
        falha_grounding=True,
        parecer=novo_parecer,
    )
