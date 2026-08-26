"""
Verificação determinística do tipo `calculo` (RF4).

O modelo apenas extrai a tabela de preços em schema fechado (fontes,
valores unitários, quantidades, valor declarado). Toda a aritmética —
média, mediana, unitário × quantidade e confronto com o valor
declarado — é recalculada aqui em `decimal.Decimal`, nunca aceita do
modelo (T-05-14). O resultado carrega uma memória de cálculo
determinística e reprodutível para o apontamento (RNF2).

Nenhuma dependência de rede, de LLM ou de arquivo neste módulo.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

DUAS_CASAS = Decimal("0.01")
QUATRO_CASAS = Decimal("0.0001")
CEM = Decimal("100")

METODOS_VALIDOS = ("media", "mediana", "menor")
METODO_FALLBACK_INVALIDO = "media"

MAX_LINHAS_PADRAO = 500
MAX_COTACOES_POR_LINHA_PADRAO = 50


class ErroTabelaPrecos(Exception):
    """
    Erro estrutural na tabela de preços: valor numérico não é
    `decimal.Decimal`, lista de cotações vazia, ou tabela acima do
    limite operacional configurado.
    """


@dataclass(frozen=True)
class Cotacao:
    fonte: str
    valor_unitario: Decimal


@dataclass(frozen=True)
class LinhaTabela:
    descricao: str
    unidade: str
    quantidade: Decimal
    cotacoes: list[Cotacao]
    metodo_declarado: str
    unitario_declarado: Decimal
    total_declarado: Decimal


@dataclass(frozen=True)
class Divergencia:
    linha: str
    campo: str
    declarado: Decimal
    recalculado: Decimal
    diferenca_absoluta: Decimal
    diferenca_relativa: Decimal


@dataclass(frozen=True)
class ResultadoCalculo:
    divergencias: list[Divergencia]
    memoria_calculo: str
    conforme: bool


def _validar_decimal(valor: object, contexto: str) -> Decimal:
    if not isinstance(valor, Decimal):
        tipo = type(valor).__name__
        raise ErroTabelaPrecos(
            f"{contexto}: valor deve ser decimal.Decimal, recebido tipo '{tipo}' — "
            "ponto flutuante nativo não é permitido nesta verificação (RNF2)"
        )
    return valor


def _arredondar(valor: Decimal) -> Decimal:
    return valor.quantize(DUAS_CASAS, rounding=ROUND_HALF_UP)


def media(valores: list[Decimal]) -> Decimal:
    if not valores:
        raise ErroTabelaPrecos("média: lista de valores vazia")
    for indice, valor in enumerate(valores):
        _validar_decimal(valor, f"média: valor na posição {indice}")
    soma = sum(valores, Decimal("0"))
    return _arredondar(soma / Decimal(len(valores)))


def mediana(valores: list[Decimal]) -> Decimal:
    if not valores:
        raise ErroTabelaPrecos("mediana: lista de valores vazia")
    for indice, valor in enumerate(valores):
        _validar_decimal(valor, f"mediana: valor na posição {indice}")
    ordenados = sorted(valores)
    quantidade_valores = len(ordenados)
    meio = quantidade_valores // 2
    if quantidade_valores % 2 == 1:
        return _arredondar(ordenados[meio])
    return _arredondar((ordenados[meio - 1] + ordenados[meio]) / Decimal("2"))


def _menor_cotacao(valores: list[Decimal]) -> Decimal:
    if not valores:
        raise ErroTabelaPrecos("menor cotação: lista de valores vazia")
    for indice, valor in enumerate(valores):
        _validar_decimal(valor, f"menor cotação: valor na posição {indice}")
    return _arredondar(min(valores))


def _recalcular_por_metodo(metodo: str, valores: list[Decimal]) -> Decimal:
    if metodo == "media":
        return media(valores)
    if metodo == "mediana":
        return mediana(valores)
    if metodo == "menor":
        return _menor_cotacao(valores)
    raise ErroTabelaPrecos(f"método de recálculo desconhecido: '{metodo}'")


def _diferenca(declarado: Decimal, recalculado: Decimal) -> tuple[Decimal, Decimal]:
    diferenca_absoluta = _arredondar(abs(declarado - recalculado))
    if recalculado != 0:
        diferenca_relativa = (diferenca_absoluta / abs(recalculado)).quantize(
            QUATRO_CASAS, rounding=ROUND_HALF_UP
        )
    elif declarado == 0:
        diferenca_relativa = Decimal("0.0000")
    else:
        diferenca_relativa = Decimal("1.0000")
    return diferenca_absoluta, diferenca_relativa


def _excede_tolerancia(
    diferenca_absoluta: Decimal,
    diferenca_relativa: Decimal,
    tolerancia_absoluta: Decimal,
    tolerancia_relativa: Decimal,
) -> bool:
    return diferenca_absoluta > tolerancia_absoluta and diferenca_relativa > tolerancia_relativa


def _formatar_cotacoes(cotacoes: list[Cotacao]) -> str:
    return ", ".join(f"{cotacao.fonte}: R$ {cotacao.valor_unitario}" for cotacao in cotacoes)


def _memoria_linha(
    descricao: str,
    campo: str,
    cotacoes: list[Cotacao],
    metodo_declarado: str,
    recalculado: Decimal,
    declarado: Decimal,
    diferenca_absoluta: Decimal,
    diferenca_relativa: Decimal,
) -> str:
    percentual = (diferenca_relativa * CEM).quantize(DUAS_CASAS, rounding=ROUND_HALF_UP)
    return (
        f"Linha {descricao} ({campo}) — cotações: {_formatar_cotacoes(cotacoes)}; "
        f"método declarado: {metodo_declarado}; valor recalculado: R$ {recalculado}; "
        f"valor declarado: R$ {declarado}; diferença: R$ {diferenca_absoluta} ({percentual}%)"
    )


def auditar_tabela_precos(
    linhas: list[LinhaTabela],
    tolerancia_absoluta: Decimal = Decimal("0.01"),
    tolerancia_relativa: Decimal = Decimal("0.005"),
    max_linhas: int = MAX_LINHAS_PADRAO,
    max_cotacoes_por_linha: int = MAX_COTACOES_POR_LINHA_PADRAO,
) -> ResultadoCalculo:
    _validar_decimal(tolerancia_absoluta, "tolerância absoluta")
    _validar_decimal(tolerancia_relativa, "tolerância relativa")

    if len(linhas) > max_linhas:
        raise ErroTabelaPrecos(
            f"tabela de preços com {len(linhas)} linhas excede o limite operacional de "
            f"{max_linhas} (proteção contra tabela sintetizada indefinidamente)"
        )

    divergencias: list[Divergencia] = []
    memorias: list[str] = []

    for linha in linhas:
        if len(linha.cotacoes) > max_cotacoes_por_linha:
            raise ErroTabelaPrecos(
                f"linha '{linha.descricao}': {len(linha.cotacoes)} cotações excede o limite "
                f"operacional de {max_cotacoes_por_linha}"
            )
        if not linha.cotacoes:
            raise ErroTabelaPrecos(f"linha '{linha.descricao}': lista de cotações vazia")

        quantidade = _validar_decimal(linha.quantidade, f"linha '{linha.descricao}': quantidade")
        unitario_declarado = _validar_decimal(
            linha.unitario_declarado, f"linha '{linha.descricao}': unitário declarado"
        )
        total_declarado = _validar_decimal(
            linha.total_declarado, f"linha '{linha.descricao}': total declarado"
        )
        valores_cotados = [
            _validar_decimal(
                cotacao.valor_unitario, f"linha '{linha.descricao}': cotação '{cotacao.fonte}'"
            )
            for cotacao in linha.cotacoes
        ]

        if linha.metodo_declarado not in METODOS_VALIDOS:
            recalculado = _recalcular_por_metodo(METODO_FALLBACK_INVALIDO, valores_cotados)
            diferenca_absoluta, diferenca_relativa = _diferenca(unitario_declarado, recalculado)
            divergencias.append(
                Divergencia(
                    linha=linha.descricao,
                    campo="metodo",
                    declarado=unitario_declarado,
                    recalculado=recalculado,
                    diferenca_absoluta=diferenca_absoluta,
                    diferenca_relativa=diferenca_relativa,
                )
            )
            memorias.append(
                _memoria_linha(
                    linha.descricao,
                    "metodo",
                    linha.cotacoes,
                    linha.metodo_declarado,
                    recalculado,
                    unitario_declarado,
                    diferenca_absoluta,
                    diferenca_relativa,
                )
            )
            continue

        unitario_recalculado = _recalcular_por_metodo(linha.metodo_declarado, valores_cotados)
        diferenca_absoluta_unitario, diferenca_relativa_unitario = _diferenca(
            unitario_declarado, unitario_recalculado
        )
        if _excede_tolerancia(
            diferenca_absoluta_unitario,
            diferenca_relativa_unitario,
            tolerancia_absoluta,
            tolerancia_relativa,
        ):
            divergencias.append(
                Divergencia(
                    linha=linha.descricao,
                    campo="unitario",
                    declarado=unitario_declarado,
                    recalculado=unitario_recalculado,
                    diferenca_absoluta=diferenca_absoluta_unitario,
                    diferenca_relativa=diferenca_relativa_unitario,
                )
            )
            memorias.append(
                _memoria_linha(
                    linha.descricao,
                    "unitario",
                    linha.cotacoes,
                    linha.metodo_declarado,
                    unitario_recalculado,
                    unitario_declarado,
                    diferenca_absoluta_unitario,
                    diferenca_relativa_unitario,
                )
            )

        total_recalculado = _arredondar(quantidade * unitario_recalculado)
        diferenca_absoluta_total, diferenca_relativa_total = _diferenca(
            total_declarado, total_recalculado
        )
        if _excede_tolerancia(
            diferenca_absoluta_total,
            diferenca_relativa_total,
            tolerancia_absoluta,
            tolerancia_relativa,
        ):
            divergencias.append(
                Divergencia(
                    linha=linha.descricao,
                    campo="total",
                    declarado=total_declarado,
                    recalculado=total_recalculado,
                    diferenca_absoluta=diferenca_absoluta_total,
                    diferenca_relativa=diferenca_relativa_total,
                )
            )
            memorias.append(
                _memoria_linha(
                    linha.descricao,
                    "total",
                    linha.cotacoes,
                    linha.metodo_declarado,
                    total_recalculado,
                    total_declarado,
                    diferenca_absoluta_total,
                    diferenca_relativa_total,
                )
            )

    memoria_calculo = "\n".join(memorias)
    return ResultadoCalculo(
        divergencias=divergencias,
        memoria_calculo=memoria_calculo,
        conforme=not divergencias,
    )
