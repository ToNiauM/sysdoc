---
phase: 02-comando-create-word-pdf
plan: 02-01
subsystem: cli
tags: [docx, templates, json, etp, cli, tests]

requires:
  - phase: 01-cli-style-gsd
    provides: agent-invocable SysDoc project structure and deterministic CLI commands
provides:
  - deterministic DOCX generation through `sysdoc create`
  - TR-specific ETP revision flow with exact `de` to `para` substitution
  - reference-template selection from `referencias/`
  - CLI and regression coverage for DOCX creation
affects: [phase-3, sysdoc-cli, document-generation, agent-workflow]

tech-stack:
  added: []
  patterns:
    - ZIP/XML DOCX placeholder replacement
    - flattened JSON placeholder mapping
    - exact conservative ETP substitution with pending substitution reporting

key-files:
  created: []
  modified:
    - sysdoc.py
    - tests/test_cli.py
    - README.md
    - AGENTS.md
    - skills/sysdoc/SKILL.md
    - CHANGELOG.md

key-decisions:
  - "Use templates from project `referencias/` instead of a fixed repository template."
  - "Keep DOCX generation deterministic with ZIP/XML placeholder replacement instead of adding `python-docx`."
  - "For `tipo=tr`, default to TR behavior, apply ETP revisions, and write `tr_[modelo]_[data].docx` in the project root."

patterns-established:
  - "Create command accepts generic DOCX templates while adding TR-specific behavior for procurement workflows."
  - "Unapplied ETP substitutions are surfaced inside the generated DOCX and on stdout."
  - "CLI docs and agent skills describe `documentos/`, `referencias/`, `output/`, and deterministic create behavior consistently."

requirements-completed:
  - SYSD-04
  - SYSD-05

duration: 1h 5m
completed: 2026-05-12
---

# Phase 2 Plan 02-01: Implementar `sysdoc create` para gerar TR `.docx` Summary

**Deterministic DOCX creation from consolidated JSON, reference Word templates, and ETP clause revisions.**

## Performance

- **Duration:** 1h 5m resumed execution, after prior partial implementation
- **Started:** 2026-05-12T16:16:00-03:00
- **Completed:** 2026-05-12T17:21:47-03:00
- **Tasks:** 5/5 completed
- **Files modified:** 6 product/doc/test files plus GSD tracking artifacts

## Accomplishments

- Added and verified `sysdoc create` as a deterministic DOCX generator using `dados_consolidados.json` and Word templates from `referencias/`.
- Implemented TR-specific ETP revision behavior: exact first-match replacement of `de` by `para`, omission-marker filtering, pending-substitution reporting, category-based template selection, and non-overwriting DOCX output names.
- Added CLI coverage for help, default `tipo=tr`, `--tipo`, placeholder replacement, auto-prepare, pending substitutions, omission handling, missing JSON, and compras template selection.
- Updated README, AGENTS, and canonical SysDoc skill documentation to describe the generic document workflow and `create` behavior.

## Task Commits

Phase 2 was resumed from a partially implemented state. The final implementation was consolidated and committed after full verification:

1. **Task 1: Generalized project structure and initial create support** - `ca4db6f` (`feat: generalize project document workflow`)
2. **Task 2: Config CLI refinement carried during Phase 2** - `7f3f828` (`refactor(cli): use --vps/--path instead of -vps/-path`)
3. **Task 3: Pause handoff for interrupted Phase 2 execution** - `d6d4eaf` (`wip: phase 2 paused at handoff`)
4. **Tasks 2-5 finalization: create helpers, tests, docs, and CLI defaults** - `b21b109` (`feat(02-01): finalize deterministic docx create`)
5. **Code-review fix: generalized ETP cache lookup and missing ETP failure** - `9d78c1e` (`fix(02-01): require prepared etp text for tr revisions`)

## Files Created/Modified

- `sysdoc.py` - Adds JSON loading, ETP cache preparation, exact ETP revision helpers, pending substitution text, DOCX placeholder rendering, template selection from `referencias/`, `create` dispatch, default `tipo=tr`, and `--tipo`.
- `tests/test_cli.py` - Adds create command tests for parser behavior, TR revision, pending substitutions, omission markers, auto-prepare, missing JSON, and category template selection.
- `README.md` - Documents `sysdoc create`, default TR behavior, reference templates, and output naming.
- `AGENTS.md` - Updates harness-level create macro semantics.
- `skills/sysdoc/SKILL.md` - Updates canonical operational flow for create with `referencias/`, `--json`, `--template`, and root DOCX output.
- `CHANGELOG.md` - Records the 1.4.0 create workflow and the `--tipo` refinement.

## Decisions Made

- **Reference templates over repository template:** The current project direction and AGENTS/SKILL instructions require templates in project `referencias/`, so Phase 2 follows that instead of introducing `templates/tr_template.docx`.
- **ZIP/XML replacement over `python-docx`:** The implemented generator fills placeholders directly inside DOCX XML. This keeps the CLI dependency footprint unchanged and preserves deterministic behavior for simple institutional templates.
- **TR default with generic extension path:** `sysdoc create` defaults to `tr` when no type is provided, but still accepts other type names for direct template filling where a matching template exists.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 4 - Architectural Scope] Reconciled template strategy with current project direction**
- **Found during:** Phase resume and Task 3/5 review.
- **Issue:** `02-01-PLAN.md` expected `python-docx` plus `templates/tr_template.docx`, but the active AGENTS/SKILL instructions had shifted to templates in `referencias/` and broader document generation.
- **Fix:** Preserved the implemented `referencias/` template strategy and documented it in README, AGENTS, SKILL, and this SUMMARY. Did not add unused `python-docx` or a fixed repository template.
- **Files modified:** `sysdoc.py`, `README.md`, `AGENTS.md`, `skills/sysdoc/SKILL.md`, `CHANGELOG.md`.
- **Verification:** `python -m pytest tests/ -v`; `python sysdoc.py create --help`; manual temporary project create check.
- **Committed in:** `b21b109`.

**2. [Rule 2 - Missing Critical] Added explicit default and flag coverage for `tipo`**
- **Found during:** Acceptance criteria review.
- **Issue:** The CLI accepted flexible positional arguments but defaulted to `documento`, while the phase plan and common workflow expect TR as the default.
- **Fix:** Changed parser dispatch so no type or project-only invocation defaults to `tr`; added `--tipo`; added tests.
- **Files modified:** `sysdoc.py`, `tests/test_cli.py`, `README.md`, `AGENTS.md`, `skills/sysdoc/SKILL.md`, `CHANGELOG.md`.
- **Verification:** `python -m pytest tests/test_cli.py -v`; `python -m pytest tests/ -v`.
- **Committed in:** `b21b109`.

**3. [Rule 3 - Execution Continuity] Converted a partially manual phase into formal GSD completion**
- **Found during:** Resume from `.planning/HANDOFF.json` and `.continue-here.md`.
- **Issue:** Implementation existed without `02-01-SUMMARY.md`, blocking downstream GSD workflows such as `$gsd-add-tests 2`.
- **Fix:** Reviewed changes, ran baseline and post-change verification, committed product changes, and created this SUMMARY.
- **Files modified:** `.planning/phases/02-comando-create-word-pdf/02-01-SUMMARY.md`, `.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`.
- **Verification:** Plan index now sees a matching summary; full test suite passes.
- **Committed in:** pending GSD tracking commit.

---

**Total deviations:** 3 handled (1 architectural reconciliation, 1 missing critical CLI behavior, 1 execution continuity fix).
**Impact on plan:** The phase goal and requirements are met, but the implementation intentionally follows the updated project architecture rather than the older fixed-template/python-docx plan details.

## Issues Encountered

- The first manual create check was invalid because PowerShell passed accented literals through stdin with replacement characters. The check was rerun with ASCII-safe Unicode escapes and passed.
- `Referencias/` remains untracked because it appears to contain real user reference DOCX material. It was deliberately not staged or committed.

## User Setup Required

None - no external service configuration required.

## Verification

- `python -m pytest tests/ -v` - 67 passed.
- `python -m pytest tests/test_cli.py -v` - 40 passed.
- `python sysdoc.py create --help` - exits 0 and shows `--tipo`.
- `python sysdoc.py --version` - prints `SysDoc 1.4.0`.
- Manual temporary project: `python sysdoc.py create <temp> tr` created `tr_gpt-5_2026-05-12.docx`; `word/document.xml` contained revised ETP text, contained no `{{` placeholders, and required no network or LLM call.
- Immutable templates untouched: `templates/analise_template.html`, `templates/render_analise.py`, and `templates/validate_sysdoc.py` are absent from `git diff --name-only`.
- Code review gate completed with no open findings after `9d78c1e`.

## Self-Check: PASSED

- `SYSD-04` covered by deterministic DOCX generation from project templates.
- `SYSD-05` covered by `sysdoc create` CLI command and parser dispatch.
- MVP TR flow generates `.docx`, revises ETP text conservatively, reports pending substitutions, and does not overwrite existing output.
- Documentation and tests reflect the implemented behavior.

## Next Phase Readiness

Phase 2 is ready for phase-level tracking completion and later `$gsd-add-tests 2`. Residual concern: the untracked `Referencias/` folder should be handled explicitly by the user before any broad repository publish.

---
*Phase: 02-comando-create-word-pdf*
*Completed: 2026-05-12*
