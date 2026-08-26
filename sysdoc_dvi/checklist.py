"""
Carregador data-driven do checklist DVI (RF1/RF2).

`carregar_checklist` valida estruturalmente cada item do YAML e devolve
`ItemChecklist` tipados — nenhuma normalização silenciosa: valor fora do
domínio ou campo ausente vira `ErroChecklist` explícito citando o item.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml

from sysdoc_dvi.tipos import ItemChecklist

CAMPOS_OBRIGATORIOS = (
    "id",
    "aplicabilidade",
    "peca",
    "tipo",
    "pergunta",
    "base_legal_texto",
    "referencia",
    "severidade_default",
    "modelo_alvo",
    "ativo",
)

APLICABILIDADES_VALIDAS = {"geral", "tic", "ambos"}
PECAS_VALIDAS = {"ETP", "TR", "MCP", "RISCOS", "PROCESSO"}
TIPOS_VALIDOS = {"presenca", "julgamento", "calculo", "vigencia", "mecanica"}
MODELOS_ALVO_VALIDOS = {"economico", "forte"}
DOCUMENTOS_SAIDA_VALIDOS = {"ETP", "TR"}

ID_PATTERN = re.compile(r"^DVI-(GER|TIC|AMB)-\d{3}$")

_PECA_PARA_DOCUMENTO_SAIDA_PADRAO = {
    "ETP": "ETP",
    "MCP": "ETP",
    "RISCOS": "ETP",
    "PROCESSO": "ETP",
    "TR": "TR",
}


class ErroChecklist(Exception):
    """Erro estrutural no checklist DVI: valor ausente, fora de domínio ou id inválido."""


def carregar_checklist(path: str | Path) -> tuple[dict, list[ItemChecklist]]:
    checklist_path = Path(path)
    with checklist_path.open("r", encoding="utf-8") as fh:
        dados = yaml.safe_load(fh)

    if not isinstance(dados, dict):
        raise ErroChecklist(
            f"{checklist_path}: checklist inválido, esperado mapeamento no topo do YAML"
        )

    meta = {"versao": dados.get("versao"), "descricao": dados.get("descricao")}

    itens_brutos = dados.get("itens")
    if not isinstance(itens_brutos, list):
        raise ErroChecklist(f"{checklist_path}: chave 'itens' ausente ou não é uma lista")

    itens: list[ItemChecklist] = []
    ids_vistos: set[str] = set()

    for bruto in itens_brutos:
        if not isinstance(bruto, dict):
            raise ErroChecklist(f"{checklist_path}: item de checklist inválido, esperado mapeamento")

        item_id_para_mensagem = bruto.get("id", "<sem id>")

        for campo in CAMPOS_OBRIGATORIOS:
            if campo not in bruto or bruto[campo] is None:
                raise ErroChecklist(
                    f"item '{item_id_para_mensagem}': campo obrigatório ausente: '{campo}'"
                )

        item_id = bruto["id"]
        if not ID_PATTERN.match(str(item_id)):
            raise ErroChecklist(
                f"item '{item_id}': id fora do padrão esperado 'DVI-(GER|TIC|AMB)-NNN'"
            )
        if item_id in ids_vistos:
            raise ErroChecklist(f"item '{item_id}': id duplicado no checklist")
        ids_vistos.add(item_id)

        aplicabilidade = bruto["aplicabilidade"]
        if aplicabilidade not in APLICABILIDADES_VALIDAS:
            raise ErroChecklist(
                f"item '{item_id}': campo 'aplicabilidade' com valor inválido: '{aplicabilidade}'"
            )

        peca = bruto["peca"]
        if peca not in PECAS_VALIDAS:
            raise ErroChecklist(f"item '{item_id}': campo 'peca' com valor inválido: '{peca}'")

        tipo = bruto["tipo"]
        if tipo not in TIPOS_VALIDOS:
            raise ErroChecklist(f"item '{item_id}': campo 'tipo' com valor inválido: '{tipo}'")

        modelo_alvo = bruto["modelo_alvo"]
        if modelo_alvo not in MODELOS_ALVO_VALIDOS:
            raise ErroChecklist(
                f"item '{item_id}': campo 'modelo_alvo' com valor inválido: '{modelo_alvo}'"
            )

        ativo = bruto["ativo"]
        if not isinstance(ativo, bool):
            raise ErroChecklist(f"item '{item_id}': campo 'ativo' deve ser booleano")

        documento_saida = bruto.get("documento_saida")
        if documento_saida is None:
            documento_saida = _PECA_PARA_DOCUMENTO_SAIDA_PADRAO[peca]
        elif documento_saida not in DOCUMENTOS_SAIDA_VALIDOS:
            raise ErroChecklist(
                f"item '{item_id}': campo 'documento_saida' com valor inválido: '{documento_saida}'"
            )

        itens.append(
            ItemChecklist(
                id=item_id,
                aplicabilidade=aplicabilidade,
                peca=peca,
                documento_saida=documento_saida,
                tipo=tipo,
                pergunta=bruto["pergunta"],
                base_legal_texto=bruto["base_legal_texto"],
                referencia=bruto["referencia"],
                severidade_default=bruto["severidade_default"],
                modelo_alvo=modelo_alvo,
                ativo=ativo,
                parametros=bruto.get("parametros") or {},
            )
        )

    return meta, itens


def filtrar_itens(itens: list[ItemChecklist], aplicabilidade: str) -> list[ItemChecklist]:
    if aplicabilidade == "geral":
        alvo = {"geral", "ambos"}
    elif aplicabilidade == "tic":
        alvo = {"tic", "ambos"}
    else:
        raise ErroChecklist(f"aplicabilidade de filtro inválida: '{aplicabilidade}'")
    return [item for item in itens if item.aplicabilidade in alvo and item.ativo]


def hash_checklist(path: str | Path) -> str:
    checklist_path = Path(path)
    digest = hashlib.sha256()
    with checklist_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
