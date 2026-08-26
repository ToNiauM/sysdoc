---
phase: 05-motor-analise-checklist
plan: 03
subsystem: validation
tags: [json-schema, pytest, retrocompatibilidade, rastreabilidade]

# Dependency graph
requires:
  - phase: 02-create-execution
    provides: "prepare grava textos extraídos em .sysdoc/cache/textos/documentos/"
provides:
  - "Contrato de dados schema_version 1.1 (aditivo): origem_verificacao, checklist_id, schema_version, checklist_hash"
  - "Rastreabilidade do campo `de` restaurada para o layout de cache atual"
  - "35 testes em tests/test_validate.py cobrindo campos novos e retrocompatibilidade"
affects: [05-motor-analise-checklist (plano do motor que emite os campos novos, ex. 05-11)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Campos novos de contrato entram só como opcionais em schema + validador, nunca em REQUIRED_*, para preservar retrocompatibilidade (RNF5)"
    - "load_source_texts prioriza .sysdoc/cache/textos/documentos/<DOC>.txt, com fallback para os dois caminhos legados"

key-files:
  created: []
  modified:
    - templates/schema_sysdoc.json
    - templates/validate_sysdoc.py
    - tests/test_validate.py

key-decisions:
  - "origem_verificacao e checklist_id validados apenas quando presentes, reaproveitando o laço de enums existente (não criou caminho de validação paralelo)"
  - "checklist_hash validado por regex 64-hex direto na função nova validate_audit_metadata, chamada do fluxo principal de validate()"

patterns-established:
  - "Testes de retrocompatibilidade sempre pareiam um caso 'campo presente e válido', um 'campo presente e inválido' e um 'campo ausente continua válido'"

requirements-completed: [RNF5, RF5, RF9]

# Metrics
duration: ~10min
completed: 2026-08-26
---

# Phase 5 Plan 3: Evolução retrocompatível do contrato de dados (schema_version 1.1) Summary

**Schema e validador aceitam origem_verificacao/checklist_id por item e schema_version/checklist_hash na raiz, e a rastreabilidade do campo `de` volta a funcionar contra `.sysdoc/cache/textos/documentos/`, tudo coberto por 8 testes novos sem quebrar nenhum dos 27 testes existentes.**

## Performance

- **Duration:** ~10 min (incluindo setup de venv de teste no ambiente)
- **Tasks:** 3/3 completed
- **Files modified:** 3

## Accomplishments
- Contrato de dados evoluído de forma aditiva para `schema_version` 1.1, sem alterar nenhum campo `required` existente
- Bug crítico de rastreabilidade corrigido: `load_source_texts` estava procurando textos extraídos apenas no caminho legado `.sysdoc/cache/textos/<DOC>.txt`, mas `prepare` grava desde a Phase 2 em `.sysdoc/cache/textos/documentos/<DOC>.txt` — a checagem de `de` fabricado estava silenciosamente inoperante em todo projeto preparado pela versão atual
- 8 testes novos (`TestCamposMotor`, `TestMetadadosAuditoria`, extensão de `TestTraceability`) garantindo tanto os casos válidos/inválidos dos campos novos quanto a retrocompatibilidade com JSON legado

## Task Commits

Each task was committed atomically:

1. **Task 1: Campos novos no schema e no validador** - `c94f3a7` (feat)
2. **Task 2: Corrigir a origem dos textos na verificação de rastreabilidade** - `29131fc` (fix)
3. **Task 3: Regressão de retrocompatibilidade em tests/test_validate.py** - `cb4328f` (test)

_Note: plan tasks were not run as strict TDD RED→GREEN because Task 3 (test authorship) was scoped as its own task per the plan; Tasks 1–2 were verified against the existing 27-test suite before commit, and Task 3 added the dedicated regression coverage._

## Files Created/Modified
- `templates/schema_sysdoc.json` - adds optional `origem_verificacao`/`checklist_id` to `$defs.item.properties`, optional `schema_version`/`checklist_hash` to root `properties`; nothing added to any `required` array
- `templates/validate_sysdoc.py` - adds `origem_verificacao` to `ENUMS`, validates `checklist_id` pattern and `validate_audit_metadata` (schema_version/checklist_hash) when present; fixes `load_source_texts` to check `.sysdoc/cache/textos/documentos/<DOC>.txt` first, falling back to the two legacy paths; docstring now states contract is `schema_version 1.1`
- `tests/test_validate.py` - `TestCamposMotor` (4 tests), `TestMetadadosAuditoria` (3 tests), and one added case in `TestTraceability` for the `documentos/` cache path

## Decisions Made
- Reused the existing generic enum-validation loop for `origem_verificacao` instead of writing a separate branch, keeping the diff minimal and message format consistent (`itens[N]: ...`)
- Added a dedicated `validate_audit_metadata` function for root-level `schema_version`/`checklist_hash` rather than inlining in `validate()`, mirroring the existing pattern of small focused validator functions (`validate_modelo_ia`, `validate_document_paths`, etc.)

## Deviations from Plan

None - plan executed exactly as written. All three tasks matched their `<action>` and `<acceptance_criteria>` blocks without needing Rule 1-4 auto-fixes.

## Issues Encountered
- The sandboxed execution environment had no `python`/`pytest` available system-wide (`externally-managed-environment` on `pip install`). Created a throwaway venv at `/tmp/claude-1003/.../scratchpad/venv` with `pytest`, `pyyaml`, `pypdf` to run verification — this venv is outside the repo and was not committed. Any CI/dev environment for this repo should have its own venv per `pyproject.toml`; this is an environment note, not a plan deviation.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- The data contract now supports the audit fields the analysis engine (motor) needs to emit (`origem_verificacao`, `checklist_id`, `checklist_hash`, `schema_version`), unblocking downstream plans (e.g. 05-11) that generate this output
- Traceability validation (`de` field) is confirmed working against the current `prepare` cache layout, closing a silent gap that existed since Phase 2
- No blockers identified for subsequent Phase 5 plans

## Self-Check: PASSED

- FOUND: templates/schema_sysdoc.json
- FOUND: templates/validate_sysdoc.py
- FOUND: tests/test_validate.py
- FOUND: .planning/phases/05-motor-analise-checklist/05-03-SUMMARY.md
- FOUND commit: c94f3a7 (Task 1)
- FOUND commit: 29131fc (Task 2)
- FOUND commit: cb4328f (Task 3)
- FOUND commit: a848ba4 (SUMMARY.md)

---
*Phase: 05-motor-analise-checklist*
*Completed: 2026-08-26*
