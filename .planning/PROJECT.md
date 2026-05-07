# SysDoc - Sistema de Análise de Documentação de Licitação

## What This Is

CLI offline para análise comparativa de documentos de licitação (ETP e TR) contra modelos de referência. Gera relatórios HTML determinísticos. Funciona como sistema invocável via slash commands em agentes de IA (OpenCode, Claude Code, Codex, Antigravity).

## Core Value

Análise técnica e jurídica de documentos de licitação via CLI determinística + harness LLM para análises complexas, outputting HTML de para e documentos Word gerados.

## Requirements

### Validated

- ✓ Extração de PDF/DOCX para texto (sysdoc.py:extract_pdf, extract_docx)
- ✓ Validação de JSON (templates/validate_sysdoc.py)
- ✓ Renderização HTML (templates/render_analise.py)
- ✓ CLI completa com comandos: status, init, prepare, analyze, validate, render, publish, deploy

### Active

- [ ] Sistema de comandos estilo GSD (/sysdoc [comando])
- [ ] Comando create para gerar documentos Word/PDF
- [ ] Documentação para integração com agentes de IA
- [ ] Saída Word além de HTML
- [ ] Estrutura de projeto padronizada para invoked-by-agent

### Out of Scope

- Interface GUI — CLI only
- Análise em tempo real com múltiplas LLMs — uma por vez
- Armazenamento em cloud — local-only

## Context

**Código existente:**
- `sysdoc.py` (~700 linhas) — CLI principal (entry point único)
- `templates/validate_sysdoc.py` (425 linhas) — Validador
- `templates/render_analise.py` (340 linhas) — Renderizador HTML
- `skills/sysdoc/SKILL.md` — Operações canônicas
- `AGENTS.md` — Instruções genéricas para harnesses de IA

**Stack atual:** Python 3.12+, pypdf, python-docx, jinja2, pytest

## Constraints

- **Offline/determinístico**: Scripts Python geram máximo de output independente de IA
- **Agent-invocável**: CLI deve funcionar via /sysdoc em qualquer harness
- **Saída múltipla**: HTML e Word

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| CLI only, sem GUI | Agentes de IA não usam GUI | — Pending |
| Output HTML + Word | Word é formato padrão para documentos oficiais | — Pending |
| Python puro para prepare/render | Determinístico, zero LLM needed | — Pending |
| LLM só no analyze | Harness do agente faz análise | — Pending |

---

*Last updated: 2026-05-07 after project initialization*