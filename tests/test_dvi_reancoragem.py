"""
Testes da re-ancoragem determinística do campo `de` (P3) — sysdoc_dvi.grounding.

Cobre: normalização de pontuação tipográfica, `reancorar_trecho` recuperando
o trecho literal do texto-fonte quando a citação do modelo diverge só por
espaçamento, hifenização de fim de linha ou aspas/travessão tipográficos,
citação fabricada continuando a degradar como hoje, e a contagem de
re-ancoragens no relatório de execução.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "templates"))

from sysdoc_dvi.grounding import (  # noqa: E402
    LIMIAR_GROUNDING_DEFAULT,
    aplicar_grounding,
    normalizar_texto,
    reancorar_trecho,
    verificar_trecho,
)
from sysdoc_dvi.relatorio import montar_relatorio  # noqa: E402
from sysdoc_dvi.tipos import ResultadoItem  # noqa: E402

import validate_sysdoc  # noqa: E402


TEXTO_PECA = (
    "1. Objeto\n"
    "O objeto é a contratação de serviços continu-\nados de limpeza predial em "
    "edifício público, incluindo fornecimento de materiais e equipamentos.\n"
    "2. Garantia\n"
    "O contratado apresentará “garantia contratual” no percentual de cinco por "
    "cento do valor do contrato — na forma da legislação vigente."
)


def _resultado(de, classificação="risco", origem="llm", severidade="alta", risco="bloqueante"):
    return ResultadoItem(
        checklist_id="DVI-AMB-901",
        origem_verificacao=origem,
        documento="ETP",
        seção="2",
        de=de,
        para="texto de substituição",
        parecer="parecer original do item",
        fundamento="Lei 14.133/2021",
        classificação=classificação,
        severidade=severidade,
        risco_jurídico=risco,
    )


class TestNormalizacaoPontuacao:
    def test_aspas_tipograficas_normalizam_para_aspas_retas(self):
        assert normalizar_texto("“garantia contratual”") == normalizar_texto('"garantia contratual"')

    def test_travessao_normaliza_para_hifen(self):
        assert normalizar_texto("na forma — da lei") == normalizar_texto("na forma - da lei")


class TestReancorarTrecho:
    def test_citacao_com_espacamento_diferente_recupera_trecho_literal(self):
        de_modelo = "O objeto  e  a contratacao de servicos continuados de limpeza predial"
        literal = reancorar_trecho(de_modelo, TEXTO_PECA)
        assert literal is not None
        assert literal in TEXTO_PECA
        ancorado, score = verificar_trecho(literal, TEXTO_PECA)
        assert (ancorado, score) == (True, 1.0)
        assert validate_sysdoc.is_traceable(literal, TEXTO_PECA)

    def test_citacao_com_aspas_tipograficas_diferentes_recupera_trecho_literal(self):
        de_modelo = 'apresentará "garantia contratual" no percentual de cinco por cento'
        literal = reancorar_trecho(de_modelo, TEXTO_PECA)
        assert literal is not None
        assert literal in TEXTO_PECA

    def test_citacao_sem_hifenizacao_de_fim_de_linha_recupera_trecho_com_hifen_original(self):
        de_modelo = "contratação de serviços continuados de limpeza predial"
        literal = reancorar_trecho(de_modelo, TEXTO_PECA)
        assert literal is not None
        assert literal in TEXTO_PECA
        assert "continu-\nados" in literal or "continu-\nados" in TEXTO_PECA

    def test_citacao_fabricada_nao_e_reancorada(self):
        de_modelo = "cláusula inexistente sobre garantia estendida de dez anos"
        assert reancorar_trecho(de_modelo, TEXTO_PECA) is None

    def test_marcador_omissao_nao_e_reancorado(self):
        assert reancorar_trecho("[OMISSÃO] trecho ausente", TEXTO_PECA) is None

    def test_de_vazio_nao_e_reancorado(self):
        assert reancorar_trecho("", TEXTO_PECA) is None
        assert reancorar_trecho(None, TEXTO_PECA) is None


class TestAplicarGroundingReancoragem:
    def test_reancoragem_bem_sucedida_preserva_classificacao_e_marca_reancorado(self, monkeypatch):
        resultado = _resultado(
            de="cláusula inexistente sobre garantia estendida de dez anos",
            classificação="risco",
            severidade="alta",
            risco="bloqueante",
        )
        monkeypatch.setattr(
            "sysdoc_dvi.grounding.reancorar_trecho",
            lambda de, texto_peca, limiar=LIMIAR_GROUNDING_DEFAULT: (
                "O objeto é a contratação de serviços continu-\nados de limpeza predial"
            ),
        )

        reclassificado = aplicar_grounding(resultado, TEXTO_PECA)

        assert reclassificado.reancorado is True
        assert reclassificado.falha_grounding is False
        assert reclassificado.de_rejeitado is None
        assert reclassificado.classificação == "risco"
        assert reclassificado.risco_jurídico == "bloqueante"
        assert reclassificado.severidade == "alta"
        assert reclassificado.parecer == resultado.parecer
        assert reclassificado.fundamento == resultado.fundamento
        assert reclassificado.de == (
            "O objeto é a contratação de serviços continu-\nados de limpeza predial"
        )

    def test_citacao_fabricada_continua_degradando_como_hoje(self):
        resultado = _resultado(
            de="cláusula inexistente sobre garantia estendida de dez anos",
            classificação="risco",
        )
        de_original = resultado.de
        reclassificado = aplicar_grounding(resultado, TEXTO_PECA)

        assert reclassificado.classificação == "pendente"
        assert reclassificado.falha_grounding is True
        assert reclassificado.reancorado is False
        assert reclassificado.de.startswith("[OMISSÃO]")
        assert reclassificado.de_rejeitado == de_original

    def test_nao_altera_resultado_deterministico(self):
        resultado = _resultado(
            de="qualquer coisa fabricada e sem relação com o texto todo",
            origem="deterministico",
        )
        reclassificado = aplicar_grounding(resultado, TEXTO_PECA)
        assert reclassificado is resultado


class TestRelatorioReancoragens:
    def test_montar_relatorio_conta_reancoragens(self):
        from dataclasses import replace

        itens = [
            replace(_resultado(de="trecho qualquer"), checklist_id="DVI-A", reancorado=True),
            replace(_resultado(de="trecho qualquer"), checklist_id="DVI-B", reancorado=False),
        ]
        relatorio = montar_relatorio(itens, "hash-teste", "1.1", 1.0)
        assert relatorio["reancoragens"] == {"total": 1, "itens": ["DVI-A"]}

    def test_renderizar_relatorio_imprime_contagem_de_reancoragens(self):
        from sysdoc_dvi.relatorio import renderizar_relatorio

        relatorio = montar_relatorio([_resultado(de="trecho qualquer")], "hash-teste", "1.1", 1.0)
        texto = renderizar_relatorio(relatorio)
        assert "Re-ancoragens determinísticas: 0" in texto
