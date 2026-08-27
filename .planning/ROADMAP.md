# ROADMAP — SysDoc GSD-Style System

## Phase Structure

| Phase | Goal | Requirements | Success Criteria |
|-------|------|--------------|------------------|
| 1 | Preparar CLI para agentes de IA | SYSD-01, SYSD-02, SYSD-03 | 3/3 |
| 2 | Implementar comando create (Word) | SYSD-04, SYSD-05 | 2/2 |
| 3 | Documentar integração com agentes | SYSD-06, SYSD-07 | 2/2 |
| 4 | Clareza de UX: fim da ambiguidade `sysdoc analyze` | SYSD-08 a SYSD-12 | 5/5 |
| 5 | Motor de análise por checklist com agentes plugáveis | PRD RF1–RF10 | 15/15 |
| 6 | Templates DOCX institucionais (aberta, por rodadas) | SYSD-16 a SYSD-18 (r1) · SYSD-13 a SYSD-15 (r2) | 4/7 |
| 7 | Interface web para pregoeiros | TBD | 0/0 |

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
**Plans:** 15/15 plans complete

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

- [x] 05-14-PLAN.md — Pipeline `sysdoc-dvi run`, `relatorio` e `config`

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 05-15-PLAN.md — Documentação canônica, CHANGELOG 1.5.0 e verificação com processos reais

---

### Phase 6: Templates DOCX institucionais

**Goal:** Entregar os templates DOCX determinísticos dos documentos institucionais do SysDoc, por rodadas. **Rodada 1 (ativa): Despacho de Verificação Inicial (DVI)** — template fiel ao modelo institucional real, alimentado pelo `dados_consolidados.json` do `sysdoc-dvi run`, contendo tão somente o que a Unidade Demandante precisa corrigir. **Rodada 2: TR** (modelos Lei 14.133). **Rodada 3: ETP**. A fase permanece aberta entre as rodadas.

**Mode:** standard

**Depends on:** Phase 2 (motor de geração DOCX), Phase 5 (motor DVI e contrato de dados)

**Context:** `.planning/phases/06-templates-tr-a-partir-dos-modelos-lei-14-133/06-CONTEXT.md` — decisões travadas D-01 a D-14. Leitura obrigatória antes de planejar; o escopo foi repactuado pelo dono do produto em 2026-08-26.

#### Rodada 1 — Despacho de Verificação Inicial (ativa)

**Success Criteria:**

1. `templates/dvi/despacho_geral.docx` e `templates/dvi/despacho_tic.docx` gerados por script determinístico, fiéis a `processo-teste/referencias/dvi.md` (título, vocativo, contextualização, seções por peça, Observações, assinatura e "De acordo")
2. Corpo montado por builder que emite XML de parágrafo com estilos nomeados, contendo apenas `ajuste_necessário` e `risco` em seções dinâmicas por peça, com pendências de documento ausente em seção própria ao final e referência cruzada automática entre peças
3. `sysdoc create <pasta> dvi` resolve a variante por `tipo: geral|tic` do `.sysdoc/config.yaml`, mantendo a precedência do `referencias/dvi.docx` do projeto
4. Sigla DVI expandida como **Despacho de Verificação Inicial** em todo o repo (9 arquivos + 2 fixtures de teste)
5. Testes E2E em `processo-teste` sem placeholders `{{` remanescentes, cobrindo as duas variantes, o override do projeto e a exclusão de itens `conforme`

**Requirements:**

- [x] **SYSD-16**: Gerador determinístico dos templates `templates/dvi/despacho_{geral,tic}.docx` com estilos nomeados e ZIP byte-estável
- [x] **SYSD-17**: Builder do corpo do despacho (filtro, numeração dinâmica por peça, alíneas `parecer`+`fundamento`, referência cruzada) e placeholder raw com allowlist explícita em `render_docx_template`
- [ ] **SYSD-18**: Resolução de variante por `tipo` no `create`/`seed_dvi_template`, correção da sigla no repo e testes E2E

#### Rodada 2 — Templates TR (pendente)

**Success Criteria:**

1. Templates DOCX em `templates/tr/` derivados dos modelos Lei 14.133 em `Referencias/`, com placeholders SysDoc anotados nas seções corretas
2. Mapeamento JSON → seção documentado, cobrindo 100% dos campos do `dados_consolidados.json` aplicáveis a cada categoria
3. `_select_reference_template` prefere `templates/tr/` antes de `referencias/` (fallback mantido)
4. `sysdoc create tr` gera DOCX sem placeholders `{{` remanescentes para cada categoria
5. Testes cobrindo cada caminho de categoria + fallback + presença de todos os campos esperados

**Requirements:**

- [ ] **SYSD-13**: Derivar e anotar os templates DOCX de TR em `templates/tr/` com placeholders SysDoc
- [ ] **SYSD-14**: Atualizar `_select_reference_template` para preferir `templates/tr/` antes de `referencias/` com fallback documentado
- [ ] **SYSD-15**: Testes E2E cobrindo cada categoria, ausência de placeholders não substituídos e fallback para `referencias/`

> **Achado do scout (2026-08-26):** existem **3 modelos distintos**, não 4 — `…servicos-e-obras…(1).docx` é byte-idêntico ao `…servicos-e-obras….docx` (md5 `a226e3c7b43485df18e7358153792131`) e o terceiro é um **Termo de Contrato**, não um TR. `_detect_procurement_category()` devolve 4 categorias contra 3 modelos reais; resolver esse descasamento é pré-requisito da rodada 2.

#### Rodada 3 — Template ETP (pendente)

Escopo a definir após a rodada 2.

**Plans:** 7 plans (rodada 1 — DVI)

Plans:
**Wave 1**

- [x] 06-01-PLAN.md — Gerador determinístico de `templates/dvi/despacho_{geral,tic}.docx` com estilos nomeados (wave 1)
- [x] 06-02-PLAN.md — Builder `sysdoc_docx/corpo_dvi.py`: filtro, numeração dinâmica por peça, alíneas e referência cruzada (wave 1)
- [x] 06-03-PLAN.md — Sigla DVI = Despacho de Verificação Inicial em todo o repo, com teste de regressão (wave 1)
- [x] 06-04-PLAN.md — Canal `raw_xml` separado (allowlist `RAW_XML_KEYS`) em `render_docx_template` e bloco `despacho:` no config (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 06-05-PLAN.md — Resolução de variante por `tipo` em `create`/`seed_dvi_template`, com precedência do projeto (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 06-06-PLAN.md — E2E sobre `processo-teste` nas duas variantes, documentação e CHANGELOG (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 06-07-PLAN.md — Checkpoint: destino de `templates/dvi_base.docx` (formato relatório) (wave 4)

### Phase 7: Interface web para pregoeiros

**Goal:** Abstrair todos os comandos do SysDoc num fluxo visual para pregoeiros: upload dos documentos do processo (PDF único ou peças separadas), extração e carregamento (prepare + fatiador de peças), análise (motor `sysdoc-dvi` com progresso em tempo real) e output com a análise em HTML e DOCX — sem o usuário tocar em terminal, YAML ou JSON.
**Requirements**: TBD
**Depends on:** Phase 5 (motor DVI); beneficia-se dos templates da Phase 6 para o output DOCX
**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 7 to break down)

---

*Phases: 7 | Requirements: 18*
*Generated: 2026-05-07 · Updated: 2026-08-26*

> **Nota de sincronia:** SYSD-13 a SYSD-18 existem apenas neste ROADMAP; `REQUIREMENTS.md` ainda para em SYSD-10. Sincronizar quando conveniente.
