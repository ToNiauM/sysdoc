# ROADMAP — SysDoc GSD-Style System

## Phase Structure

| Phase | Goal | Requirements | Success Criteria |
|-------|------|--------------|------------------|
| 1 | Preparar CLI para agentes de IA | SYSD-01, SYSD-02, SYSD-03 | 3/3 |
| 2 | Implementar comando create (Word) | SYSD-04, SYSD-05 | 2/2 |
| 3 | Documentar integração com agentes | SYSD-06, SYSD-07 | 2/2 |

---

### Phase 1: CLI-style GSD

**Goal:** Transformar sysdoc.py em sistema estilo GSD com /sysdoc commands.

**Mode:** standard

**Success Criteria:**
1. CLI responde a /sysdoc no contexto de agentes
2. Estrutura de projeto padronizada para invocation
3. Help contextual para cada comando

**Requirements:**
- [ ] **SYSD-01**: Refatorar argparse para aceitar /sysdoc prefix (mant compat)
- [ ] **SYSD-02**: Adicionar estrutura de projeto .sysdoc/config.yaml
- [ ] **SYSD-03**: Documentar formato de invocation em AGENTS.md

---

### Phase 2: Comando Create (Word/PDF)

**Goal:** Implementar /sysdoc create para gerar documentos conforme modelo.

**Mode:** standard

**Success Criteria:**
1. Gera arquivo .docx a partir de template
2. Preenche campos de dados_consolidados.json
3. Funciona offline/sem LLM

**Requirements:**
- [ ] **SYSD-04**: Criar gerador de Word (python-docx) baseado em template
- [ ] **SYSD-05**: Adicionar comando create ao CLI

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

*Phases: 3 | Requirements: 7*
*Generated: 2026-05-07*