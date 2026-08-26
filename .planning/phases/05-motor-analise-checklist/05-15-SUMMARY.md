---
phase: 05-motor-analise-checklist
plan: 15
subsystem: docs
tags: [sysdoc-dvi, checklist, documentation, changelog, readme]

# Dependency graph
requires:
  - phase: 05-motor-analise-checklist (plans 05-01..05-14)
    provides: sysdoc_dvi package (run/relatorio/config), checklists/dvi.yaml, normas/vigencia.yaml, sysdoc create dvi, schema 1.1, artifact naming pattern
provides:
  - Canonical documentation (SKILL.md, AGENTS.md, CLAUDE.md, both wrappers) declaring checklists/dvi.yaml as the single source of DVI analysis items
  - CLAUDE.md corrected to remove non-existent sysdoc connect/models commands and describe the real ~/.sysdoc/config.json / sysdoc-dvi config mechanism
  - README.md section documenting the sysdoc-dvi motor end-to-end for human operators
  - CHANGELOG.md [1.5.0] release entry consolidating everything shipped across 05-01..05-14
affects: [05-16, future-phases-reading-SKILL.md-or-AGENTS.md]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Documentation-as-reference: SKILL.md declares checklists/dvi.yaml canonical without duplicating item IDs (mitigates T-05-51 drift risk)"

key-files:
  created:
    - .planning/phases/05-motor-analise-checklist/deferred-items.md
  modified:
    - skills/sysdoc/SKILL.md
    - AGENTS.md
    - CLAUDE.md
    - .claude/skills/sysdoc-analise/SKILL.md
    - .opencode/skills/sysdoc-analise/SKILL.md
    - README.md
    - CHANGELOG.md

key-decisions:
  - "CHANGELOG [Não publicado] section promoted directly to [1.5.0] — 2026-08-26 rather than added as a new section, since D-05 fixes the release label at 1.5.0 and no other unreleased work exists ahead of it."
  - "Task 3 (real-process verification, CA1/CA5/CA7/CA8) could not be executed honestly: this sandbox has no configured LLM provider keys (sysdoc-dvi config --listar confirms all four provider keys absent) and no real procurement project folders. Ran every check that is honestly possible offline instead of fabricating results, and returned a checkpoint for the human to complete with real processes and configured models."

requirements-completed: []

# Metrics
duration: ~35min
completed: 2026-08-26
---

# Phase 05 Plan 15: Documentation Alignment + DVI Motor Verification Checkpoint Summary

**Canonical docs (SKILL.md/AGENTS.md/CLAUDE.md/wrappers/README/CHANGELOG) now declare `checklists/dvi.yaml` as the single source of DVI items, drop the fictitious `sysdoc connect`/`sysdoc models` commands, and ship a consolidated CHANGELOG `[1.5.0]` entry; Task 3's real-process verification (CA1/CA5/CA7/CA8) is a pending human checkpoint because this environment has no configured model keys or real procurement folders.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-08-26
- **Tasks:** 2 of 3 executed and committed (Task 3 is a `checkpoint:human-verify` — reached, offline-verifiable portions run, awaiting human with real processes)
- **Files modified:** 7 (+ 1 new deferred-items.md)

## Accomplishments

- `skills/sysdoc/SKILL.md` gained an "Análise DVI por checklist" section declaring `checklists/dvi.yaml` as canonical, describing both RF8 coupling levels (artefato / código), and pointing to `sysdoc-dvi run` as the automated path — without duplicating any item ID (verified: `grep -c "DVI-GER-\|DVI-AMB-" skills/sysdoc/SKILL.md` == 0).
- `CLAUDE.md`'s stale "Environment & Configuration" section (claiming `sysdoc connect`/`sysdoc models` exist) and Core-files table were corrected to describe the real mechanism: `~/.sysdoc/config.json` (hand-edited or via `sysdoc-dvi config --economico/--forte`) plus the four provider env vars. `sysdoc connect`/`sysdoc models` no longer appear anywhere in CLAUDE.md.
- `AGENTS.md` and both harness wrappers (`.claude/skills/sysdoc-analise/SKILL.md`, `.opencode/skills/sysdoc-analise/SKILL.md`) now list `sysdoc-dvi run/relatorio/config` and reference the checklist as the source of analysis items.
- `README.md` gained a full "Motor de análise DVI (`sysdoc-dvi`)" section: config prerequisite, `sysdoc-dvi run [pasta] --tipo geral|tic`, a table of what each verification type (`presenca`/`julgamento`/`calculo`/`vigencia`/`mecanica`) does, checklist/vigência file locations, how to edit/disable an item with zero code changes, and the manual next step (`sysdoc create dvi`, `sysdoc deploy`), with the canonical naming example `01_processo-042_dvi_2026-08-26.docx`.
- `CHANGELOG.md`'s `[Não publicado]` section was promoted to `## [1.5.0] — 2026-08-26` and expanded with items that existed in code/tests but were not yet individually changelogged: the checklist motor itself, `normas/vigencia.yaml`, the deterministic `calculo`/`vigencia`/`mecanica` checks, the grounding check, dedicated synthesis, the resume checkpoint, the execution report, manifest piece anchors, and the schema 1.1 audit fields (`origem_verificacao`, `checklist_id`, `checklist_hash`, `schema_version`) — plus the pre-existing `de`-field traceability fix (commit `29131fc`, Task 05-03) which had not been changelogged.
- Full offline verification run: `364 passed` in the whole `tests/` suite (venv), plus a targeted re-run of `tests/test_dvi_run.py` (10/10, including the fake-agent end-to-end `TestRunCompleto`), `tests/test_dvi_create.py` (10/10), and `tests/test_nomes_artefatos.py` (17/17) — all green.
- Confirmed no API keys or secrets are present anywhere in the working tree (`grep` for `sk-ant-`, `sk-or-v1-`, `AIzaSy`, `sk-proj-` and generic `sk-<20+ chars>` patterns found only test fixtures and doc placeholders, e.g. `"sk-..."`, `sk-ant-x`).
- Logged the pre-existing `sysdoc.py` `VERSION = "1.4.0"` vs `pyproject.toml`'s `1.5.0` drift to `deferred-items.md` — out of this documentation-only plan's `files_modified` scope, flagged for a future code-touching plan.

## Task Commits

1. **Task 1: Fluxo canônico e wrappers apontando para o checklist** - `be0aa77` (docs)
2. **Task 2: README e CHANGELOG da 1.5.0** - `48d6676` (docs)
3. **Task 3: Verificação com processos reais (CA1, CA5, CA8)** - `checkpoint:human-verify`, gate=`blocking` — **not resumable by this agent**; see "Checkpoint: Task 3" below.

**Plan metadata:** this SUMMARY commit (see below) — `docs(05-15): create summary`

## Files Created/Modified

- `skills/sysdoc/SKILL.md` - new "Análise DVI por checklist" section (canonical YAML source, RF8 two levels, `sysdoc-dvi run` pointer)
- `AGENTS.md` - "Motor DVI (`sysdoc-dvi`)" subsection with the three subcommands and the "items live in YAML, not in prompts" rule
- `CLAUDE.md` - CLI commands list gains `sysdoc-dvi`; Core-files table corrected (removed `connect`/`models`, added `sysdoc_dvi/cli.py`, `checklists/dvi.yaml`, `normas/vigencia.yaml`); Environment & Configuration section rewritten around the real key mechanism; Key Rules gained checklist/vigencia/naming/versioning rules
- `.claude/skills/sysdoc-analise/SKILL.md` - trigger list + DVI checklist guidance added
- `.opencode/skills/sysdoc-analise/SKILL.md` - trigger list + DVI checklist guidance added
- `README.md` - new "Motor de análise DVI (`sysdoc-dvi`)" section + TOC entry
- `CHANGELOG.md` - `[Não publicado]` → `## [1.5.0] — 2026-08-26`, with Adicionado/Alterado/Corrigido expanded per D-08/D-09
- `.planning/phases/05-motor-analise-checklist/deferred-items.md` - new file logging the out-of-scope `sysdoc.py` VERSION drift

## Decisions Made

- Promoted `[Não publicado]` straight to `[1.5.0]` instead of appending a new unreleased section, per D-05 (single version label for this delivery).
- Did not touch `sysdoc.py`'s `VERSION` constant even though it disagrees with `pyproject.toml` — outside this plan's declared `files_modified`, and a code change, not documentation; logged to `deferred-items.md` instead of silently fixing (Rule 1 would normally apply, but the plan's scope boundary for a documentation-only plan takes precedence — this is arguably a borderline call, flagged for orchestrator visibility).
- For Task 3, chose an honest partial verification over a fabricated complete one, per explicit phase-state guidance: ran everything offline (full suite, targeted DVI/create/naming test reruns, `sysdoc-dvi --help`/`config --listar`, secret-leak grep, doc greps) and is returning the real-process steps as an open checkpoint rather than claiming CA1/CA5/CA7/CA8 are verified.

## Deviations from Plan

None — Tasks 1 and 2 executed as written; all their acceptance-criteria greps pass exactly as specified in the plan. Task 3 is inherently a `checkpoint:human-verify` in the plan itself (not a deviation), and this environment lacks the two preconditions the checkpoint's `<how-to-verify>` steps require (configured model keys, real procurement project folders in `documentos/`), so it cannot be completed autonomously.

## Checkpoint: Task 3 — Verificação com processos reais (CA1, CA5, CA8)

**What was honestly verified offline in this environment:**

- `python -m pytest tests/ -q` → **364 passed**, 0 failed, 0 errors (whole suite, isolated venv).
- Targeted reruns, verbose: `tests/test_dvi_run.py` (10/10, including `TestRunCompleto::test_run_completo_gera_json_html_e_relatorio`, the fake-agent end-to-end pipeline test), `tests/test_dvi_create.py` (10/10), `tests/test_nomes_artefatos.py` (17/17).
- `python3 -m sysdoc_dvi.cli --help`, `run --help`, `config --help` all resolve correctly, confirming the `run`/`relatorio`/`config` subcommands and their documented flags exist as described in the updated docs.
- `python3 -m sysdoc_dvi.cli config --listar` confirms this environment has **no** economic/strong model mapping and **no** provider API keys configured (`openrouter`, `openai`, `gemini`, `anthropic` all "ausente") — the precondition for CA1/CA5/CA8 is genuinely absent here, not skipped.
- Grep across the working tree for API-key-shaped strings (`sk-ant-`, `sk-or-v1-`, `AIzaSy`, `sk-proj-`, generic `sk-<20+ chars>`) found only test fixtures and doc placeholders — no real secret leaked into any generated artifact or doc (partial coverage of checkpoint step 7; full coverage requires the real-process run).
- `grep -rn "sysdoc-dvi" AGENTS.md skills/sysdoc/SKILL.md` returns occurrences, satisfying the plan's `<verification>` block.

**What remains for the human** (cannot be run in this sandbox — no LLM provider keys, no real procurement project folders):

1. Configure real models: `sysdoc-dvi config --economico <provedor/modelo> --forte <provedor/modelo>`.
2. Pick one real "geral" procurement process and one real "TIC" process, each with ETP/TR/MCP/Mapa de Riscos in `documentos/`.
3. Run `sysdoc-dvi run <pasta-geral> --tipo geral` and `sysdoc-dvi run <pasta-tic> --tipo tic`; confirm exit code 0 and `sysdoc validate` passes both JSONs without manual edits (**CA1**).
4. Open `output/*_relatorio_*.json` for both; record counts by status/type, grounding failures, tokens, cost, duration; note the economic model's baseline grounding-failure rate (**CA8**).
5. Run the same DVI analysis via a harness reading `checklists/dvi.yaml` directly on one of the two folders, then `sysdoc compare <pasta>`, confirming both runs appear side by side and are comparable (**CA5**).
6. Run `sysdoc create dvi <pasta>`, open the generated DOCX, confirm content and the `xx_nome_dvi_data.docx` naming (**CA7**).
7. Confirm no generated file or log contains an API key (full check, with real data this time).

**Resume signal (per plan):** respond "aprovado" with the observed grounding-failure rate, or describe any divergences found.

## Self-Check: PASSED

- `skills/sysdoc/SKILL.md` — FOUND (edited, verified via grep)
- `AGENTS.md` — FOUND (edited, verified via grep)
- `CLAUDE.md` — FOUND (edited, verified via grep)
- `.claude/skills/sysdoc-analise/SKILL.md` — FOUND (edited, verified via grep)
- `.opencode/skills/sysdoc-analise/SKILL.md` — FOUND (edited, verified via grep)
- `README.md` — FOUND (edited, verified via grep)
- `CHANGELOG.md` — FOUND (edited, verified via grep)
- `.planning/phases/05-motor-analise-checklist/deferred-items.md` — FOUND (new file)
- Commit `be0aa77` — FOUND in `git log --oneline`
- Commit `48d6676` — FOUND in `git log --oneline`
