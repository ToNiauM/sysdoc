# Phase 5: Motor de análise por checklist com agentes plugáveis - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-26
**Phase:** 05-motor-analise-checklist
**Areas discussed:** Entry point e operação da CLI (D2 + ergonomia), Versionamento e nomenclatura (D1+D4), Tabela de vigência (D3), Checklists e provedores LLM

---

## Entry point e operação da CLI

| Option | Description | Selected |
|--------|-------------|----------|
| Binários por produto | `sysdoc` determinístico + novo executável `sysdoc-dvi` | ✓ |
| Grupos de subcomando | `sysdoc dvi run` dentro da CLI única | |
| sysdoc-agent genérico | Recomendação original do PRD | |

**User's choice:** Binários por produto (`sysdoc-dvi`).
**Notes:** O usuário levantou (via "Other" na seleção de áreas) a necessidade de separar os fluxos TR×ETP vs DVI e deixar a operação mais fácil ("sysdoc-dvi, sysdoc-docs ou algo assim").

| Option | Description | Selected |
|--------|-------------|----------|
| Dois modos do mesmo motor | Fase 5 só DVI; comparação TR×ETP vira checklist futuro | ✓ |
| Binários separados já | Criar `sysdoc-docs` nesta fase | |
| Só DVI, decidir depois | Sem compromisso de arquitetura | |

| Option | Description | Selected |
|--------|-------------|----------|
| Pipeline completo | prepare → análise → validate → render → relatório num comando | ✓ |
| Só análise | run produz apenas JSON + relatório | |
| Pipeline com --ate | Completo com parada em etapa | |

| Option | Description | Selected |
|--------|-------------|----------|
| Checkpoint e retomada | Resultados incrementais; re-run pula itens resolvidos | ✓ |
| Sempre do zero | Reexecuta tudo a cada run | |
| Você decide | | |

---

## Versionamento e nomenclatura (D1+D4)

| Option | Description | Selected |
|--------|-------------|----------|
| Versões independentes | CLI 1.5.0 + sysdoc-dvi 0.2.0 | |
| Versão única do repo | Tudo como SysDoc 1.5.0 | ✓ |
| Você decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| ASCII sem acento | presenca, vigencia, origem_verificacao... | ✓ |
| Acentuado como o schema | presença, vigência... | |
| Você decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Prefixo por escopo | DVI-GER-001, DVI-TIC-001, DVI-AMB-001 | ✓ |
| Sequencial simples | DVI-001... | |
| Semântico por peça | ETP-VIG-01... | |

**Naming de artefatos:** primeira proposta (`[modelo]_[data]`) foi rejeitada duas vezes pelo usuário, que definiu em texto livre o padrão `xx_nome_tipo_data.extensao`. Confirmado: `xx` = contador de produção por artefato (01, 02, 03..., nunca reutilizado), `nome` = slug da pasta do projeto, `tipo` = artefato. Alternativa "contador global do projeto (estilo peças SEI)" apresentada e não escolhida. Escopo: todos os artefatos a partir da 1.5.0; arquivos antigos não renomeados.

---

## Tabela de vigência (D3)

| Option | Description | Selected |
|--------|-------------|----------|
| Global + override | `normas/vigencia.yaml` + `referencias/vigencia.yaml` por projeto | ✓ |
| Só por projeto | | |
| Só global | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Semear dos checklists | Normas citadas nos itens entram na conversão | ✓ |
| Começar vazia | | |
| Você decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Alerta após 6 meses | conferida_em > 180 dias → aviso no relatório | ✓ |
| Só exibir a data | | |
| Você decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Normalizador + aliases | Normalização determinística + campo aliases | ✓ |
| Só normalizador | | |
| Match exato | | |

---

## Checklists e provedores LLM

| Option | Description | Selected |
|--------|-------------|----------|
| Arquivo único dvi.yaml | Campo aplicabilidade roteia geral/tic/ambos | ✓ |
| Por aplicabilidade | geral.yaml + tic.yaml | |
| Por peça | etp.yaml, tr.yaml... | |

**Provedor LLM:** primeira resposta escolheu "SDK anthropic"; ao chegar na pergunta de modelos default, o usuário esclareceu em texto livre que quer escolher modelos diversos via OpenAI, OpenRouter "e afins" com chaves próprias. Decisão revisada:

| Option | Description | Selected |
|--------|-------------|----------|
| Reusar padrão do sysdoc.py | Multi-provedor via requests + ~/.sysdoc/config.json | ✓ |
| Via OpenRouter apenas | | |
| SDKs oficiais por provedor | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Exigir configuração | Sem modelos configurados → abort com instrução | ✓ |
| Default do provedor conectado | | |
| Wizard interativo | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Retry + pendente | JSON inválido → 1 retry → pendente (falha_estruturada) | ✓ |
| Abortar a execução | | |
| Você decide | | |

---

## Claude's Discretion

- Formato interno do checkpoint de retomada e do relatório de execução.
- Estrutura do pacote do orquestrador e do protocolo `AnalysisAgent`.
- Reuso da CLI como biblioteca (import vs subprocess).
- Tolerância numérica default de `calculo` e limiar default do grounding check (ambos configuráveis).

## Deferred Ideas

- Checklist `comparacao-tr-etp.yaml` no motor — fase futura.
- Binário `sysdoc-docs` — reavaliar após estabilizar `sysdoc-dvi`.
- Wizard interativo de configuração de modelos.
