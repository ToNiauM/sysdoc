"""
Montagem do dados_consolidados.json a partir dos `ResultadoItem` do motor DVI.

`montar_json` converte a lista de `ResultadoItem` produzida pelo motor no
contrato do validador vigente (RNF5): renumera por documento (`ETP-NNN`/
`TR-NNN`), preserva o `checklist_id` original em campo próprio, preenche a
trilha de auditoria (`origem_verificacao`, `metadados`, `schema_version`,
`checklist_hash`) e falha cedo com `ErroMontagem` — antes de gravar
qualquer coisa em disco — sempre que o resultado não sobreviveria ao
`sysdoc validate` (campos vazios ou curtos demais, coerência
classificação/risco/severidade, `modelo_ia` inválido, `checklist_hash`
malformado).

`pareceres` aceita tanto um `dict` quanto qualquer objeto com os atributos
`parecer_executivo`, `secao_etp` e `secao_tr` (cada seção, por sua vez, com
`classificação_documento`, `parecer_documento` e `numero`) — o mesmo
formato produzido pela síntese dedicada (RF6), sem acoplar esta montagem a
um tipo concreto ainda não publicado.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from sysdoc_dvi.tipos import ResultadoItem

_ROOT = Path(__file__).resolve().parents[1]
_TEMPLATES_DIR = _ROOT / "templates"
if str(_TEMPLATES_DIR) not in sys.path:
    sys.path.insert(0, str(_TEMPLATES_DIR))

from validate_sysdoc import validate_item_coherence  # noqa: E402

SCHEMA_VERSION = "1.1"

_MODELO_IA_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_GENERIC_MODELS = {"ia", "modelo", "default", "llm", "ai", "gpt", "claude", "gemini"}
_CHECKLIST_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")

_CAMPOS_TEXTO_OBRIGATORIOS = ("de", "para", "parecer", "fundamento")
_CAMPOS_PROJETO_OBRIGATORIOS = ("órgão", "processo", "valor_estimado", "objeto")
_DOCUMENTOS_SAIDA = ("ETP", "TR")


class ErroMontagem(Exception):
    """Erro estrutural na montagem do dados_consolidados.json (RNF5)."""


def _contar_palavras(texto: str) -> int:
    return len(re.findall(r"\b\w+\b", str(texto or ""), flags=re.UNICODE))


def _validar_modelo_ia(modelo_ia: str) -> None:
    modelo = str(modelo_ia or "").strip()
    if not modelo:
        raise ErroMontagem("modelo_ia ausente: informe o slug real do modelo utilizado")
    if modelo.lower() in _GENERIC_MODELS:
        raise ErroMontagem(
            f"modelo_ia inválido: '{modelo}' é um valor genérico; use o slug real do modelo"
        )
    if not _MODELO_IA_PATTERN.fullmatch(modelo):
        raise ErroMontagem(
            f"modelo_ia inválido: '{modelo}' deve estar em slug minúsculo "
            "(letras, números, pontos, hífens ou underscores)"
        )


def _validar_checklist_hash(checklist_hash: str) -> None:
    if not _CHECKLIST_HASH_PATTERN.fullmatch(str(checklist_hash or "")):
        raise ErroMontagem(
            f"checklist_hash inválido: '{checklist_hash}' deve ser um hash sha256 "
            "hexadecimal de 64 caracteres"
        )


def _validar_projeto(projeto: dict) -> None:
    if not isinstance(projeto, dict):
        raise ErroMontagem(
            "projeto: deve ser um mapeamento com órgão, processo, valor_estimado e objeto"
        )
    for campo in _CAMPOS_PROJETO_OBRIGATORIOS:
        valor = projeto.get(campo)
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            raise ErroMontagem(f"projeto: campo obrigatório ausente ou vazio: '{campo}'")


def _titulo_item(resultado: ResultadoItem) -> str:
    texto_base = (resultado.parecer or resultado.fundamento or resultado.checklist_id).strip()
    primeira_frase = texto_base.split(".")[0].strip() or texto_base
    palavras = primeira_frase.split()
    if len(palavras) > 12:
        primeira_frase = " ".join(palavras[:12]) + "..."
    return primeira_frase


def _validar_textos(resultado: ResultadoItem) -> None:
    for campo in _CAMPOS_TEXTO_OBRIGATORIOS:
        valor = getattr(resultado, campo)
        if _contar_palavras(valor) < 3:
            raise ErroMontagem(
                f"item '{resultado.checklist_id}': campo '{campo}' vazio ou curto demais "
                "para compor o dados_consolidados.json"
            )


def _montar_item(resultado: ResultadoItem, documento: str, numero: int) -> dict:
    classificacao = resultado.classificação
    risco = resultado.risco_jurídico
    if classificacao == "conforme" and risco != "informativo":
        risco = "informativo"

    item = {
        "id": f"{documento}-{numero:03d}",
        "número": numero,
        "item": _titulo_item(resultado),
        "documento": documento,
        "seção": resultado.seção,
        "de": resultado.de,
        "para": resultado.para,
        "parecer": resultado.parecer,
        "fundamento": resultado.fundamento,
        "classificação": classificacao,
        "severidade": resultado.severidade,
        "risco_jurídico": risco,
        "status_delic": "novo",
        "alterado_pelo_jurídico": False,
        "origem_verificacao": resultado.origem_verificacao,
        "checklist_id": resultado.checklist_id,
    }

    erros_coerencia: list[str] = []
    validate_item_coherence(erros_coerencia, item, f"itens[{item['id']}]")
    if erros_coerencia:
        raise ErroMontagem(
            f"item '{resultado.checklist_id}' falhou na checagem de coerência: "
            + "; ".join(erros_coerencia)
        )

    return item


def _campo(fonte: Any, nome: str, obrigatorio: bool = True) -> Any:
    if isinstance(fonte, dict):
        valor = fonte.get(nome)
    else:
        valor = getattr(fonte, nome, None)
    if obrigatorio and (valor is None or (isinstance(valor, str) and not valor.strip())):
        raise ErroMontagem(f"pareceres: campo obrigatório ausente ou vazio: '{nome}'")
    return valor


def _montar_secao(pareceres: Any, chave: str) -> dict:
    secao = pareceres.get(chave) if isinstance(pareceres, dict) else getattr(pareceres, chave, None)
    if secao is None:
        raise ErroMontagem(f"pareceres: seção obrigatória ausente: '{chave}'")
    return {
        "classificação_documento": _campo(secao, "classificação_documento"),
        "parecer_documento": _campo(secao, "parecer_documento"),
        "numero": _campo(secao, "numero"),
    }


def _origem_resumo(itens: list[ResultadoItem]) -> str:
    contagem: dict[str, int] = {}
    for item in itens:
        contagem[item.origem_verificacao] = contagem.get(item.origem_verificacao, 0) + 1
    partes = [f"{origem}: {quantidade}" for origem, quantidade in sorted(contagem.items())]
    return ", ".join(partes) if partes else "nenhuma"


def montar_json(
    itens: list[ResultadoItem],
    pareceres: Any,
    projeto: dict,
    modelo_ia: str,
    checklist_hash: str,
    documentos_analisados: list[str],
    data_analise: str,
) -> dict:
    _validar_modelo_ia(modelo_ia)
    _validar_checklist_hash(checklist_hash)
    _validar_projeto(projeto)

    if not itens:
        raise ErroMontagem("nenhum item de resultado foi informado à montagem")
    if not documentos_analisados:
        raise ErroMontagem("documentos_analisados: deve conter ao menos um documento analisado")

    for resultado in itens:
        if resultado.documento not in _DOCUMENTOS_SAIDA:
            raise ErroMontagem(
                f"item '{resultado.checklist_id}': documento de saída inválido "
                f"'{resultado.documento}'"
            )
        _validar_textos(resultado)

    itens_montados: list[dict] = []
    for documento in _DOCUMENTOS_SAIDA:
        itens_do_documento = [item for item in itens if item.documento == documento]
        for numero, resultado in enumerate(itens_do_documento, start=1):
            itens_montados.append(_montar_item(resultado, documento, numero))

    metadados = [
        {"label": "Hash do checklist", "valor": checklist_hash},
        {"label": "Versão do schema", "valor": SCHEMA_VERSION},
        {"label": "Itens verificados", "valor": str(len(itens))},
        {"label": "Origem das verificações", "valor": _origem_resumo(itens)},
    ]

    return {
        "titulo": "Análise Comparativa DVI",
        "subtitulo": f"Processo {projeto.get('processo', '')}",
        "modelo_ia": modelo_ia,
        "data_análise": data_analise,
        "projeto": dict(projeto),
        "metadados": metadados,
        "documentos_analisados": list(documentos_analisados),
        "parecer_executivo": _campo(pareceres, "parecer_executivo"),
        "secao_etp": _montar_secao(pareceres, "secao_etp"),
        "secao_tr": _montar_secao(pareceres, "secao_tr"),
        "itens": itens_montados,
        "nota_integridade": (
            "Análise gerada automaticamente pelo motor DVI a partir do checklist "
            f"tipado; {len(itens)} itens verificados sob o hash {checklist_hash}."
        ),
        "schema_version": SCHEMA_VERSION,
        "checklist_hash": checklist_hash,
    }
