"""
Contratos de dados do motor de análise DVI.

Estes tipos são o contrato estável consumido por todos os planos desta fase
(carregador de checklist, verificações determinísticas, agentes de análise,
orquestrador). Não redefinir em outro módulo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

Aplicabilidade = Literal["geral", "tic", "ambos"]
Peca = Literal["ETP", "TR", "MCP", "RISCOS", "PROCESSO"]
TipoVerificacao = Literal["presenca", "julgamento", "calculo", "vigencia", "mecanica"]
ModeloAlvo = Literal["economico", "forte"]
OrigemVerificacao = Literal["llm", "deterministico", "lookup"]


@dataclass(frozen=True)
class ItemChecklist:
    id: str
    aplicabilidade: Aplicabilidade
    peca: Peca
    documento_saida: str
    tipo: TipoVerificacao
    pergunta: str
    base_legal_texto: str
    referencia: str
    severidade_default: str
    modelo_alvo: ModeloAlvo
    ativo: bool
    parametros: dict = field(default_factory=dict)


@dataclass
class UsoModelo:
    provedor: str
    modelo: str
    tokens_entrada: int
    tokens_saida: int
    custo_estimado: float
    duracao_s: float


@dataclass
class ResultadoItem:
    checklist_id: str
    origem_verificacao: OrigemVerificacao
    documento: str
    seção: str
    de: str
    para: str
    parecer: str
    fundamento: str
    classificação: str
    severidade: str
    risco_jurídico: str
    uso: UsoModelo | None = None
    falha_estruturada: str | None = None
    falha_grounding: bool = False


class AnalysisAgent(Protocol):
    def executar_item(self, item: ItemChecklist, contexto: str) -> ResultadoItem: ...

    def executar_lote(
        self, itens: list[ItemChecklist], contexto: str
    ) -> list[ResultadoItem]: ...
