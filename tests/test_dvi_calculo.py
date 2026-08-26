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


class TestAuditoria:
    def test_conforme_true_quando_nao_ha_divergencia(self):
        resultado = auditar_tabela_precos([_linha()])
        assert resultado.conforme is True
        assert resultado.divergencias == []
        assert resultado.memoria_calculo == ""

    def test_metodo_invalido_gera_divergencia_de_campo_metodo(self):
        linha = _linha(metodo_declarado="moda")
        resultado = auditar_tabela_precos([linha])
        assert resultado.conforme is False
        assert len(resultado.divergencias) == 1
        assert resultado.divergencias[0].campo == "metodo"

    def test_lista_vazia_de_cotacoes_levanta_erro_citando_descricao(self):
        linha = LinhaTabela(
            descricao="Item sem cotação",
            unidade="unid",
            quantidade=Decimal("1"),
            cotacoes=[],
            metodo_declarado="media",
            unitario_declarado=Decimal("10.00"),
            total_declarado=Decimal("10.00"),
        )
        with pytest.raises(ErroTabelaPrecos) as exc_info:
            auditar_tabela_precos([linha])
        assert "Item sem cotação" in str(exc_info.value)

    def test_memoria_calculo_cita_cotacoes_metodo_e_valores(self):
        linha = _linha(
            descricao="Item com divergência",
            quantidade=Decimal("5"),
            valores_cotados=(Decimal("50.00"), Decimal("52.00"), Decimal("48.00")),
            unitario_declarado=Decimal("60.00"),
        )
        resultado = auditar_tabela_precos([linha])
        assert "Item com divergência" in resultado.memoria_calculo
        assert "media" in resultado.memoria_calculo
        assert "50.00" in resultado.memoria_calculo
        assert "60.00" in resultado.memoria_calculo

    def test_entrada_em_float_e_rejeitada_com_erro_tabela_precos(self):
        linha = LinhaTabela(
            descricao="Item com float",
            unidade="unid",
            quantidade=Decimal("1"),
            cotacoes=[Cotacao(fonte="Fornecedor A", valor_unitario=10.0)],
            metodo_declarado="media",
            unitario_declarado=Decimal("10.00"),
            total_declarado=Decimal("10.00"),
        )
        with pytest.raises(ErroTabelaPrecos):
            auditar_tabela_precos([linha])

    def test_limite_de_linhas_excedido_levanta_erro(self):
        linhas = [_linha(descricao=f"Item {indice}") for indice in range(3)]
        with pytest.raises(ErroTabelaPrecos):
            auditar_tabela_precos(linhas, max_linhas=2)

    def test_limite_de_cotacoes_por_linha_excedido_levanta_erro(self):
        linha = _linha(
            valores_cotados=(Decimal("10.00"), Decimal("10.00"), Decimal("10.00"))
        )
        with pytest.raises(ErroTabelaPrecos):
            auditar_tabela_precos([linha], max_cotacoes_por_linha=2)


class TestErrosPlantados:
    @staticmethod
    def _carregar_fixture():
        dados = json.loads(FIXTURE_MCP_SINTETICO.read_text(encoding="utf-8"))
        linhas = []
        esperado = {}
        for bruto in dados["linhas"]:
            cotacoes = [
                Cotacao(fonte=c["fonte"], valor_unitario=Decimal(c["valor_unitario"]))
                for c in bruto["cotacoes"]
            ]
            linha = LinhaTabela(
                descricao=bruto["descricao"],
                unidade=bruto["unidade"],
                quantidade=Decimal(bruto["quantidade"]),
                cotacoes=cotacoes,
                metodo_declarado=bruto["metodo_declarado"],
                unitario_declarado=Decimal(bruto["unitario_declarado"]),
                total_declarado=Decimal(bruto["total_declarado"]),
            )
            linhas.append(linha)
            esperado[bruto["descricao"]] = bruto["divergencia_esperada"]
        return linhas, esperado

    def test_cada_erro_plantado_produz_divergencia_do_campo_esperado(self):
        linhas, esperado = self._carregar_fixture()
        resultado = auditar_tabela_precos(linhas)
        divergencias_por_linha = {d.linha: d for d in resultado.divergencias}

        for descricao, divergencia_esperada in esperado.items():
            if divergencia_esperada is None:
                continue
            assert descricao in divergencias_por_linha, (
                f"linha '{descricao}' deveria ter gerado divergência e não gerou"
            )
            assert divergencias_por_linha[descricao].campo == divergencia_esperada["campo"]

    def test_linhas_de_controle_nao_produzem_apontamento(self):
        linhas, esperado = self._carregar_fixture()
        resultado = auditar_tabela_precos(linhas)
        divergencias_por_linha = {d.linha: d for d in resultado.divergencias}

        for descricao, divergencia_esperada in esperado.items():
            if divergencia_esperada is not None:
                continue
            assert descricao not in divergencias_por_linha, (
                f"linha de controle '{descricao}' não deveria gerar divergência"
            )

    def test_contagem_de_divergencias_igual_a_contagem_de_erros_plantados(self):
        linhas, esperado = self._carregar_fixture()
        resultado = auditar_tabela_precos(linhas)
        erros_plantados = sum(1 for valor in esperado.values() if valor is not None)
        assert len(resultado.divergencias) == erros_plantados

    def test_memoria_calculo_menciona_descricao_declarado_e_recalculado_de_cada_linha_divergente(
        self,
    ):
        linhas, esperado = self._carregar_fixture()
        resultado = auditar_tabela_precos(linhas)

        for divergencia in resultado.divergencias:
            assert divergencia.linha in resultado.memoria_calculo
            assert str(divergencia.declarado) in resultado.memoria_calculo
            assert str(divergencia.recalculado) in resultado.memoria_calculo

    def test_zero_falso_positivo_e_zero_falso_negativo(self):
        linhas, esperado = self._carregar_fixture()
        resultado = auditar_tabela_precos(linhas)
        descricoes_divergentes_detectadas = {d.linha for d in resultado.divergencias}
        descricoes_divergentes_esperadas = {
            descricao for descricao, valor in esperado.items() if valor is not None
        }
        assert descricoes_divergentes_detectadas == descricoes_divergentes_esperadas
