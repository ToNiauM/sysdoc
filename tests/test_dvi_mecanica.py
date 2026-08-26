"""
Testes das verificações mecânicas do motor DVI (sysdoc_dvi.verificacoes.mecanica).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sysdoc_dvi.tipos import ItemChecklist  # noqa: E402
from sysdoc_dvi.verificacoes.mecanica import (  # noqa: E402
    verificar_codigos_catalogo,
    verificar_cronograma,
    verificar_item_mecanico,
    verificar_numeracao,
)


def _item(verificacao, severidade_default="média"):
    return ItemChecklist(
        id="DVI-GER-900",
        aplicabilidade="geral",
        peca="ETP",
        documento_saida="ETP",
        tipo="mecanica",
        pergunta="pergunta de teste",
        base_legal_texto="pendente",
        referencia="Checklist interno DVI",
        severidade_default=severidade_default,
        modelo_alvo="economico",
        ativo=True,
        parametros={"verificacao": verificacao},
    )


class TestNumeracao:
    def test_salto_entre_secoes_gera_achado(self):
        achados = verificar_numeracao("1. Objeto\n2. Escopo\n4. Prazo")
        assert len(achados) == 1
        assert achados[0].tipo == "numeracao"

    def test_hierarquia_correta_nao_gera_achado(self):
        texto = "1. Objeto\n1.1 Sub\n1.2 Sub2\n2. Escopo"
        assert verificar_numeracao(texto) == []

    def test_trecho_e_linha_literal_extraida(self):
        texto = "1. Objeto\n2. Escopo\n4. Prazo de entrega"
        achados = verificar_numeracao(texto)
        assert achados[0].trecho == "4. Prazo de entrega"

    def test_numeracao_repetida_gera_achado(self):
        texto = "1. Objeto\n1. Objeto duplicado\n2. Escopo"
        achados = verificar_numeracao(texto)
        assert len(achados) == 1
        assert "repetida" in achados[0].descricao

    def test_texto_sem_secoes_numeradas_nao_gera_achado(self):
        assert verificar_numeracao("Texto corrido sem nenhuma seção numerada.") == []


class TestCatalogo:
    def test_sem_codigo_gera_achado(self):
        achados = verificar_codigos_catalogo("Texto de item sem qualquer código de catálogo")
        assert len(achados) == 1
        assert achados[0].tipo == "catalogo"

    def test_catmat_presente_nao_gera_achado(self):
        assert verificar_codigos_catalogo("CATMAT 123456 item") == []

    def test_catser_presente_nao_gera_achado(self):
        assert verificar_codigos_catalogo("Serviço CATSER: 7891011") == []

    def test_codigo_do_item_aceita_acentuacao_e_caixa(self):
        assert verificar_codigos_catalogo("Código do item 12345") == []
        assert verificar_codigos_catalogo("codigo do item 987") == []


class TestCronograma:
    def test_mencao_sem_secao_correspondente_gera_achado(self):
        texto = "O cronograma físico-financeiro será apresentado no anexo.\nSem tabela nenhuma."
        achados = verificar_cronograma(texto)
        assert len(achados) == 1
        assert achados[0].tipo == "cronograma"

    def test_mencao_com_secao_numerada_nao_gera_achado(self):
        texto = "3. Cronograma físico-financeiro\nDetalhamento das etapas a seguir."
        assert verificar_cronograma(texto) == []

    def test_mencao_com_tabela_etapa_valor_nao_gera_achado(self):
        texto = "O cronograma de execução consta abaixo.\nEtapa 1 | Valor R$ 100,00"
        assert verificar_cronograma(texto) == []

    def test_sem_mencao_nao_gera_achado(self):
        assert verificar_cronograma("Texto qualquer sem menção ao tema em questão.") == []


class TestItemMecanico:
    def test_com_achado_sai_deterministico_e_risco(self):
        item = _item("numeracao", severidade_default="alta")
        resultado = verificar_item_mecanico(item, "1. Objeto\n2. Escopo\n4. Prazo")
        assert resultado.origem_verificacao == "deterministico"
        assert resultado.classificação == "risco"
        assert resultado.risco_jurídico == "bloqueante"
        assert resultado.de != ""
        assert resultado.checklist_id == item.id

    def test_sem_achado_sai_conforme_informativo(self):
        item = _item("numeracao")
        resultado = verificar_item_mecanico(item, "1. Objeto\n2. Escopo\n3. Prazo")
        assert resultado.classificação == "conforme"
        assert resultado.risco_jurídico == "informativo"
        assert resultado.origem_verificacao == "deterministico"

    def test_severidade_media_gera_risco_relevante_nao_bloqueante(self):
        item = _item("catalogo", severidade_default="média")
        resultado = verificar_item_mecanico(item, "texto sem nenhum código")
        assert resultado.classificação == "risco"
        assert resultado.risco_jurídico == "relevante"

    def test_chave_verificacao_ausente_levanta_erro_explicito(self):
        item = ItemChecklist(
            id="DVI-GER-901",
            aplicabilidade="geral",
            peca="ETP",
            documento_saida="ETP",
            tipo="mecanica",
            pergunta="pergunta",
            base_legal_texto="pendente",
            referencia="ref",
            severidade_default="média",
            modelo_alvo="economico",
            ativo=True,
            parametros={},
        )
        with pytest.raises(ValueError):
            verificar_item_mecanico(item, "1. Objeto")

    def test_chave_verificacao_invalida_levanta_erro_explicito(self):
        item = _item("formatacao")
        with pytest.raises(ValueError):
            verificar_item_mecanico(item, "1. Objeto")
