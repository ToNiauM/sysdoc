"""
Testes da síntese dedicada dos pareceres do motor DVI (sysdoc_dvi.sintese).

RF6: uma chamada final ao modelo forte recebe exclusivamente os itens já
validados e produz `parecer_executivo`/`parecer_documento`, com os mínimos
de palavras do validador (450/120) garantidos por um retry único. A
classificação de documento é sempre determinística, nunca pedida ao
modelo.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sysdoc_dvi.sintese import (  # noqa: E402
    ErroSintese,
    Pareceres,
    classificar_documento,
    sintetizar,
    word_count,
)
from sysdoc_dvi.provedores import RespostaModelo  # noqa: E402
from sysdoc_dvi.tipos import ResultadoItem, UsoModelo  # noqa: E402


def _item(
    checklist_id="DVI-AMB-900",
    documento="ETP",
    seção="2",
    de="texto original literal do trecho analisado",
    para="texto de substituição sugerido",
    parecer="parecer original do item",
    fundamento="Lei 14.133/2021",
    classificação="conforme",
    severidade="informativa",
    risco_jurídico="informativo",
    origem_verificacao="llm",
    falha_grounding=False,
    falha_estruturada=None,
):
    return ResultadoItem(
        checklist_id=checklist_id,
        origem_verificacao=origem_verificacao,
        documento=documento,
        seção=seção,
        de=de,
        para=para,
        parecer=parecer,
        fundamento=fundamento,
        classificação=classificação,
        severidade=severidade,
        risco_jurídico=risco_jurídico,
        falha_grounding=falha_grounding,
        falha_estruturada=falha_estruturada,
    )


def _palavras(n, prefixo="parecer"):
    return " ".join(f"{prefixo}{i}" for i in range(n))


def _projeto():
    return {
        "órgão": "Secretaria de Administração",
        "processo": "SEI 0001.000001/2026-01",
        "objeto": "Contratação de serviços continuados de limpeza predial",
        "valor_estimado": "R$ 1.200.000,00",
    }


def _uso(indice=0):
    return UsoModelo(
        provedor="teste",
        modelo="modelo-forte-teste",
        tokens_entrada=100 + indice,
        tokens_saida=100 + indice,
        custo_estimado=0.01,
        duracao_s=0.1,
    )


class AgenteFalso:
    def __init__(self, respostas):
        self._fila = list(respostas)
        self.chamadas = []

    def chamar(self, alvo, prompt, *, schema=None):
        self.chamadas.append((alvo, prompt, schema))
        if not self._fila:
            raise AssertionError("AgenteFalso sem mais respostas programadas")
        conteudo = self._fila.pop(0)
        return RespostaModelo(
            conteudo=conteudo,
            bruto=json.dumps(conteudo, ensure_ascii=False),
            uso=_uso(len(self.chamadas)),
        )


class TestClassificacao:
    def test_reprovado_quando_ha_item_bloqueante(self):
        itens = [
            _item(documento="ETP", classificação="risco", risco_jurídico="bloqueante", severidade="crítica"),
            _item(documento="ETP", classificação="conforme", risco_jurídico="informativo"),
        ]
        assert classificar_documento(itens, "ETP") == "reprovado"

    def test_pendente_de_complementacao_quando_ha_pendente_sem_bloqueante(self):
        itens = [
            _item(documento="ETP", classificação="pendente", risco_jurídico="informativo"),
            _item(documento="ETP", classificação="conforme", risco_jurídico="informativo"),
        ]
        assert classificar_documento(itens, "ETP") == "pendente_de_complementação"

    def test_aprovado_com_ressalvas_quando_ha_ajuste_necessario(self):
        itens = [
            _item(documento="TR", classificação="ajuste_necessário", risco_jurídico="menor"),
        ]
        assert classificar_documento(itens, "TR") == "aprovado_com_ressalvas"

    def test_aprovado_com_ressalvas_quando_ha_risco_relevante(self):
        itens = [
            _item(documento="TR", classificação="risco", risco_jurídico="relevante", severidade="alta"),
        ]
        assert classificar_documento(itens, "TR") == "aprovado_com_ressalvas"

    def test_aprovado_quando_sem_pendencias(self):
        itens = [
            _item(documento="TR", classificação="conforme", risco_jurídico="informativo"),
        ]
        assert classificar_documento(itens, "TR") == "aprovado"


def _fila_feliz():
    return [
        {"parecer_executivo": _palavras(460)},
        {"parecer_documento": _palavras(130)},
        {"parecer_documento": _palavras(130)},
    ]


class TestTemplate:
    def test_prompt_nao_contem_texto_literal_da_peca(self):
        segredo = "TRECHO-LITERAL-SECRETO-DA-PECA-NAO-PODE-VAZAR"
        itens = [
            _item(documento="ETP", de=segredo, para="outro texto", fundamento="Lei 14.133/2021, art. 18"),
            _item(documento="TR", de="outro trecho", para="outro texto"),
        ]
        agente = AgenteFalso(_fila_feliz())
        sintetizar(itens, _projeto(), agente, "ETP-001/2026", "TR-001/2026")
        for _alvo, prompt, _schema in agente.chamadas:
            assert segredo not in prompt

    def test_todas_as_chamadas_usam_alvo_forte(self):
        itens = [_item(documento="ETP"), _item(documento="TR")]
        agente = AgenteFalso(_fila_feliz())
        sintetizar(itens, _projeto(), agente, "ETP-001/2026", "TR-001/2026")
        assert agente.chamadas
        assert all(alvo == "forte" for alvo, _prompt, _schema in agente.chamadas)


class TestMinimos:
    def test_retry_unico_executivo_atinge_minimo_na_segunda_tentativa(self):
        respostas = [
            {"parecer_executivo": _palavras(100)},
            {"parecer_executivo": _palavras(460)},
            {"parecer_documento": _palavras(130)},
            {"parecer_documento": _palavras(130)},
        ]
        agente = AgenteFalso(respostas)
        pareceres = sintetizar(
            [_item(documento="ETP"), _item(documento="TR")],
            _projeto(),
            agente,
            "ETP-001/2026",
            "TR-001/2026",
        )
        assert word_count(pareceres.parecer_executivo) >= 450
        chamadas_executivo = [c for c in agente.chamadas if "executivo" in c[1].lower() or "parecer_executivo" in c[1]]
        assert len(chamadas_executivo) == 2

    def test_erro_sintese_executivo_ainda_curto_apos_retry(self):
        respostas = [
            {"parecer_executivo": _palavras(100)},
            {"parecer_executivo": _palavras(150)},
        ]
        agente = AgenteFalso(respostas)
        try:
            sintetizar(
                [_item(documento="ETP"), _item(documento="TR")],
                _projeto(),
                agente,
                "ETP-001/2026",
                "TR-001/2026",
            )
            raise AssertionError("deveria ter levantado ErroSintese")
        except ErroSintese as exc:
            assert "150" in str(exc)
        assert len(agente.chamadas) == 2

    def test_retry_unico_documento_atinge_minimo_na_segunda_tentativa(self):
        respostas = [
            {"parecer_executivo": _palavras(460)},
            {"parecer_documento": _palavras(40)},
            {"parecer_documento": _palavras(130)},
            {"parecer_documento": _palavras(130)},
        ]
        agente = AgenteFalso(respostas)
        pareceres = sintetizar(
            [_item(documento="ETP"), _item(documento="TR")],
            _projeto(),
            agente,
            "ETP-001/2026",
            "TR-001/2026",
        )
        assert word_count(pareceres.secao_etp["parecer_documento"]) >= 120
        assert len(agente.chamadas) == 4

    def test_erro_sintese_documento_ainda_curto_apos_retry(self):
        respostas = [
            {"parecer_executivo": _palavras(460)},
            {"parecer_documento": _palavras(40)},
            {"parecer_documento": _palavras(60)},
        ]
        agente = AgenteFalso(respostas)
        try:
            sintetizar(
                [_item(documento="ETP"), _item(documento="TR")],
                _projeto(),
                agente,
                "ETP-001/2026",
                "TR-001/2026",
            )
            raise AssertionError("deveria ter levantado ErroSintese")
        except ErroSintese as exc:
            assert "60" in str(exc)


class TestNotaIntegridade:
    def test_contagem_por_origem_e_pendentes_por_falha(self):
        itens = [
            _item(documento="ETP", origem_verificacao="llm", classificação="conforme"),
            _item(documento="ETP", origem_verificacao="llm", classificação="pendente", falha_grounding=True),
            _item(documento="TR", origem_verificacao="deterministico", classificação="conforme"),
            _item(documento="TR", origem_verificacao="lookup", classificação="conforme"),
        ]
        agente = AgenteFalso(_fila_feliz())
        pareceres = sintetizar(itens, _projeto(), agente, "ETP-001/2026", "TR-001/2026")
        assert "4 item(ns)" in pareceres.nota_integridade
        assert "2 de origem llm" in pareceres.nota_integridade
        assert "1 de origem deterministico" in pareceres.nota_integridade
        assert "1 de origem lookup" in pareceres.nota_integridade
        assert "1 item(ns) ficaram pendentes" in pareceres.nota_integridade


class TestUso:
    def test_uso_acumula_uma_entrada_por_chamada_sem_retry(self):
        itens = [_item(documento="ETP"), _item(documento="TR")]
        agente = AgenteFalso(_fila_feliz())
        pareceres = sintetizar(itens, _projeto(), agente, "ETP-001/2026", "TR-001/2026")
        assert len(pareceres.uso) == 3
        assert all(isinstance(uso, UsoModelo) for uso in pareceres.uso)

    def test_uso_acumula_chamadas_extras_quando_ha_retry(self):
        respostas = [
            {"parecer_executivo": _palavras(100)},
            {"parecer_executivo": _palavras(460)},
            {"parecer_documento": _palavras(130)},
            {"parecer_documento": _palavras(130)},
        ]
        agente = AgenteFalso(respostas)
        pareceres = sintetizar(
            [_item(documento="ETP"), _item(documento="TR")],
            _projeto(),
            agente,
            "ETP-001/2026",
            "TR-001/2026",
        )
        assert len(pareceres.uso) == 4
