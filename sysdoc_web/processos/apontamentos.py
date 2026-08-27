"""
Leitura segura do `dados_consolidados.json` para a tela de resultado
(D-06, D-09, D-13 — 07-CONTEXT.md; T-07-07-01 do threat model do plano).

Nenhuma função deste módulo devolve HTML: tudo aqui é dado primitivo (str,
int, dict, list) que o template Django auto-escapa no ponto de renderização.
Os rótulos em português substituem por completo os valores crus do enum do
schema (`ajuste_necessário`, `risco_jurídico`, etc.) — a tela nunca mostra o
nome técnico do campo, só a tradução.
"""

from __future__ import annotations

ROTULO_CLASSIFICACAO = {
    "conforme": "Conforme",
    "ajuste_necessário": "Ajuste necessário",
    "risco": "Risco",
    "pendente": "Pendente de verificação",
}

ROTULO_RISCO = {
    "informativo": "Informativo",
    "relevante": "Relevante",
    "bloqueante": "Bloqueante",
}

# Tokens de APRESENTAÇÃO — só decidem cor. Deliberadamente desacoplados do
# vocabulário do schema: o valor cru (`ajuste_necessário`, `bloqueante`)
# nunca chega ao HTML, nem como texto nem como atributo. Um valor
# desconhecido cai em "neutro" em vez de vazar o original.
ESTADO_CLASSIFICACAO = {
    "conforme": "ok",
    "ajuste_necessário": "atencao",
    "risco": "critico",
    "pendente": "neutro",
}

ESTADO_RISCO = {
    "informativo": "neutro",
    "relevante": "atencao",
    "bloqueante": "critico",
}

_NAO_IDENTIFICADO = "não identificado"


def _texto(fonte: dict, *chaves: str, padrao: str = _NAO_IDENTIFICADO) -> str:
    for chave in chaves:
        valor = fonte.get(chave)
        if valor is None:
            continue
        texto = str(valor).strip()
        if texto:
            return texto
    return padrao


def resumo_para_tela(dados: dict) -> dict:
    """Contagens e identificação do processo, prontas para o cabeçalho da tela.

    Campo ausente no JSON vira a string `"não identificado"` — nunca
    `KeyError` — porque o pregoeiro precisa de uma tela honesta mesmo quando
    a análise deixou um campo institucional em branco.
    """
    projeto = dados.get("projeto")
    projeto = projeto if isinstance(projeto, dict) else {}
    itens = dados.get("itens")
    itens = itens if isinstance(itens, list) else []

    por_classificacao = {rotulo: 0 for rotulo in ROTULO_CLASSIFICACAO.values()}
    bloqueantes = 0
    for item in itens:
        if not isinstance(item, dict):
            continue
        classificacao = item.get("classificação") or item.get("classificacao") or ""
        rotulo = ROTULO_CLASSIFICACAO.get(classificacao, _NAO_IDENTIFICADO)
        por_classificacao[rotulo] = por_classificacao.get(rotulo, 0) + 1
        risco = item.get("risco_jurídico") or item.get("risco_juridico") or ""
        if risco == "bloqueante":
            bloqueantes += 1

    return {
        "objeto": _texto(projeto, "objeto"),
        "processo": _texto(projeto, "processo"),
        "orgao": _texto(projeto, "órgão", "orgao"),
        "data": _texto(dados, "data_análise", "data_analise"),
        "total": len(itens),
        "por_classificacao": por_classificacao,
        "bloqueantes": bloqueantes,
    }


def itens_para_tela(dados: dict) -> list[dict]:
    """Apontamentos prontos para a tela, ordenados por documento e depois id.

    Não inclui o identificador do provedor de IA usado nem qualquer outro
    metadado de execução da análise (D-06) — só o que descreve o achado em
    si.
    """
    itens = dados.get("itens")
    itens = itens if isinstance(itens, list) else []

    resultado = []
    for item in itens:
        if not isinstance(item, dict):
            continue
        classificacao = item.get("classificação") or item.get("classificacao") or ""
        risco = item.get("risco_jurídico") or item.get("risco_juridico") or ""
        resultado.append(
            {
                "id": _texto(item, "id"),
                "documento": _texto(item, "documento"),
                "secao": _texto(item, "seção", "secao"),
                "classificacao_rotulo": ROTULO_CLASSIFICACAO.get(
                    classificacao, _NAO_IDENTIFICADO
                ),
                "risco_rotulo": ROTULO_RISCO.get(risco, _NAO_IDENTIFICADO),
                # Ponte para a COR do estado (`data-estado` no template).
                # Token de apresentação, nunca o valor cru do schema: a
                # página não expõe vocabulário de máquina em lugar nenhum,
                # nem em atributo — garantia travada por
                # `test_resultado_lista_apontamentos_com_rotulos`.
                "classificacao_estado": ESTADO_CLASSIFICACAO.get(classificacao, "neutro"),
                "risco_estado": ESTADO_RISCO.get(risco, "neutro"),
                "severidade": _texto(item, "severidade"),
                "parecer": _texto(item, "parecer", padrao=""),
                "fundamento": _texto(item, "fundamento", padrao=""),
                "de": _texto(item, "de", padrao=""),
                "para": _texto(item, "para", padrao=""),
            }
        )

    resultado.sort(key=lambda item: (item["documento"], item["id"]))
    return resultado
