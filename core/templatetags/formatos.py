"""Filtros de formatação monetária e numérica pt-BR para templates."""

from decimal import Decimal, InvalidOperation
from django import template

register = template.Library()


@register.filter(name="moeda")
def moeda(valor):
    """Formata um Decimal/número como '1.234,56' (pt-BR, sem prefixo R$)."""
    if valor is None or valor == "":
        return ""

    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return ""

    negativo = numero < 0
    numero = abs(numero)

    inteiro, _, decimais = f"{numero:.2f}".partition(".")

    grupos = []
    while len(inteiro) > 3:
        grupos.insert(0, inteiro[-3:])
        inteiro = inteiro[:-3]
    grupos.insert(0, inteiro)
    parte_inteira = ".".join(grupos)

    sinal = "-" if negativo else ""
    return f"{sinal}{parte_inteira},{decimais}"


@register.filter(name="moeda_curta")
def moeda_curta(valor):
    """Abrevia valores monetários para cards (ex.: 12,4 mil / 1,5 mi)."""
    if valor is None or valor == "":
        return ""

    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return ""

    negativo = numero < 0
    numero = abs(numero)

    if numero >= Decimal("1000000"):
        abreviado = numero / Decimal("1000000")
        sufixo = " mi"
    elif numero >= Decimal("1000"):
        abreviado = numero / Decimal("1000")
        sufixo = " mil"
    else:
        return moeda(-numero if negativo else numero)

    sinal = "-" if negativo else ""
    return f"{sinal}{abreviado:.1f}".replace(".", ",") + sufixo
