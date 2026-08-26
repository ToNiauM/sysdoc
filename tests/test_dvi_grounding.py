"""
Testes do grounding check do campo `de` do motor DVI (sysdoc_dvi.grounding).

CA3 (PRD §7): item com trecho `de` fabricado é rejeitado pelo grounding check
e reclassificado como `pendente`, com registro no relatório (`falha_grounding`).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sysdoc_dvi.grounding import (  # noqa: E402
    LIMIAR_GROUNDING_DEFAULT,
    aplicar_grounding,
    normalizar_texto,
    verificar_trecho,
)
from sysdoc_dvi.tipos import ResultadoItem  # noqa: E402


TEXTO_PECA = (
    "1. Objeto\n"
    "O objeto é a contratação de serviços continuados de limpeza predial em "
    "edifício público, incluindo fornecimento de materiais e equipamentos.\n"
    "2. Garantia\n"
    "O contratado apresentará garantia contratual no percentual de cinco por "
    "cento do valor do contrato, na forma da legislação vigente."
)


def _resultado(de, classificação="risco", origem="llm", severidade="alta", risco="bloqueante"):
    return ResultadoItem(
        checklist_id="DVI-AMB-900",
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


class TestNormalizacao:
    def test_remove_acentos_e_caixa(self):
        assert normalizar_texto("AÇÃO Jurídica") == "acao juridica"

    def test_colapsa_espacos_e_quebras(self):
        assert normalizar_texto("linha   um\n\nlinha  dois") == "linha um linha dois"

    def test_remove_hifenizacao_de_quebra_de_linha(self):
        assert normalizar_texto("continu-\nados") == "continuados"


class TestVerificarTrecho:
    def test_trecho_literal_e_ancorado(self):
        trecho = "O objeto é a contratação de serviços continuados de limpeza predial"
        ancorado, score = verificar_trecho(trecho, TEXTO_PECA)
        assert ancorado is True
        assert score >= LIMIAR_GROUNDING_DEFAULT

    def test_trecho_com_variacao_de_caixa_espaco_e_acento_e_ancorado(self):
        trecho_variado = "o   OBJETO e  a\ncontratacao de servicos continuados"
        ancorado, _ = verificar_trecho(trecho_variado, TEXTO_PECA)
        assert ancorado is True

    def test_trecho_fabricado_nao_e_ancorado(self):
        trecho = "cláusula inexistente sobre garantia estendida de dez anos"
        ancorado, score = verificar_trecho(trecho, TEXTO_PECA)
        assert ancorado is False
        assert score < LIMIAR_GROUNDING_DEFAULT

    def test_trecho_curto_demais_nao_ancora(self):
        ancorado, score = verificar_trecho("ab cd", TEXTO_PECA)
        assert ancorado is False
        assert score == 0.0


class TestOmissao:
    def test_marcador_omissao_sempre_ancorado(self):
        ancorado, score = verificar_trecho("[OMISSÃO] seção de garantia contratual", TEXTO_PECA)
        assert (ancorado, score) == (True, 1.0)

    def test_marcador_omissao_nao_consulta_texto(self):
        ancorado, score = verificar_trecho("[OMISSÃO] tema totalmente ausente do texto", "")
        assert (ancorado, score) == (True, 1.0)


class TestLimiar:
    def test_default_e_0_85(self):
        assert LIMIAR_GROUNDING_DEFAULT == 0.85

    def test_limiar_mais_permissivo_aceita_trecho_parcial(self):
        trecho_parcial = (
            "objeto contratação serviços continuados limpeza xyz totalmente diferente aqui"
        )
        _, score = verificar_trecho(trecho_parcial, TEXTO_PECA)
        ancorado_permissivo, _ = verificar_trecho(
            trecho_parcial, TEXTO_PECA, limiar=max(0.01, score - 0.05)
        )
        assert ancorado_permissivo is True

    def test_limiar_mais_rigoroso_rejeita_trecho_antes_aceito(self):
        trecho_quase_perfeito = "O objeto é a contratação de serviços continuados de limpeza predia"
        ancorado_default, score = verificar_trecho(trecho_quase_perfeito, TEXTO_PECA)
        assert ancorado_default is True
        ancorado_rigoroso, _ = verificar_trecho(
            trecho_quase_perfeito, TEXTO_PECA, limiar=min(0.999, score + 0.02)
        )
        assert ancorado_rigoroso is False


class TestCA3:
    def test_trecho_fabricado_reclassifica_para_pendente(self):
        resultado = _resultado(
            de="cláusula inexistente sobre garantia estendida de dez anos",
            classificação="risco",
            origem="llm",
        )
        de_original = resultado.de
        reclassificado = aplicar_grounding(resultado, TEXTO_PECA)

        assert reclassificado.classificação == "pendente"
        assert reclassificado.falha_grounding is True
        assert reclassificado.de == de_original
        assert "pendente" in reclassificado.parecer.lower()
        assert "rejeitado" in reclassificado.parecer.lower()

    def test_trecho_literal_nao_altera_resultado(self):
        resultado = _resultado(
            de="O objeto é a contratação de serviços continuados de limpeza predial",
            classificação="risco",
            origem="llm",
        )
        reclassificado = aplicar_grounding(resultado, TEXTO_PECA)
        assert reclassificado == resultado

    def test_nao_altera_resultado_deterministico(self):
        resultado = _resultado(
            de="qualquer coisa fabricada e sem relação com o texto todo",
            origem="deterministico",
        )
        reclassificado = aplicar_grounding(resultado, TEXTO_PECA)
        assert reclassificado is resultado

    def test_nao_altera_resultado_lookup(self):
        resultado = _resultado(
            de="qualquer coisa fabricada e sem relação com o texto todo",
            origem="lookup",
        )
        reclassificado = aplicar_grounding(resultado, TEXTO_PECA)
        assert reclassificado is resultado


class TestDesempenho:
    def test_peca_grande_processa_em_menos_de_5_segundos(self):
        paragrafo_filler = (
            "Disposição contratual genérica sobre execução do objeto e obrigações "
            "das partes conforme instrumento convocatório e legislação aplicável. "
        )
        texto_grande = paragrafo_filler * 8000
        alvo = (
            "\nA garantia contratual será prestada no percentual de cinco por cento "
            "do valor total do contrato, nos termos do artigo noventa e seis da lei.\n"
        )
        metade = len(texto_grande) // 2
        texto_peca = texto_grande[:metade] + alvo + texto_grande[metade:]
        assert len(texto_peca.encode("utf-8")) >= 500_000

        trecho = "A garantia contratual será prestada no percentual de cinco por cento"
        inicio = time.monotonic()
        ancorado, _ = verificar_trecho(trecho, texto_peca)
        duracao = time.monotonic() - inicio

        assert ancorado is True
        assert duracao < 5.0
