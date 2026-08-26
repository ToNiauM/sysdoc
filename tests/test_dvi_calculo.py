"""
Testes de sysdoc_dvi.verificacoes.calculo (RF4 — verificação `calculo`).

Toda a aritmética da pesquisa de preços é recalculada em Python puro com
`decimal.Decimal`; estes testes provam que a auditoria detecta 100% dos
erros plantados (CA2) e que o arredondamento é `ROUND_HALF_UP` estável
entre execuções (RNF2).
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sysdoc_dvi.verificacoes.calculo import (  # noqa: E402
    Cotacao,
    Divergencia,
    ErroTabelaPrecos,
    LinhaTabela,
    ResultadoCalculo,
    auditar_tabela_precos,
    media,
    mediana,
)

FIXTURE_MCP_SINTETICO = ROOT / "tests" / "fixtures" / "mcp_sintetico.json"


def _linha(
    descricao="Item de teste",
    unidade="unid",
    quantidade=Decimal("10"),
    valores_cotados=(Decimal("100.00"), Decimal("102.00"), Decimal("98.00")),
    metodo_declarado="media",
    unitario_declarado=None,
    total_declarado=None,
):
    cotacoes = [
        Cotacao(fonte=f"fonte-{indice + 1}", valor_unitario=valor)
        for indice, valor in enumerate(valores_cotados)
    ]
    if metodo_declarado == "media":
        recalculado = media(list(valores_cotados))
    elif metodo_declarado == "mediana":
        recalculado = mediana(list(valores_cotados))
    else:
        recalculado = min(valores_cotados)
    if unitario_declarado is None:
        unitario_declarado = recalculado
    if total_declarado is None:
        total_declarado = quantidade * recalculado
    return LinhaTabela(
        descricao=descricao,
        unidade=unidade,
        quantidade=quantidade,
        cotacoes=cotacoes,
        metodo_declarado=metodo_declarado,
        unitario_declarado=unitario_declarado,
        total_declarado=total_declarado,
    )


class TestMedia:
    def test_media_de_tres_valores(self):
        assert media([Decimal("10"), Decimal("20"), Decimal("30")]) == Decimal("20.00")

    def test_media_arredonda_half_up_no_ponto_meio(self):
        assert media([Decimal("0.02"), Decimal("0.03")]) == Decimal("0.03")

    def test_media_estavel_entre_execucoes_com_terco(self):
        valores = [Decimal(1) / Decimal(3) for _ in range(3)]
        assert media(valores) == media(valores) == Decimal("0.33")

    def test_media_rejeita_float(self):
        with pytest.raises(ErroTabelaPrecos):
            media([10.0, 20.0, 30.0])

    def test_media_lista_vazia_levanta_erro(self):
        with pytest.raises(ErroTabelaPrecos):
            media([])


class TestMediana:
    def test_mediana_par_media_dos_centrais(self):
        assert mediana(
            [Decimal("10"), Decimal("20"), Decimal("30"), Decimal("40")]
        ) == Decimal("25.00")

    def test_mediana_impar_valor_central(self):
        assert mediana([Decimal("10"), Decimal("50"), Decimal("30")]) == Decimal("30.00")

    def test_mediana_rejeita_float(self):
        with pytest.raises(ErroTabelaPrecos):
            mediana([10.0, 20.0])

    def test_mediana_lista_vazia_levanta_erro(self):
        with pytest.raises(ErroTabelaPrecos):
            mediana([])


class TestTolerancia:
    def test_diferenca_de_um_centavo_nao_gera_divergencia(self):
        linha = _linha(
            quantidade=Decimal("4"),
            valores_cotados=(Decimal("25.00"), Decimal("25.00"), Decimal("25.00")),
            total_declarado=Decimal("100.01"),
        )
        resultado = auditar_tabela_precos([linha])
        assert resultado.conforme is True
        assert resultado.divergencias == []

    def test_diferenca_acima_da_tolerancia_gera_divergencia_total(self):
        linha = _linha(
            quantidade=Decimal("6"),
            valores_cotados=(Decimal("15.00"), Decimal("15.00"), Decimal("15.00")),
            total_declarado=Decimal("100.00"),
        )
        resultado = auditar_tabela_precos([linha])
        assert resultado.conforme is False
        assert any(divergencia.campo == "total" for divergencia in resultado.divergencias)

    def test_diferenca_acima_da_tolerancia_gera_divergencia_unitario(self):
        linha = _linha(
            quantidade=Decimal("5"),
            valores_cotados=(Decimal("50.00"), Decimal("52.00"), Decimal("48.00")),
            unitario_declarado=Decimal("60.00"),
        )
        resultado = auditar_tabela_precos([linha])
        assert resultado.conforme is False
        assert any(divergencia.campo == "unitario" for divergencia in resultado.divergencias)

    def test_tolerancia_e_configuravel(self):
        linha = _linha(
            quantidade=Decimal("10"),
            valores_cotados=(Decimal("100.00"), Decimal("100.00"), Decimal("100.00")),
            unitario_declarado=Decimal("101.00"),
        )
        resultado_default = auditar_tabela_precos([linha])
        assert resultado_default.conforme is False

        resultado_tolerante = auditar_tabela_precos(
            [linha],
            tolerancia_absoluta=Decimal("5.00"),
            tolerancia_relativa=Decimal("0.5"),
        )
        assert resultado_tolerante.conforme is True
