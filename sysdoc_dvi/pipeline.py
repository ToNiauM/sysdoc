"""
Orquestração ponta a ponta do motor DVI (D-01, D-03, D-04, D-16, RF9).

`executar_run` é o único ponto que conhece a ordem fixa do fluxo completo:
carregar config de modelos → carregar e filtrar checklist → `sysdoc.prepare`
(se o cache ainda não existir) → mapear peças → carregar checkpoint →
executar itens do checklist → sintetizar pareceres → montar
`dados_consolidados.json` → `sysdoc.validate` → `sysdoc.render` → gravar e
imprimir o relatório de execução → limpar o checkpoint.

Este módulo importa `sysdoc` como biblioteca (`import sysdoc`) e chama
`sysdoc.prepare`/`sysdoc.validate`/`sysdoc.render` diretamente — nenhum
processo filho do próprio binário `sysdoc` é iniciado aqui (decisão
registrada em 05-CONTEXT.md); `validate`/`render` já isolam os scripts de
`templates/` em processo filho internamente, por conta própria.

Deviation from plan wording (documentado também no SUMMARY.md): `montagem.
montar_json` falha cedo (`ErroMontagem`) sempre que um `ResultadoItem` tem
`de`/`para`/`parecer`/`fundamento` vazio ou curto demais — o que inclui todo
item que degradou para `pendente` (ver `despacho._pendente` e `agente.
_resultado_pendente`, que devolvem esses campos vazios de propósito, para
nunca inventar conteúdo). Como um único item pendente não pode abortar a
montagem inteira do relatório (RF9: "um item nunca derruba a análise
inteira"), este módulo preenche, antes de `montar_json`, um texto de
preenchimento determinístico em português culto para qualquer campo com
menos de três palavras — sempre prefixando `de`/`para` com o marcador
`[OMISSÃO]` já usado em `despacho`/`grounding`/`validate_sysdoc.is_traceable`
para que a rastreabilidade também não seja acusada como fabricação.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import sysdoc
from sysdoc_dvi import despacho, provedores
from sysdoc_dvi.agente import AgenteLLM
from sysdoc_dvi.checklist import ErroChecklist, carregar_checklist, filtrar_itens, hash_checklist
from sysdoc_dvi.checkpoint import carregar_checkpoint, limpar_checkpoint, registrar_item
from sysdoc_dvi.config import ConfigDvi, ErroConfiguracaoModelos, carregar_config_dvi
from sysdoc_dvi.despacho import executar_checklist
from sysdoc_dvi.montagem import SCHEMA_VERSION, ErroMontagem, montar_json
from sysdoc_dvi.normas import ErroVigencia, carregar_vigencia
from sysdoc_dvi.pecas import ErroMapeamentoPeca, mapear_pecas
from sysdoc_dvi.provedores import chamar_modelo
from sysdoc_dvi.relatorio import montar_relatorio, renderizar_relatorio
from sysdoc_dvi.sintese import AgenteSintese, ErroSintese, sintetizar
from sysdoc_dvi.tipos import AnalysisAgent, ResultadoItem

_ROOT = Path(__file__).resolve().parents[1]
_CHECKLIST_PADRAO = _ROOT / "checklists" / "dvi.yaml"
_VIGENCIA_PADRAO = _ROOT / "normas" / "vigencia.yaml"

_CAMPOS_TEXTO_OBRIGATORIOS = ("de", "para", "parecer", "fundamento")
_CONTAGEM_PALAVRAS = re.compile(r"\b\w+\b", re.UNICODE)

_ERROS_CONHECIDOS = (
    ErroConfiguracaoModelos,
    ErroChecklist,
    ErroMapeamentoPeca,
    ErroVigencia,
    ErroSintese,
    ErroMontagem,
)


class ErroPipeline(Exception):
    """Erro conhecido do orquestrador (aplicabilidade ausente/inválida, checklist vazio etc.), com o remédio na própria mensagem."""


def _contar_palavras(texto: object) -> int:
    return len(_CONTAGEM_PALAVRAS.findall(str(texto or "")))


def derivar_modelo_ia(alvo: str) -> str:
    """Deriva o slug de `modelo_ia` a partir do alvo `provedor/modelo`.

    Alvos de OpenRouter podem ter prefixo de fornecedor e sufixo de variante
    (ex.: `openrouter/z-ai/glm-5.2:free`): usa-se sempre o último segmento do
    caminho e os caracteres fora do domínio do validador (`[a-z0-9._-]`) são
    substituídos por hífen, preservando um slug real e válido do modelo.
    """
    slug = str(alvo or "").rsplit("/", 1)[-1].strip().lower()
    slug = re.sub(r"[^a-z0-9._-]+", "-", slug)
    return slug.strip("._-")


def _texto_placeholder(campo: str, resultado: ResultadoItem) -> str:
    motivo = str(resultado.falha_estruturada or resultado.parecer or "").strip()
    if campo in ("de", "para"):
        return (
            f"[OMISSÃO] item {resultado.checklist_id} sem trecho localizado; "
            "pendente de verificação humana"
        )
    if campo == "parecer":
        detalhe = motivo or "sem detalhamento adicional disponível"
        return f"Item pendente de verificação humana: {detalhe}"
    return "Fundamentação não disponível; item classificado como pendente para revisão humana."


def _preencher_pendencias(resultados: list[ResultadoItem]) -> list[ResultadoItem]:
    completados: list[ResultadoItem] = []
    for resultado in resultados:
        atualizacoes: dict[str, str] = {}
        for campo in _CAMPOS_TEXTO_OBRIGATORIOS:
            if _contar_palavras(getattr(resultado, campo)) < 3:
                atualizacoes[campo] = _texto_placeholder(campo, resultado)
        completados.append(replace(resultado, **atualizacoes) if atualizacoes else resultado)
    return completados


class _AdaptadorAgenteSintese:
    """Casa o `AgenteLLM` (protocolo `AnalysisAgent`) com o protocolo `AgenteSintese`
    exigido por `sysdoc_dvi.sintese.sintetizar` (05-10), chamando o provedor
    diretamente para o alvo `forte`/`economico` já resolvido em `ConfigDvi`.
    """

    def __init__(self, config: ConfigDvi) -> None:
        self._config = config

    def chamar(self, alvo: str, prompt: str, *, schema: dict | None = None):
        alvo_resolvido = self._config.forte if alvo == "forte" else self._config.economico
        return chamar_modelo(
            alvo_resolvido,
            prompt,
            schema=schema,
            timeout_s=self._config.timeout_s,
            max_retries=self._config.max_retries,
        )


def _resolver_agente_sintese(agente_execucao: AnalysisAgent, config: ConfigDvi) -> AgenteSintese:
    chamar = getattr(agente_execucao, "chamar", None)
    if callable(chamar):
        return agente_execucao  # já implementa AgenteSintese (ex.: agente injetado em teste)
    return _AdaptadorAgenteSintese(config)


def _montar_projeto_info(config_projeto: dict, textos: dict[str, str]) -> dict:
    orgao = str(config_projeto.get("orgao") or config_projeto.get("órgão") or "").strip()
    processo = str(config_projeto.get("processo") or "").strip()
    valor_estimado = str(config_projeto.get("valor_estimado") or "").strip()
    objeto = str(config_projeto.get("objeto") or "").strip()

    if not processo:
        processo = sysdoc.detect_process(textos)
    if not valor_estimado:
        valores = sysdoc.detect_values(textos)
        valor_estimado = valores[0] if valores else "não identificado"
    if not objeto:
        objeto = sysdoc.detect_object(textos)
    if not orgao:
        orgao = "não identificado"

    return {"órgão": orgao, "processo": processo, "valor_estimado": valor_estimado, "objeto": objeto}


def _gravar_relatorio(
    paths: "sysdoc.ProjectPaths",
    projeto_arg: str,
    resultados: list[ResultadoItem],
    checklist_hash: str,
    schema_version: str,
    pecas_mapeadas: dict,
    tabela_vigencia: dict,
    limiar_dias: int,
    duracao_total_s: float,
) -> Path:
    relatorio = montar_relatorio(
        resultados,
        checklist_hash,
        schema_version or SCHEMA_VERSION,
        duracao_total_s,
        pecas_mapeadas=pecas_mapeadas,
        tabela_vigencia=tabela_vigencia,
        limiar_dias_vigencia=limiar_dias,
    )
    paths.output.mkdir(parents=True, exist_ok=True)
    data = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    destino = sysdoc.proximo_nome_artefato(paths.output, paths.root.name, "relatorio", data, ".json")
    destino.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")
    print(renderizar_relatorio(relatorio, projeto_arg))
    print(f"Relatório salvo em: {sysdoc.rel(destino)}")
    return destino


def executar_run(
    projeto: str,
    tipo: str | None = None,
    checklist: str | None = None,
    economico: str | None = None,
    forte: str | None = None,
    retomar: bool = True,
    agente: AnalysisAgent | None = None,
) -> int:
    inicio = time.monotonic()
    try:
        return _executar_run(projeto, tipo, checklist, economico, forte, retomar, agente, inicio)
    except _ERROS_CONHECIDOS as exc:
        print(str(exc))
        return 1
    except ErroPipeline as exc:
        print(str(exc))
        return 1


def _executar_run(
    projeto: str,
    tipo: str | None,
    checklist: str | None,
    economico: str | None,
    forte: str | None,
    retomar: bool,
    agente: AnalysisAgent | None,
    inicio: float,
) -> int:
    provedores.limpar_registro_chamadas()

    print("1) Carregando configuração de modelos...")
    config = carregar_config_dvi(economico=economico, forte=forte)

    paths = sysdoc.project_paths(projeto)
    config_projeto = sysdoc.load_config(paths)

    tipo_efetivo = tipo or config_projeto.get("tipo")
    if not tipo_efetivo:
        raise ErroPipeline(
            "aplicabilidade não declarada: informe --tipo geral|tic ou defina 'tipo: geral' "
            f"(ou 'tic') em {sysdoc.rel(paths.config)}."
        )
    if tipo_efetivo not in ("geral", "tic"):
        raise ErroPipeline(
            f"aplicabilidade inválida: '{tipo_efetivo}' (esperado 'geral' ou 'tic'); "
            f"corrija --tipo ou o campo 'tipo' em {sysdoc.rel(paths.config)}."
        )

    checklist_path = Path(checklist) if checklist else _CHECKLIST_PADRAO
    print(f"2) Carregando checklist {sysdoc.rel(checklist_path)}...")
    _meta, todos_itens = carregar_checklist(checklist_path)
    itens = filtrar_itens(todos_itens, tipo_efetivo)
    if not itens:
        raise ErroPipeline(
            f"nenhum item ativo do checklist se aplica a '{tipo_efetivo}' em "
            f"{sysdoc.rel(checklist_path)}; ative itens ou ajuste --tipo."
        )
    checklist_hash_atual = hash_checklist(checklist_path)
    print(f"   {len(itens)} item(ns) ativo(s) para '{tipo_efetivo}'.")

    if not paths.manifest.is_file():
        print("3) Preparando cache do projeto (sysdoc prepare)...")
        resultado_prepare = sysdoc.prepare(projeto)
        if resultado_prepare != 0:
            return resultado_prepare
    else:
        print("3) Cache já preparado; reaproveitando.")

    pecas_exigidas = {item.peca for item in itens}
    print(f"4) Mapeando peças exigidas: {', '.join(sorted(pecas_exigidas)) or 'nenhuma'}...")
    pecas_mapeadas = mapear_pecas(paths.root, pecas_exigidas)
    textos = {
        peca: mapeada.caminho.read_text(encoding="utf-8") for peca, mapeada in pecas_mapeadas.items()
    }

    tabela_vigencia = carregar_vigencia(_VIGENCIA_PADRAO, paths.root / "normas" / "vigencia.yaml")

    agente_execucao = agente or AgenteLLM(config, schemas_por_tipo=despacho.SCHEMAS_POR_TIPO)

    checkpoint_resolvido = carregar_checkpoint(paths.root, checklist_hash_atual) if retomar else {}
    itens_pendentes = [item for item in itens if item.id not in checkpoint_resolvido]
    if checkpoint_resolvido:
        print(f"   Retomando: {len(checkpoint_resolvido)} item(ns) já resolvido(s) no checkpoint.")
    print(f"5) Executando checklist ({len(itens_pendentes)} item(ns) pendente(s))...")

    def _ao_concluir(resultado: ResultadoItem) -> None:
        registrar_item(paths.root, checklist_hash_atual, resultado)

    novos_resultados = executar_checklist(
        itens_pendentes,
        textos,
        agente_execucao,
        tabela_vigencia,
        limiar_grounding=config.limiar_grounding,
        ao_concluir=_ao_concluir,
    )

    resultados_por_id = dict(checkpoint_resolvido)
    for resultado in novos_resultados:
        resultados_por_id[resultado.checklist_id] = resultado
    resultados = _preencher_pendencias([resultados_por_id[item.id] for item in itens])

    print("6) Sintetizando pareceres (modelo forte)...")
    agente_sintese = _resolver_agente_sintese(agente_execucao, config)
    projeto_info = _montar_projeto_info(config_projeto, textos)
    pareceres = sintetizar(
        resultados,
        projeto_info,
        agente_sintese,
        numero_etp=str(config_projeto.get("numero_etp") or "não informado"),
        numero_tr=str(config_projeto.get("numero_tr") or "não informado"),
    )

    documentos_analisados = sorted({resultado.documento for resultado in resultados})
    modelo_ia = derivar_modelo_ia(config.forte) or config.forte
    data_analise = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print("7) Montando dados_consolidados.json...")
    dados = montar_json(
        resultados,
        pareceres,
        projeto_info,
        modelo_ia,
        checklist_hash_atual,
        documentos_analisados,
        data_analise,
    )

    dados_path = paths.root / "dados_consolidados.json"
    dados_path.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   JSON gravado: {sysdoc.rel(dados_path)}")

    print("8) Validando (sysdoc validate)...")
    rc_validate = sysdoc.validate(projeto, str(dados_path))
    if rc_validate != 0:
        print("   Validação falhou; JSON e relatório preservados para inspeção.")
        _gravar_relatorio(
            paths,
            projeto,
            resultados,
            checklist_hash_atual,
            dados.get("schema_version", ""),
            pecas_mapeadas,
            tabela_vigencia,
            config.limiar_curadoria_dias,
            time.monotonic() - inicio,
        )
        return rc_validate

    print("9) Renderizando HTML (sysdoc render)...")
    rc_render = sysdoc.render(projeto, str(dados_path))
    if rc_render != 0:
        return rc_render

    _gravar_relatorio(
        paths,
        projeto,
        resultados,
        checklist_hash_atual,
        dados.get("schema_version", ""),
        pecas_mapeadas,
        tabela_vigencia,
        config.limiar_curadoria_dias,
        time.monotonic() - inicio,
    )

    limpar_checkpoint(paths.root)
    return 0
