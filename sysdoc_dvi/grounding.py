"""
Grounding check do campo `de` (RF5) do motor DVI.

Todo item produzido por LLM com veredicto diferente de `pendente` precisa
trazer, no campo `de`, um trecho literal localizável no texto extraído da
peça indicada. Este módulo valida essa ancoragem com correspondência
aproximada (`difflib.SequenceMatcher`, biblioteca padrão — nenhuma
dependência nova) e reclassifica como `pendente` quando o trecho não é
encontrado. O `de` rejeitado NUNCA segue para o JSON final (o validador
imutável o acusaria como não rastreável e derrubaria a análise inteira,
violando RF9): o campo `de` é reescrito com o marcador `[OMISSÃO]`
reconhecido por `verificar_trecho` e por `validate_sysdoc.is_traceable`, e o
trecho original fica preservado em `de_rejeitado`, consumido apenas pelo
relatório de execução (RF9).

A lógica aqui é deliberadamente mais estrita que `templates/validate_sysdoc.py`
(`is_traceable`) — não a substitui.

Antes de degradar um item que falhou na checagem acima, `aplicar_grounding`
dá uma segunda chance determinística via `reancorar_trecho` (P3): se o
trecho citado divergir do texto-fonte só por espaçamento, hifenização de
fim de linha ou pontuação tipográfica (aspas/travessão), `de` é reescrito
com o trecho LITERAL correspondente do texto-fonte (nunca sintetizado) e o
item é marcado com `reancorado=True`, preservando classificação e risco.
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

_MAPA_PONTUACAO_TIPOGRAFICA = str.maketrans(
    {
        "“": '"', "”": '"', "„": '"', "«": '"', "»": '"', "‟": '"',
        "‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'",
        "–": "-", "—": "-", "−": "-", "‒": "-",
    }
)


def _normalizar_pontuacao(texto: str) -> str:
    return texto.translate(_MAPA_PONTUACAO_TIPOGRAFICA)


def normalizar_texto(texto: str) -> str:
    texto = _normalizar_pontuacao(str(texto or ""))
    texto = re.sub(r"-\s*\n\s*", "", texto)
    normalizado = unicodedata.normalize("NFKD", texto)
    sem_acentos = "".join(char for char in normalizado if not unicodedata.combining(char))
    minusculo = sem_acentos.lower()
    return re.sub(r"\s+", " ", minusculo).strip()


def _normalizar_com_mapa(texto: str) -> tuple[str, list[int]]:
    bruto = _normalizar_pontuacao(str(texto or ""))
    saida: list[str] = []
    mapa: list[int] = []
    indice = 0
    tamanho = len(bruto)

    while indice < tamanho:
        caractere = bruto[indice]

        if caractere == "-":
            resto = bruto[indice + 1:]
            casamento = re.match(r"\s*\n\s*", resto)
            if casamento:
                indice += 1 + casamento.end()
                continue

        if caractere.isspace():
            fim_run = indice
            while fim_run < tamanho and bruto[fim_run].isspace():
                fim_run += 1
            if saida and saida[-1] != " ":
                saida.append(" ")
                mapa.append(indice)
            indice = fim_run
            continue

        decomposto = unicodedata.normalize("NFKD", caractere)
        base = "".join(char for char in decomposto if not unicodedata.combining(char)).lower()
        for char_base in base:
            saida.append(char_base)
            mapa.append(indice)
        indice += 1

    while saida and saida[0] == " ":
        saida.pop(0)
        mapa.pop(0)
    while saida and saida[-1] == " ":
        saida.pop()
        mapa.pop()

    return "".join(saida), mapa


def _tokens_significativos(texto_normalizado: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", texto_normalizado)
    return [token for token in tokens if len(token) >= 3 and token not in _STOPWORDS]


def _melhor_janela(trecho_norm: str, texto_norm: str) -> tuple[float, int, int]:
    tokens = _tokens_significativos(trecho_norm)
    if len(tokens) < 3 or not texto_norm:
        return 0.0, 0, 0

    tamanho = len(trecho_norm)
    primeiro_token = tokens[0]
    posicoes = [match.start() for match in re.finditer(re.escape(primeiro_token), texto_norm)]
    if not posicoes:
        return 0.0, 0, 0
    if len(posicoes) > _MAX_POSICOES_CANDIDATAS:
        posicoes = posicoes[:_MAX_POSICOES_CANDIDATAS]

    margem = max(10, tamanho // 3)
    passo = max(1, tamanho // 8)
    melhor_score = 0.0
    melhor_inicio = 0
    melhor_fim = 0

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
                melhor_inicio = inicio
                melhor_fim = inicio + len(janela)
        if melhor_score >= 0.999:
            break

    return melhor_score, melhor_inicio, melhor_fim


def verificar_trecho(
    de: str, texto_peca: str, limiar: float = LIMIAR_GROUNDING_DEFAULT
) -> tuple[bool, float]:
    bruto = str(de or "").strip()
    if bruto.startswith(_MARCADOR_OMISSAO):
        return True, 1.0

    trecho_norm = normalizar_texto(bruto)
    texto_norm = normalizar_texto(texto_peca)
    score, _, _ = _melhor_janela(trecho_norm, texto_norm)
    return score >= limiar, score


def reancorar_trecho(
    de: str, texto_peca: str, limiar: float = LIMIAR_GROUNDING_DEFAULT
) -> str | None:
    bruto = str(de or "").strip()
    if not bruto or bruto.startswith(_MARCADOR_OMISSAO):
        return None

    trecho_norm = normalizar_texto(bruto)
    texto_norm, mapa = _normalizar_com_mapa(texto_peca)
    if not texto_norm or not mapa:
        return None

    score, inicio, fim = _melhor_janela(trecho_norm, texto_norm)
    if score < limiar or fim <= inicio:
        return None

    inicio_original = mapa[inicio]
    fim_original = mapa[fim - 1] + 1
    literal = str(texto_peca or "")[inicio_original:fim_original]

    ancorado, _ = verificar_trecho(literal, texto_peca, limiar)
    if not ancorado:
        return None
    return literal


def aplicar_grounding(
    resultado: ResultadoItem, texto_peca: str, limiar: float = LIMIAR_GROUNDING_DEFAULT
) -> ResultadoItem:
    if resultado.origem_verificacao in ("deterministico", "lookup"):
        return resultado

    ancorado, score = verificar_trecho(resultado.de, texto_peca, limiar)
    if ancorado:
        return resultado

    literal = reancorar_trecho(resultado.de, texto_peca, limiar)
    if literal is not None:
        return replace(
            resultado,
            de=literal,
            reancorado=True,
            falha_grounding=False,
            de_rejeitado=None,
        )

    novo_parecer = (
        f"{resultado.parecer} [REJEITADO PELO GROUNDING: trecho citado em `de` não foi "
        f"localizado no texto extraído da peça (score={score:.2f} < limiar={limiar:.2f}); "
        "item reclassificado como pendente]"
    ).strip()

    return replace(
        resultado,
        de=(
            f"{_MARCADOR_OMISSAO} trecho citado pelo modelo não localizado no texto "
            "extraído da peça"
        ),
        de_rejeitado=resultado.de,
        classificação="pendente",
        risco_jurídico="informativo",
        falha_grounding=True,
        parecer=novo_parecer,
    )
