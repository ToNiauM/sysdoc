---
phase: 05-motor-analise-checklist
plan: 02
subsystem: infra
tags: [python, argparse, pathlib, regex, pytest]

# Dependency graph
requires: []
provides:
  - "proximo_nome_artefato(destino, projeto, tipo, data, extensao) in sysdoc.py"
  - "proximo_nome_artefato replicated in templates/render_analise.py (subprocess-isolated)"
  - "xx_nome_tipo_data.extensao naming applied to publish (JSON), render (HTML), create (DOCX)"
  - "status/deploy/compare glob compatibility across legacy and new artifact names"
affects: [05-11-relatorio-execucao, 05-12-create-dvi]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-(projeto,tipo) monotonic counter parsed from the two-digit filename prefix, never reused, never overwrites"
    - "Naming logic duplicated (not imported) between sysdoc.py and templates/render_analise.py because the renderer runs as an isolated subprocess"

key-files:
  created:
    - tests/test_nomes_artefatos.py
  modified:
    - sysdoc.py
    - templates/render_analise.py
    - tests/test_cli.py
    - CHANGELOG.md

key-decisions:
  - "Removed orphaned resolve_next_json_archive, resolve_next_output, resolve_next_docx_output, resolve_next_filename once proximo_nome_artefato had no remaining alternative callers"
  - "publish() no longer deduplicates identical JSON content by reusing an existing archive path — every publish call always creates a new numbered file (D-08: contador nunca reutilizado)"
  - "modelo_ia removed from all generated filenames; it remains only in JSON metadata"

requirements-completed: [RF10, RNF5]

# Metrics
duration: ~35min
completed: 2026-08-26
---

# Phase 5 Plan 02: Artifact Naming Pattern Summary

**Implemented `xx_nome_tipo_data.extensao` artifact naming (D-08/D-09) across `publish`, `render`, and `create`, with `status`/`deploy`/`compare` reading both legacy and new filenames.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-08-26T14:19:55Z (first task commit)
- **Completed:** 2026-08-26T14:23:45Z
- **Tasks:** 3
- **Files modified:** 4 (sysdoc.py, templates/render_analise.py, tests/test_cli.py, CHANGELOG.md) + 1 created (tests/test_nomes_artefatos.py)

## Accomplishments

- `proximo_nome_artefato()` implemented in `sysdoc.py` and replicated (not imported) in `templates/render_analise.py`, since the renderer executes as an isolated subprocess.
- `publish()`, `create()` (DOCX) and the HTML renderer all emit `01_<slug-do-projeto>_<tipo>_<data>.<ext>`, incrementing to `02_`, `03_`... on every regeneration, per (projeto, tipo) pair, ignoring the date and immune to legacy filenames.
- `modelo_ia` no longer appears in any generated filename; it stays exclusively inside the JSON payload/metadata.
- `status()`, `deploy()`, and `compare()` glob both the legacy patterns (`analise_*.html`, `dados_consolidados_*.json`, `tr_*.docx`) and the new patterns (`*_analise_*.html`, `*_dados_*.json`) without double-counting.
- 17 new tests added covering the counter, slugging, renderer project-name derivation, and glob compatibility; full suite (84 tests) green.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implementar proximo_nome_artefato em sysdoc.py e aplicar em publish/create** - `3ef65c7` (feat)
2. **Task 2: Aplicar o padrão no renderer HTML** - `ce44179` (feat)
3. **Task 3: Suíte de testes do padrão de nomes** - `3f3d4b0` (test)

**Additional commit (deviation, Rule 2):** `5f0fc06` (docs) - CHANGELOG entry required by D-09 ("permitido, com registro no CHANGELOG").

_Note: no plan-metadata final commit was made per worktree-mode instructions — the orchestrator handles STATE.md/ROADMAP.md centrally after merge._

## Files Created/Modified

- `sysdoc.py` - Added `proximo_nome_artefato()`; rewired `publish()` and `create()` to use it; removed orphaned `resolve_next_json_archive`, `resolve_next_output`, `resolve_next_docx_output`; updated `status()`/`deploy()`/`compare()` globs for dual-pattern compatibility.
- `templates/render_analise.py` - Replaced `resolve_next_filename()` with a locally-duplicated `proximo_nome_artefato()`; `main()` now derives `projeto` from the parent dir when `projeto_dir` ends in `output/`, else from the dir itself.
- `tests/test_cli.py` - Updated 5 `create()` DOCX filename assertions from the old `tr_<modelo>_<data>.docx` pattern to the new `01_<slug-projeto>_tr_<data>.docx` pattern (required consequence of Task 1's interface change; all 40 tests in this file still pass).
- `tests/test_nomes_artefatos.py` (new) - `TestContador`, `TestSlugProjeto`, `TestRendererNome`, `TestCompatibilidadeGlobs` (17 tests, no network/SSH dependency, `subprocess.run` monkeypatched for deploy tests).
- `CHANGELOG.md` - Documented the naming-pattern change under `[Não publicado]`.

## Decisions Made

- **Counter matching is per (projeto, tipo), ignores the date component.** The regex `^(\d{2})_{slug(projeto)}_{slug(tipo)}_` only inspects the leading two-digit prefix and the projeto/tipo slugs; the trailing date/extension are irrelevant to the count, exactly as specified in `<behavior>`.
- **No content-based deduplication in `publish()` anymore.** The old `resolve_next_json_archive` returned an existing path if its content matched the new payload (avoiding a duplicate on identical re-publish). This is superseded by D-08's explicit "contador monotônico; nenhuma escrita reaproveita nome existente" — every `publish()` call now always creates a new numbered archive, even for byte-identical content. This is an intentional behavior change mandated by the phase context, not a regression.
- **`proximo_nome_artefato` duplicated, not imported, between `sysdoc.py` and `templates/render_analise.py`.** The renderer's module docstring and `<interfaces>` context explicitly state it runs as a subprocess and does not import `sysdoc.py`; duplicating ~12 lines of logic was preferred over introducing a shared import that would break that isolation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug/consequence of interface change] Updated 5 stale `create()` filename assertions in `tests/test_cli.py`**
- **Found during:** Task 1 verification (`pytest tests/test_nomes_artefatos.py tests/test_cli.py`)
- **Issue:** `create()`'s DOCX output naming changed from `tr_<modelo_ia>_<data>.docx` to `proximo_nome_artefato(...)` output (`01_<slug-projeto>_tr_<data>.docx`), which is exactly what Task 1 mandated. Five existing tests (`test_create_fills_docx_placeholders`, `test_create_tr_applies_etp_revisions`, `test_create_tr_reports_pending_substitution`, `test_create_tr_ignores_omission_markers`, `test_create_selects_compras_template`) still asserted the old literal filename `tr_gpt-5_2026-05-12.docx` and would fail after the interface change.
- **Fix:** Recomputed the expected filename per test using the actual project directory name's slug (e.g. `ProjetoCreate` → `projetocreate`) and updated each assertion to `01_<slug>_tr_2026-05-12.docx`.
- **Files modified:** `tests/test_cli.py`
- **Verification:** `pytest tests/test_cli.py -q` → 40 passed; full suite `pytest tests/ -q` → 84 passed.
- **Committed in:** `3ef65c7` (part of Task 1 commit)

**2. [Rule 2 - Missing documentation required by decision D-09] Added CHANGELOG entry**
- **Found during:** Post-Task-3 review of `<canonical_refs>`/decisions in `05-CONTEXT.md`
- **Issue:** D-09 explicitly states the naming-pattern evolution of `render_analise.py`/publish/create "implica evolução... permitido, com registro no CHANGELOG" — this plan's task list did not include a CHANGELOG task, but the decision makes it a requirement, not optional polish.
- **Fix:** Added a bullet under `[Não publicado]` → `### Alterado` in `CHANGELOG.md` describing the naming pattern, the counter semantics, `modelo_ia` removal from filenames, and the glob-compatibility guarantee.
- **Files modified:** `CHANGELOG.md`
- **Verification:** Visual review; no test coverage applicable to a docs file.
- **Committed in:** `5f0fc06` (separate docs commit, not part of any task's file set)

---

**Total deviations:** 2 auto-fixed (1 Rule 1, 1 Rule 2)
**Impact on plan:** Both were necessary consequences of the explicitly-planned interface change (Task 1) and an explicitly-cited context decision (D-09). No scope creep — no new features, no architectural changes.

## Issues Encountered

- No system-wide `pytest`/`pyyaml` install available in this environment (`pip install` blocked by PEP 668 externally-managed-environment). Created an isolated venv under the scratchpad directory (`/tmp/.../scratchpad/.venv`) to run the test suite; this venv is not part of the repository and was not committed. No production code or dependency declarations were changed — `pyproject.toml`'s existing `pytest>=7.0`/`pyyaml>=6.0` dev/runtime dependencies were installed as-is into the throwaway venv, nothing new was added.
- Worktree branch `worktree-agent-a461d34bd8ecb591f` was found checked out at a stale point (unrelated Phase 2 continuation commits, diverged from the expected base). Per the mandatory `<worktree_branch_check>` setup step, `git reset --hard ef1e5c83...` was run to correct the base before any task work began.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `proximo_nome_artefato` is available in both `sysdoc.py` (importable) and duplicated in `templates/render_analise.py` (subprocess-isolated) for reuse by later plans in this phase (05-11 relatório de execução, 05-12 `sysdoc create dvi`) that need `tipo=relatorio` / `tipo=dvi` artifact names.
- No blockers. Full test suite (84 tests) green; immutable files (`templates/analise_template.html`, `templates/validate_sysdoc.py`) untouched (`git diff --stat` empty for both).

---
*Phase: 05-motor-analise-checklist*
*Completed: 2026-08-26*
