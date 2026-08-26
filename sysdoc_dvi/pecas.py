"""
Mapeamento de peças (RF3).

Localiza ETP, TR, MCP, RISCOS e PROCESSO entre os textos extraídos pelo
`sysdoc prepare`, usando as âncoras textuais gravadas em `manifest.json`
(ver `sysdoc.detectar_ancoras`), com override manual em `.sysdoc/config.yaml`
(chave `pecas`) e abort explícito — via `ErroMapeamentoPeca` — quando uma
peça exigida não é localizada.

Mitigação do risco nº 1 do PRD: nenhum item pode ser avaliado contra a
peça errada.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - pyyaml é dependência do projeto
    yaml = None

PECAS_VALIDAS = {"ETP", "TR", "MCP", "RISCOS", "PROCESSO"}


class ErroMapeamentoPeca(Exception):
    """Peça obrigatória não localizada, override inválido ou ambiguidade sem remédio."""


@dataclass(frozen=True)
class PecaMapeada:
    peca: str
    label: str
    caminho: Path
    origem: str
    score: int


def _carregar_manifest(projeto: Path) -> dict:
    manifest_path = projeto / ".sysdoc" / "cache" / "manifest.json"
    if not manifest_path.is_file():
        raise ErroMapeamentoPeca(
            f"manifest não encontrado em {manifest_path}; rode 'sysdoc prepare {projeto}' antes de mapear peças."
        )
    with manifest_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _carregar_overrides_config(projeto: Path) -> dict[str, str]:
    config_path = projeto / ".sysdoc" / "config.yaml"
    if not config_path.is_file() or yaml is None:
        return {}
    try:
        dados = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(dados, dict):
        return {}
    pecas = dados.get("pecas")
    if not isinstance(pecas, dict):
        return {}
    return {str(chave).upper(): str(valor) for chave, valor in pecas.items()}


def _resolver_caminho_cache(projeto: Path, entrada: dict) -> Path:
    cache_dir = (projeto / ".sysdoc" / "cache").resolve()
    caminho = Path(entrada["cache"])
    caminho = caminho if caminho.is_absolute() else (projeto / caminho)
    caminho = caminho.resolve()
    try:
        caminho.relative_to(cache_dir)
    except ValueError:
        raise ErroMapeamentoPeca(
            f"caminho de cache fora de {cache_dir} para o arquivo '{entrada.get('label')}': {caminho}"
        )
    return caminho


def _remedio_pecas_yaml(peca: str) -> str:
    return f"pecas:\n  {peca.lower()}: <nome-do-arquivo>"


def _listar_candidatos(entradas: list[dict], peca: str) -> str:
    if not entradas:
        return "nenhum arquivo em documentos/"
    partes = [
        f"{entrada['label']} (âncoras {peca}: {entrada.get('ancoras', {}).get(peca, 0)})"
        for entrada in entradas
    ]
    return ", ".join(partes)


def _resolver_por_override(
    projeto: Path, peca: str, valor_override: str, entradas_documentos: list[dict]
) -> PecaMapeada:
    alvo = valor_override.strip().lower()
    for entrada in entradas_documentos:
        nome_arquivo = Path(entrada.get("source", "")).name.lower()
        if nome_arquivo == alvo or entrada.get("source", "").lower() == alvo:
            caminho = _resolver_caminho_cache(projeto, entrada)
            return PecaMapeada(
                peca=peca,
                label=entrada["label"],
                caminho=caminho,
                origem="override",
                score=0,
            )
    raise ErroMapeamentoPeca(
        f"override de peça '{peca}' aponta para '{valor_override}', mas nenhum arquivo com esse nome "
        f"foi encontrado no manifest. Arquivos disponíveis: {_listar_candidatos(entradas_documentos, peca)}. "
        "Rode 'sysdoc prepare' novamente ou corrija o valor em .sysdoc/config.yaml."
    )


def _resolver_por_ancora(
    peca: str, entradas_documentos: list[dict]
) -> tuple[dict, int] | None:
    candidatos = [
        entrada for entrada in entradas_documentos if entrada.get("peca_sugerida") == peca
    ]
    if not candidatos:
        return None

    candidatos_ordenados = sorted(
        candidatos,
        key=lambda entrada: entrada.get("ancoras", {}).get(peca, 0),
        reverse=True,
    )
    melhor = candidatos_ordenados[0]
    melhor_score = melhor.get("ancoras", {}).get(peca, 0)
    segunda_score = (
        candidatos_ordenados[1].get("ancoras", {}).get(peca, 0)
        if len(candidatos_ordenados) > 1
        else -1
    )
    if melhor_score == segunda_score:
        empatados = [
            entrada
            for entrada in candidatos_ordenados
            if entrada.get("ancoras", {}).get(peca, 0) == melhor_score
        ]
        nomes = ", ".join(
            f"{entrada['label']} ({entrada.get('ancoras', {}).get(peca, 0)} âncoras)"
            for entrada in empatados
        )
        raise ErroMapeamentoPeca(
            f"peça '{peca}' ambígua: mais de um arquivo com a mesma contagem de âncoras ({nomes}). "
            f"Declare manualmente em .sysdoc/config.yaml:\n{_remedio_pecas_yaml(peca)}"
        )
    return melhor, melhor_score


def _resolver_por_nome(peca: str, entradas_documentos: list[dict]) -> dict | None:
    for entrada in entradas_documentos:
        nome_stem = Path(entrada.get("source", "")).stem.upper()
        label = str(entrada.get("label", "")).upper()
        if nome_stem == peca or label == peca:
            return entrada
    return None


def mapear_pecas(
    projeto: Path,
    exigidas: set[str],
    overrides: dict[str, str] | None = None,
) -> dict[str, PecaMapeada]:
    projeto = Path(projeto)
    manifest = _carregar_manifest(projeto)
    overrides_efetivos = _carregar_overrides_config(projeto)
    if overrides:
        overrides_efetivos.update({str(chave).upper(): str(valor) for chave, valor in overrides.items()})

    entradas_documentos = [
        item for item in manifest.get("files", []) if item.get("category") == "documentos"
    ]

    resultado: dict[str, PecaMapeada] = {}
    pecas_a_resolver = (set(overrides_efetivos) | set(exigidas)) & PECAS_VALIDAS

    for peca in pecas_a_resolver:
        if peca in overrides_efetivos:
            resultado[peca] = _resolver_por_override(
                projeto, peca, overrides_efetivos[peca], entradas_documentos
            )
            continue

        vencedor_ancora = _resolver_por_ancora(peca, entradas_documentos)
        if vencedor_ancora is not None:
            entrada, score = vencedor_ancora
            caminho = _resolver_caminho_cache(projeto, entrada)
            resultado[peca] = PecaMapeada(
                peca=peca,
                label=entrada["label"],
                caminho=caminho,
                origem="ancora",
                score=score,
            )
            continue

        entrada_por_nome = _resolver_por_nome(peca, entradas_documentos)
        if entrada_por_nome is not None:
            caminho = _resolver_caminho_cache(projeto, entrada_por_nome)
            resultado[peca] = PecaMapeada(
                peca=peca,
                label=entrada_por_nome["label"],
                caminho=caminho,
                origem="nome",
                score=0,
            )
            continue

        if peca in exigidas:
            raise ErroMapeamentoPeca(
                f"peça obrigatória '{peca}' não localizada entre os documentos preparados. "
                f"Arquivos disponíveis: {_listar_candidatos(entradas_documentos, peca)}. "
                f"Declare manualmente em .sysdoc/config.yaml:\n{_remedio_pecas_yaml(peca)}"
            )

    return resultado
