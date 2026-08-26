"""
Relatório de execução do motor DVI (RF9).

`montar_relatorio` agrega os `ResultadoItem` de uma execução em contagens
por status/documento/origem, falhas de grounding e estruturadas, tokens e
custo por modelo (lidos de `provedores.REGISTRO_CHAMADAS`, que já cobre
inclusive as tentativas de retry — não reinventa a medição de uso feita
pela camada de provedores), duração total e avisos operacionais (norma com
curadoria vencida, alvo sem preço registrado). `renderizar_relatorio`
produz a versão em texto, no mesmo estilo de handoff numerado usado por
`sysdoc.py`, terminando sempre com a instrução do próximo comando
(`sysdoc create [pasta] dvi`). Nenhum dos dois expõe chave de API, prompt ou
resposta bruta do modelo (T-05-37).
"""

from __future__ import annotations

from typing import Any

from sysdoc_dvi import provedores
from sysdoc_dvi.normas import normas_desatualizadas
from sysdoc_dvi.tipos import ResultadoItem


def _valor(fonte: Any, nome: str) -> Any:
    if isinstance(fonte, dict):
        return fonte.get(nome)
    return getattr(fonte, nome, None)


def _contagem(itens: list[ResultadoItem], campo: str) -> dict[str, int]:
    contagem: dict[str, int] = {}
    for item in itens:
        chave = getattr(item, campo)
        contagem[chave] = contagem.get(chave, 0) + 1
    return contagem


def _falhas_grounding(itens: list[ResultadoItem]) -> dict:
    afetados = [item for item in itens if item.falha_grounding]
    return {
        "total": len(afetados),
        "itens": [item.checklist_id for item in afetados],
        "trechos_rejeitados": {
            item.checklist_id: item.de_rejeitado for item in afetados if item.de_rejeitado
        },
    }


def _falhas_estruturadas(itens: list[ResultadoItem]) -> dict:
    afetados = [item.checklist_id for item in itens if item.falha_estruturada]
    return {"total": len(afetados), "itens": afetados}


def _reancoragens(itens: list[ResultadoItem]) -> dict:
    afetados = [item.checklist_id for item in itens if getattr(item, "reancorado", False)]
    return {"total": len(afetados), "itens": afetados}


def _agregar_uso(registro_chamadas: list[dict]) -> tuple[dict, dict, float]:
    tokens_por_modelo: dict[str, dict[str, int]] = {}
    custo_por_modelo: dict[str, float] = {}
    custo_total = 0.0
    for registro in registro_chamadas:
        alvo = f"{registro.get('provedor')}/{registro.get('modelo')}"
        entrada = tokens_por_modelo.setdefault(alvo, {"entrada": 0, "saida": 0})
        entrada["entrada"] += int(registro.get("tokens_entrada", 0) or 0)
        entrada["saida"] += int(registro.get("tokens_saida", 0) or 0)
        custo = float(registro.get("custo_estimado", 0.0) or 0.0)
        custo_por_modelo[alvo] = custo_por_modelo.get(alvo, 0.0) + custo
        custo_total += custo
    return tokens_por_modelo, custo_por_modelo, custo_total


def _pecas_mapeadas_serializavel(pecas_mapeadas: dict | None) -> dict:
    if not pecas_mapeadas:
        return {}
    return {
        peca: {"label": _valor(mapeada, "label"), "origem": _valor(mapeada, "origem")}
        for peca, mapeada in pecas_mapeadas.items()
    }


def _avisos_vigencia(tabela_vigencia: dict[str, dict] | None, limiar_dias: int) -> list[str]:
    if not tabela_vigencia:
        return []
    desatualizadas = normas_desatualizadas(tabela_vigencia, limiar_dias=limiar_dias)
    return [
        f"Norma '{norma}' com curadoria vencida (mais de {limiar_dias} dias); "
        "revise 'conferida_em' na tabela de vigência."
        for norma in desatualizadas
    ]


def _avisos_precos(tokens_por_modelo: dict, custo_por_modelo: dict) -> list[str]:
    avisos = []
    for alvo, tokens in tokens_por_modelo.items():
        total_tokens = tokens.get("entrada", 0) + tokens.get("saida", 0)
        if total_tokens > 0 and custo_por_modelo.get(alvo, 0.0) == 0.0:
            avisos.append(
                f"Alvo '{alvo}' não possui preço registrado; custo estimado ficou "
                "zerado apesar de tokens consumidos. Registre o preço com: "
                f"sysdoc-dvi config --preco {alvo} <entrada_usd_1M> <saida_usd_1M>"
            )
    return avisos


def montar_relatorio(
    itens: list[ResultadoItem],
    checklist_hash: str,
    schema_version: str,
    duracao_total_s: float,
    pecas_mapeadas: dict | None = None,
    tabela_vigencia: dict[str, dict] | None = None,
    limiar_dias_vigencia: int = 180,
    registro_chamadas: list[dict] | None = None,
) -> dict:
    chamadas = registro_chamadas if registro_chamadas is not None else provedores.REGISTRO_CHAMADAS
    tokens_por_modelo, custo_por_modelo, custo_total = _agregar_uso(chamadas)

    avisos = _avisos_vigencia(tabela_vigencia, limiar_dias_vigencia)
    avisos += _avisos_precos(tokens_por_modelo, custo_por_modelo)

    return {
        "itens_por_status": _contagem(itens, "classificação"),
        "itens_por_tipo": _contagem(itens, "documento"),
        "itens_por_origem": _contagem(itens, "origem_verificacao"),
        "falhas_grounding": _falhas_grounding(itens),
        "falhas_estruturadas": _falhas_estruturadas(itens),
        "reancoragens": _reancoragens(itens),
        "tokens_por_modelo": tokens_por_modelo,
        "custo_por_modelo": custo_por_modelo,
        "custo_total": custo_total,
        "duracao_total_s": duracao_total_s,
        "checklist_hash": checklist_hash,
        "schema_version": schema_version,
        "pecas_mapeadas": _pecas_mapeadas_serializavel(pecas_mapeadas),
        "avisos": avisos,
    }


def _linhas_contagem(titulo: str, contagem: dict[str, int]) -> list[str]:
    linhas = [f"  {titulo}:"]
    if not contagem:
        linhas.append("    (nenhum item)")
        return linhas
    for chave, quantidade in sorted(contagem.items()):
        linhas.append(f"    - {chave}: {quantidade}")
    return linhas


def renderizar_relatorio(relatorio: dict, projeto: str = "") -> str:
    project_arg = projeto or "<pasta>"
    linhas = ["Relatório de execução do motor DVI", ""]

    linhas.append("1) Itens por status:")
    linhas.extend(_linhas_contagem("status", relatorio.get("itens_por_status", {}))[1:])
    linhas.append("2) Itens por documento:")
    linhas.extend(_linhas_contagem("documento", relatorio.get("itens_por_tipo", {}))[1:])
    linhas.append("3) Itens por origem de verificação:")
    linhas.extend(_linhas_contagem("origem", relatorio.get("itens_por_origem", {}))[1:])

    falhas_grounding = relatorio.get("falhas_grounding", {})
    falhas_estruturadas = relatorio.get("falhas_estruturadas", {})
    linhas.append(f"4) Falhas de grounding: {falhas_grounding.get('total', 0)}")
    linhas.append(f"5) Falhas estruturadas: {falhas_estruturadas.get('total', 0)}")

    reancoragens = relatorio.get("reancoragens") or {}
    linhas.append(f"6) Re-ancoragens determinísticas: {reancoragens.get('total', 0)}")

    pecas_mapeadas = relatorio.get("pecas_mapeadas") or {}
    linhas.append("7) Peças mapeadas:")
    if pecas_mapeadas:
        for peca in sorted(pecas_mapeadas):
            info = pecas_mapeadas[peca]
            linhas.append(f"    - {peca}: {info.get('label')} ({info.get('origem')})")
    else:
        linhas.append("    (nenhuma)")

    avisos = relatorio.get("avisos") or []
    if avisos:
        linhas.append("")
        linhas.append("Avisos:")
        for aviso in avisos:
            linhas.append(f"  - {aviso}")

    linhas.append("")
    linhas.append(f"Custo total estimado: {relatorio.get('custo_total', 0.0):.4f}")
    linhas.append(f"Duração total: {relatorio.get('duracao_total_s', 0.0):.2f}s")
    linhas.append(f"Hash do checklist: {relatorio.get('checklist_hash', '')}")
    linhas.append(f"Versão do schema: {relatorio.get('schema_version', '')}")
    linhas.append("")
    linhas.append(f"Próximo passo: sysdoc create {project_arg} dvi")

    return "\n".join(linhas)
