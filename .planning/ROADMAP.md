# ROADMAP — SysDoc GSD-Style System

## Phase Structure

| Phase | Goal | Requirements | Success Criteria |
|-------|------|--------------|------------------|
| 1 | Preparar CLI para agentes de IA | SYSD-01, SYSD-02, SYSD-03 | 3/3 |
| 2 | Implementar comando create (Word) | SYSD-04, SYSD-05 | 2/2 |
| 3 | Documentar integração com agentes | SYSD-06, SYSD-07 | 2/2 |
| 4 | Clareza de UX: fim da ambiguidade `sysdoc analyze` | SYSD-08 a SYSD-12 | 5/5 |
| 5 | Templates TR a partir dos modelos Lei 14.133 | SYSD-13 a SYSD-15 | 0/3 |

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

---

### Phase 5: Templates TR a partir dos modelos Lei 14.133

**Goal:** Criar 4 templates DOCX determinísticos derivados dos modelos Lei 14.133 em `Referencias/` (compras, serviços-e-obras, serviços-e-obras v2, contrato sem MDO exclusiva), com `{{placeholders}}` SysDoc mapeados para todos os campos do `dados_consolidados.json`, e ajustar `_select_reference_template` para preferir os novos templates.

**Mode:** standard

**Depends on:** Phase 2

**Success Criteria:**
1. 4 templates DOCX em `templates/tr/` derivados dos 4 modelos Lei 14.133, com placeholders SysDoc anotados nas seções corretas
2. Mapeamento JSON → seção documentado, cobrindo 100% dos campos do `dados_consolidados.json` aplicáveis a cada categoria
3. `_select_reference_template` prefere `templates/tr/` antes de `referencias/` (fallback mantido)
4. `sysdoc create tr` em projeto-teste gera DOCX sem placeholders `{{` remanescentes para cada uma das 4 categorias
5. Testes cobrindo cada caminho de categoria + fallback + presença de todos os campos esperados

**Requirements:**
- [ ] **SYSD-13**: Derivar e anotar 4 templates DOCX (compras, serviços-e-obras, serviços-e-obras-v2, contrato-sem-MDO) em `templates/tr/` com placeholders SysDoc
- [ ] **SYSD-14**: Atualizar `_select_reference_template` para preferir `templates/tr/` antes de `referencias/` com fallback documentado
- [ ] **SYSD-15**: Testes E2E cobrindo cada categoria, ausência de placeholders não substituídos e fallback para `referencias/`

**Plans:**
- [ ] TBD (run /gsd-plan-phase 5 to break down)

---

*Phases: 5 | Requirements: 15*
*Generated: 2026-05-07 · Updated: 2026-05-12*
