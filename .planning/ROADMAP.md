# ROADMAP — SysDoc GSD-Style System

## Phase Structure

| Phase | Goal | Requirements | Success Criteria |
|-------|------|--------------|------------------|
| 1 | Preparar CLI para agentes de IA | SYSD-01, SYSD-02, SYSD-03 | 3/3 |
| 2 | Implementar comando create (Word) | SYSD-04, SYSD-05 | 2/2 |
| 3 | Documentar integração com agentes | SYSD-06, SYSD-07 | 2/2 |
| 4 | Clareza de UX: fim da ambiguidade `sysdoc analyze` | SYSD-08 a SYSD-12 | 5/5 |

---

### Phase 1: CLI-style GSD

**Goal:** Transformar sysdoc.py em sistema estilo GSD com /sysdoc commands.

**Mode:** standard

**Success Criteria:**

1. CLI responde a /sysdoc no contexto de agentes
2. Estrutura de projeto padronizada para invocation
3. Help contextual para cada comando

**Requirements:**

- [x] **SYSD-01**: Refatorar argparse para aceitar /sysdoc prefix (mant compat)
- [x] **SYSD-02**: Adicionar estrutura de projeto .sysdoc/config.yaml
- [x] **SYSD-03**: Documentar formato de invocation em AGENTS.md

---

### Phase 2: Comando Create (Word/PDF)

**Goal:** Implementar /sysdoc create para gerar documentos conforme modelo.

**Mode:** standard

**Planning:** `.planning/phases/02-comando-create-word-pdf/02-01-PLAN.md`

**Wave 1:** Implementa `sysdoc create` para TR `.docx`, incluindo template Word, helpers determinísticos, parser, testes e documentação.

**Success Criteria:**

1. Gera arquivo .docx a partir de template
2. Preenche campos de dados_consolidados.json
3. Funciona offline/sem LLM

**Requirements:**

- [x] **SYSD-04**: Criar gerador de Word baseado em template
- [x] **SYSD-05**: Adicionar comando create ao CLI

---

### Phase 3: Integração Agentes IA

**Goal:** Documentar e testar integração com OpenCode, Claude Code, Codex, Antigravity.

**Mode:** standard

**Success Criteria:**

1. SKILL.md atualizado para invocation
2. AGENTS.md criado
3. Testado em pelo menos 2 agentes

**Requirements:**

- [ ] **SYSD-06**: Atualizar skills/sysdoc/SKILL.md para invocation
- [ ] **SYSD-07**: Criar AGENTS.md com formato de comandos

---

### Phase 4: Clareza de UX

**Goal:** Eliminar a ambiguidade de `sysdoc analyze` deixando explícito que a CLI prepara o cache e a IA faz a análise dentro de um harness. A CLI permanece 100% determinística e nunca chama LLMs — princípio permanente, não TODO futuro.

**Mode:** standard

**Success Criteria:**

1. `sysdoc analyze` exibe handoff visual em diagrama ASCII com slash command e harnesses suportados
2. `sysdoc guia` conduz o usuário passo a passo até o harness, com guarda de TTY
3. `sysdoc analyze --dry-run` reimprime o handoff sem reextrair PDFs
4. Nenhum texto da CLI menciona `--auto`, OpenRouter, API key ou modo autônomo
5. Suite de testes cobre handoff, dry-run e guia, com regressão para o princípio offline

**Requirements:**

- [x] **SYSD-08**: Refatorar `print_analysis_handoff()` em diagrama ASCII com Claude Code, OpenCode, Codex CLI e Gemini CLI
- [x] **SYSD-09**: Adicionar flag `--dry-run` em `analyze` (reimprime handoff sem reextrair)
- [x] **SYSD-10**: Implementar `sysdoc guia` com wizard interativo e proteção `isatty()`
- [x] **SYSD-11**: Cobrir handoff/dry-run/guia em `tests/test_cli.py`, incluindo regressão "no LLM mention"
- [x] **SYSD-12**: Documentar comandos em README e CHANGELOG sem alterar SKILL.md, AGENTS.md ou wrappers

### Phase 5: Motor de análise por checklist com agentes plugáveis

**Goal:** Entregar um motor de análise dirigido por checklist tipado e data-driven (`checklists/*.yaml`), executável por orquestrador via API ou por qualquer harness agêntico, com verificações determinísticas em Python (cálculo, vigência, mecânica), grounding check do campo `de`, síntese dedicada de pareceres e saída DVI em DOCX via `sysdoc create dvi` — preservando a CLI determinística sem chamadas a LLM.
**Requirements**: PRD em `.planning/phases/05-motor-analise-checklist/PRD.md` (RF1–RF10, RNF1–RNF5)
**Depends on:** Phase 4
**Plans:** 13/15 plans executed

**Onda 1:** fundação do pacote `sysdoc_dvi` + checklist tipado; padrão de nomes de artefatos; evolução do contrato de dados.
**Onda 2:** tabela de vigência; auditoria de cálculo; verificações mecânicas + grounding; mapeamento de peças; camada de provedores.
**Onda 3:** despacho por tipo; síntese de pareceres; montagem/relatório/checkpoint; `sysdoc create dvi`; conversão dos prompts DVI em checklist.
**Onda 4:** pipeline `sysdoc-dvi run`.
**Onda 5:** documentação canônica, CHANGELOG 1.5.0 e verificação com processos reais.

Plans:
**Wave 1**

- [x] 05-01-PLAN.md — Fundação do motor: pacote `sysdoc_dvi`, contratos, loader do checklist, entry point `sysdoc-dvi`
- [x] 05-02-PLAN.md — Padrão de nomes de artefatos `xx_nome_tipo_data.extensao` em publish/render/create
- [x] 05-03-PLAN.md — Contrato de dados 1.1: `origem_verificacao`, `checklist_id`, `checklist_hash`, `schema_version` e rastreabilidade

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 05-04-PLAN.md — Tabela `normas/vigencia.yaml` e verificação determinística de vigência
- [x] 05-05-PLAN.md — Auditoria aritmética da pesquisa de preços com memória de cálculo
- [x] 05-06-PLAN.md — Verificações mecânicas e grounding check do campo `de`
- [x] 05-07-PLAN.md — Mapeamento de peças por âncoras no manifest, com override e abort
- [x] 05-08-PLAN.md — Camada multi-provedor, configuração de modelos e `AgenteLLM`

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 05-09-PLAN.md — Prompts Jinja e despacho por tipo de verificação
- [x] 05-10-PLAN.md — Síntese dedicada dos pareceres executivo e por documento
- [x] 05-11-PLAN.md — Montagem do `dados_consolidados.json`, relatório de execução e checkpoint
- [x] 05-12-PLAN.md — `sysdoc create dvi` (DOCX a partir de template institucional)
- [x] 05-13-PLAN.md — Conversão dos prompts DVI em `checklists/dvi.yaml` e seed da tabela de vigência

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 05-14-PLAN.md — Pipeline `sysdoc-dvi run`, `relatorio` e `config`

**Wave 5** *(blocked on Wave 4 completion)*

- [ ] 05-15-PLAN.md — Documentação canônica, CHANGELOG 1.5.0 e verificação com processos reais

---

*Phases: 5 | Requirements: 12*
*Generated: 2026-05-07*
