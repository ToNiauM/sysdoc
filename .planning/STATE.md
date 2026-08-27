---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 06
status: ready_to_execute
stopped_at: "Phase 6 planejada — 7 planos em 4 waves (rodada 1: Despacho de Verificação Inicial)"
last_updated: "2026-08-27T03:45:59.637Z"
progress:
  total_phases: 7
  completed_phases: 2
  total_plans: 24
  completed_plans: 17
  percent: 29
---

# STATE — SysDoc

**Project:** SysDoc - Sistema de Análise de Documentação de Licitação
**Current Phase:** 06
**Mode:** standard

## Project Reference

See: .planning/PROJECT.md

**Core value:** CLI offline para análise de documentos de licitação via agentes de IA.

## Progress

| Phase | Status | Plans | Progress |
|-------|--------|-------|----------|
| 1 | complete | 1/1 | 100% |
| 2 | complete | 1/1 | 100% |
| 3 | pending | 0/1 | 0% |
| 4 | pending | 0/1 | 0% |
| 5 | pending | 0/0 | 0% |
| 6 | in_progress | 1/7 | 14% |

## Recent Changes

- 2026-05-07: Projeto inicializado no GSD.
- 2026-05-07: Codebase mapeado.
- 2026-05-07: Phase 1 concluída — `sysdoc analyze`, `.sysdoc/config.yaml`, AGENTS.md, wrappers Claude Code/OpenCode e testes CLI.
- 2026-05-08: Phase 2 planejada — `02-RESEARCH.md`, `02-PATTERNS.md` e `02-01-PLAN.md`.
- 2026-05-12: Phase 2 concluída — `sysdoc create` gera DOCX determinístico a partir de JSON + templates em `referencias/`, com revisão ETP para `tipo=tr`; 67 testes passando.
- 2026-05-12: Phase adicionada — Templates TR a partir dos 4 modelos Lei 14.133 em `Referencias/`, com placeholders SysDoc anotados.
- 2026-08-26: Merge de branches — "Templates TR (Lei 14.133)" renumerada de Phase 5 para Phase 6; Phase 5 permanece "Motor de análise por checklist" (concluída, release 1.5.0).
- 2026-08-27: Phase 6 planejada (rodada 1: Despacho de Verificação Inicial) — 7 planos em 4 waves, cobrindo SYSD-16/17/18 e D-01 a D-14. Canal raw-XML separado (`render_docx_template(..., raw_xml=)`) adotado em vez de allowlist sobre `values`, eliminando por construção a injeção via chave homônima no `dados_consolidados.json`.
- 2026-08-27: Plano 06-01 concluído — gerador determinístico `templates/build_despacho_templates.py` cria `templates/dvi/despacho_geral.docx` e `templates/dvi/despacho_tic.docx`, moldura fiel a `processo-teste/referencias/dvi.md` com seis estilos nomeados e placeholder raw único `{{corpo_apontamentos_xml}}`; 11 testes novos, suíte completa (480) verde.

## Recent Decisions

- Templates de geração DOCX ficam em `referencias/`, não em um template fixo do repositório.
- `sysdoc create` permanece offline e determinístico, usando substituição ZIP/XML de placeholders em DOCX.
- `tipo=tr` é o padrão quando omitido; `--tipo` existe para scripts.
- Para TR, o ETP preparado é lido de `.sysdoc/cache/textos/documentos/ETP.txt`, com fallback legado para `.sysdoc/cache/textos/ETP.txt`.
- `templates/dvi/` é a pasta própria para templates institucionais do despacho, um DOCX por variante de verificação (`despacho_geral.docx`, `despacho_tic.docx`), no molde do gerador determinístico já usado por `templates/build_dvi_base.py`.

## Accumulated Context

### Roadmap Evolution

- Phase 5 added: Motor de análise por checklist com agentes plugáveis (PRD completo em `.planning/phases/05-motor-analise-checklist/PRD.md`)
- Phase 7 added (2026-08-26): Interface web para pregoeiros — fluxo visual de upload → extração → análise → output HTML/DOCX, abstraindo a CLI e o motor DVI

## Pending Todos

- Revisar a pasta não rastreada `Referencias/` antes de qualquer publicação ampla; ela parece conter modelos reais do usuário.

## Blockers/Concerns

- Nenhum bloqueio ativo para continuar o roadmap.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260826-o2d | Melhorias DX motor DVI: autocorreção de acentuação pós-validação (P2), progresso por item no run (P4), template DVI base semeado pelo init (P6) | 2026-08-26 | b376b5f | [260826-o2d-melhorias-dx-motor-dvi-autocorre-o-p-s-v](./quick/260826-o2d-melhorias-dx-motor-dvi-autocorre-o-p-s-v/) |
| 260826-p65 | Motor DVI: fatiador determinístico de peças no prepare (P1), re-ancoragem determinística do campo `de` antes de degradar (P3), preços de modelos configuráveis por alvo (P5) | 2026-08-26 | 8af987b | [260826-p65-motor-dvi-fatiador-deterministico-de-pec](./quick/260826-p65-motor-dvi-fatiador-deterministico-de-pec/) |

## Session Continuity

Last session: 2026-08-27T03:45:59.637Z
Stopped at: Completed 06-01-PLAN.md (templates DOCX do Despacho de Verificação Inicial)
Resume file: .planning/phases/06-templates-tr-a-partir-dos-modelos-lei-14-133/06-02-PLAN.md

## Current Focus

Phase 3: Integração Agentes IA. Próximo passo recomendado: `$gsd-discuss-phase 3`.

---

*Last updated: 2026-08-26 — Completed quick task 260826-p65: fatiador de peças, re-ancoragem e preços (P1+P3+P5)*
