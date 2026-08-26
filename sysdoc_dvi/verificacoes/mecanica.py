"""
Verificações mecânicas puras (RF4, bloco `mecanica`) do motor DVI.

Nenhuma chamada a LLM, rede ou dependência de terceiros aqui — apenas
varredura por regex sobre o texto já extraído da peça (mesmo padrão de
numeração de seção usado por `sysdoc.detect_sections`). Formatação visual
(margens, fonte, espaçamento) está fora de escopo do texto extraído.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from sysdoc_dvi.tipos import ItemChecklist, ResultadoItem

_SECTION_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)*)\.?\s+(.{1,160})$")

_CATALOGO_PATTERN = re.compile(r"\bCAT(?:MAT|SER)\b[\s.:\-]{0,3}\d{4,8}", re.IGNORECASE)
_CODIGO_ITEM_PATTERN = re.compile(
    r"\bc[oó]digo\s+d[oa]\s+item\b[\s.:\-]{0,3}\d{3,8}", re.IGNORECASE
)

_MENCAO_CRONOGRAMA_PATTERNS = (
    re.compile(r"cronograma\s+f[ií]sico[\s\-]*financeiro", re.IGNORECASE),
    re.compile(r"cronograma\s+de\s+execu[cç][aã]o", re.IGNORECASE),
)


@dataclass(frozen=True)
class AchadoMecanico:
    tipo: str
    descricao: str
    trecho: str


def _sem_acentos(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(char for char in normalizado if not unicodedata.combining(char))


def verificar_numeracao(texto: str) -> list[AchadoMecanico]:
    achados: list[AchadoMecanico] = []
    ultimo_por_prefixo: dict[tuple[int, ...], int] = {}

    for linha in str(texto or "").splitlines():
        match = _SECTION_PATTERN.match(linha)
        if not match:
            continue
        try:
            componentes = tuple(int(parte) for parte in match.group(1).split("."))
        except ValueError:
            continue

        prefixo, numero = componentes[:-1], componentes[-1]
        anterior = ultimo_por_prefixo.get(prefixo)

        if anterior is not None:
            esperado = anterior + 1
            if numero == anterior:
                achados.append(
                    AchadoMecanico(
                        tipo="numeracao",
                        descricao=(
                            f"Numeração repetida: '{match.group(1)}' aparece mais de uma vez "
                            "no mesmo nível"
                        ),
                        trecho=linha.strip(),
                    )
                )
            elif numero < anterior:
                achados.append(
                    AchadoMecanico(
                        tipo="numeracao",
                        descricao=(
                            f"Numeração fora de ordem: '{match.group(1)}' aparece após item de "
                            "número maior no mesmo nível"
                        ),
                        trecho=linha.strip(),
                    )
                )
            elif numero > esperado:
                achados.append(
                    AchadoMecanico(
                        tipo="numeracao",
                        descricao=(
                            f"Salto de numeração: seção {anterior} seguida de {numero} "
                            f"(esperado {esperado}) no mesmo nível"
                        ),
                        trecho=linha.strip(),
                    )
                )

        ultimo_por_prefixo[prefixo] = numero

    return achados


def verificar_codigos_catalogo(texto: str) -> list[AchadoMecanico]:
    texto = str(texto or "")
    if _CATALOGO_PATTERN.search(texto) or _CODIGO_ITEM_PATTERN.search(texto):
        return []
    return [
        AchadoMecanico(
            tipo="catalogo",
            descricao=(
                "Nenhum código de catálogo (CATMAT/CATSER) foi encontrado no texto extraído"
            ),
            trecho="",
        )
    ]


def _tem_mencao_cronograma(texto: str) -> bool:
    return any(padrao.search(texto) for padrao in _MENCAO_CRONOGRAMA_PATTERNS)


def _tem_secao_ou_tabela_cronograma(texto: str) -> bool:
    for linha in texto.splitlines():
        match = _SECTION_PATTERN.match(linha)
        if match and "cronograma" in _sem_acentos(match.group(2)).lower():
            return True

    for linha in texto.splitlines():
        linha_norm = _sem_acentos(linha).lower()
        if "etapa" in linha_norm and (
            "valor" in linha_norm or "parcela" in linha_norm or "%" in linha
        ):
            return True

    return False


def verificar_cronograma(texto: str) -> list[AchadoMecanico]:
    texto = str(texto or "")
    if not _tem_mencao_cronograma(texto):
        return []
    if _tem_secao_ou_tabela_cronograma(texto):
        return []

    trecho = ""
    for linha in texto.splitlines():
        if _tem_mencao_cronograma(linha):
            trecho = linha.strip()
            break

    return [
        AchadoMecanico(
            tipo="cronograma",
            descricao=(
                "Cronograma físico-financeiro é mencionado no texto, mas não há seção ou "
                "tabela correspondente"
            ),
            trecho=trecho,
        )
    ]


_DISPATCH = {
    "numeracao": verificar_numeracao,
    "catalogo": verificar_codigos_catalogo,
    "cronograma": verificar_cronograma,
}


def verificar_item_mecanico(item: ItemChecklist, texto_peca: str) -> ResultadoItem:
    verificacao = item.parametros.get("verificacao")
    if verificacao not in _DISPATCH:
        raise ValueError(
            f"item '{item.id}': parametros['verificacao'] ausente ou inválido "
            f"(esperado um de {sorted(_DISPATCH)}, recebido {verificacao!r})"
        )

    achados = _DISPATCH[verificacao](texto_peca)

    if achados:
        classificação = "risco"
        severidade = item.severidade_default
        risco_jurídico = "bloqueante" if severidade in ("crítica", "alta") else "relevante"
        de = "\n".join(achado.trecho for achado in achados if achado.trecho)
        parecer = "; ".join(achado.descricao for achado in achados)
    else:
        classificação = "conforme"
        severidade = "informativa"
        risco_jurídico = "informativo"
        de = ""
        parecer = (
            f"Verificação mecânica '{verificacao}' não encontrou inconsistências no texto "
            "analisado."
        )

    return ResultadoItem(
        checklist_id=item.id,
        origem_verificacao="deterministico",
        documento=item.documento_saida,
        seção="",
        de=de,
        para="",
        parecer=parecer,
        fundamento=item.referencia,
        classificação=classificação,
        severidade=severidade,
        risco_jurídico=risco_jurídico,
    )
