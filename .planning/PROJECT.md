# SysDoc - Sistema de Análise de Documentação de Licitação

## What This Is

CLI offline para preparação, análise assistida por agente e geração determinística de documentos. O caso comum continua sendo ETP/TR, mas a estrutura de projeto é genérica: documentos a analisar ficam em `documentos/`, referências e templates ficam em `referencias/`, e artefatos publicados ficam em `output/`.

## Core Value

Análise técnica e jurídica de documentos de licitação via CLI determinística + harness de IA externo, com saídas rastreáveis em JSON, HTML e DOCX.

## Requirements

### Validated

- ✓ Extração de PDF/DOCX/TXT/MD para texto.
- ✓ Estrutura `.sysdoc/config.yaml` por projeto.
- ✓ Estrutura genérica `documentos/`, `referencias/`, `output/`.
- ✓ Validação de JSON consolidado.
- ✓ Renderização HTML determinística.
- ✓ CLI completa com comandos: status, init, config, prepare, analyze, validate, render, publish, deploy, compare, guia.
- ✓ `sysdoc create` gera DOCX determinístico a partir de JSON + template.
- ✓ `tipo=tr` aplica revisão ETP com substituição exata `de`→`para` e registra pendências.

### Active

- [ ] Documentação e validação de integração com agentes de IA.

### Out of Scope

- Interface GUI — CLI only.
- Análise em tempo real com múltiplas LLMs — uma por vez.
- Armazenamento em cloud — local-only.
- Geração PDF direta no `create` — Word pode exportar PDF por enquanto.

## Current State

Phase 2 concluída em 2026-05-12. `sysdoc create` está implementado e verificado com 67 testes passando.

## Context

**Código existente:**

- `sysdoc.py` — CLI principal.
- `templates/validate_sysdoc.py` — validador determinístico.
- `templates/render_analise.py` — renderizador HTML determinístico.
- `skills/sysdoc/SKILL.md` — fluxo operacional canônico.
- `AGENTS.md` — instruções genéricas para harnesses de IA.

**Stack atual:** Python 3.12+, pypdf, pyyaml, pytest.

## Constraints

- **Offline/determinístico**: scripts Python geram output sem chamada a LLM.
- **Agent-invocável**: CLI deve funcionar via `/sysdoc` em qualquer harness.
- **Saída múltipla**: JSON, HTML e Word.
- **Templates de análise imutáveis**: `templates/analise_template.html`, `templates/render_analise.py` e `templates/validate_sysdoc.py` não são alterados durante análises.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| CLI only, sem GUI | Agentes de IA não usam GUI | Accepted |
| Output HTML + Word | Word é formato operacional para documentos oficiais | Accepted |
| Python puro para prepare/render/create | Determinístico, zero LLM needed | Accepted |
| LLM só no analyze | Harness externo faz análise; CLI prepara e renderiza | Accepted |
| Templates DOCX em `referencias/` | Referências incluem modelos oficiais e material de apoio por projeto | Accepted |

---

*Last updated: 2026-05-12 after Phase 2 completion*
