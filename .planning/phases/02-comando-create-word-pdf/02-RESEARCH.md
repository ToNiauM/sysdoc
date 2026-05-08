# Phase 2 Research: Comando Create (Word/PDF)

**Phase:** 2 - Comando Create (Word/PDF)  
**Date:** 2026-05-08  
**Status:** Complete  
**Research mode:** Inline Codex execution, no subagents

## Objective

Research how to implement `sysdoc create` so Phase 2 can be planned with concrete implementation choices. The phase goal is to generate an offline, deterministic TR `.docx` from `dados_consolidados.json`, the extracted `ETP.txt`, and a Word template.

## Inputs Reviewed

- `skills/sysdoc/SKILL.md` - canonical SysDoc workflow and `/sysdoc create` placeholder.
- `AGENTS.md` - repository-level constraints, including tests before/after edits and immutable analysis templates.
- `.planning/phases/02-comando-create-word-pdf/02-CONTEXT.md` - user decisions and open planning decisions.
- `.planning/phases/02-comando-create-word-pdf/02-DISCUSSION-LOG.md` - MVP scope decisions.
- `.planning/REQUIREMENTS.md` - `SYSD-04` and `SYSD-05`.
- `.planning/ROADMAP.md` - Phase 2 goal and success criteria.
- `sysdoc.py` - CLI parser, path handling, cache preparation, JSON publishing, naming helpers.
- `tests/test_cli.py` and `tests/test_validate.py` - local testing patterns.
- `pyproject.toml` - current dependencies.
- `.planning/codebase/ARCHITECTURE.md` and `.planning/codebase/TESTING.md` - existing project patterns.

## Key Findings

### Existing code supports a narrow extension

`sysdoc.py` is a single-file deterministic CLI. The right integration points are:

- `ProjectPaths` for canonical project paths.
- `project_paths()` for path resolution.
- `prepare()` and `analyze()` patterns for cache preparation.
- `slug()`, `extract_date()` and `resolve_next_json_archive()` for output naming style.
- `build_parser()` for subcommands.
- `main()` for command dispatch.

There is no existing Word generation path. The closest existing pattern is deterministic rendering: `publish()` validates inputs, derives a versioned filename from `modelo_ia` and `data_análise`, writes output, and prints the resulting path.

### Engine choice

Three approaches were considered:

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| `docxtpl` | Strong placeholder/loop support; Jinja-like templates | Adds heavier dependency and template semantics not needed for MVP | Do not use for MVP |
| `python-docx` | Simple, maintained, adequate for headings/paragraphs/tables; easy tests by ZIP/XML inspection | Adds dependency; placeholder replacement across runs needs helper discipline | Use for MVP |
| DIY ZIP/XML | Zero dependency; mirrors `extract_docx()` style | Writing valid WordprocessingML is brittle and distracts from SysDoc value | Avoid |

Recommendation: use `python-docx>=1.1.2`. This aligns with the Phase 2 requirement text (`Gerador de Word (python-docx)`) and keeps implementation readable.

### Template strategy

The best MVP strategy is a fixed default template in `templates/tr_template.docx`.

Rationale:

- It matches the existing `templates/` convention.
- It keeps output deterministic and project-wide.
- It avoids introducing per-project template config before a concrete need exists.
- It can be expanded later to allow `[pasta]/.sysdoc/tr_template.docx` overrides.

The template should be minimal: title, header placeholders and a body anchor. The generator can load it with `python-docx`, replace simple paragraph placeholders, append the adjusted ETP body and append a pending substitutions section when needed.

Because this repository treats the HTML renderer/template as immutable during analyses, Phase 2 must not modify:

- `templates/analise_template.html`
- `templates/render_analise.py`
- `templates/validate_sysdoc.py`

Adding `templates/tr_template.docx` is acceptable because it is a new Word generation template, not part of an active analysis rendering pass.

### Data mapping

Required input:

- `[pasta]/dados_consolidados.json`
- `[pasta]/.sysdoc/cache/textos/ETP.txt`
- `templates/tr_template.docx`

Recommended header mapping:

| JSON path | DOCX placeholder |
|---|---|
| `projeto.objeto` | `{{objeto}}` |
| `projeto.processo` | `{{processo}}` |
| `projeto.valor_estimado` | `{{valor_estimado}}` |
| `projeto.órgão` | `{{orgao}}` |
| `data_análise` | `{{data_analise}}` |
| `modelo_ia` | `{{modelo_ia}}` |

Recommended body logic:

1. Start with literal `ETP.txt`.
2. Filter `dados_consolidados.itens` where:
   - `documento == "ETP"`
   - `classificação in {"ajuste_necessário", "risco"}`
   - `de` is not an omission marker.
3. For each filtered item, replace the first exact occurrence of `de` in `ETP.txt` with `para`.
4. If exact replacement fails, preserve the ETP text unchanged and add that item to a final "Substituições pendentes" section.
5. Ignore `TR` items in the MVP because the chosen source body is the ETP literal.

This is intentionally conservative. It avoids fuzzy replacement changing the wrong clause in a procurement document.

### CLI shape

Recommended command:

```text
sysdoc create [pasta] [tipo]
```

With:

- `tipo` optional positional argument, default `tr`.
- `--tipo tr` alias for scripts that prefer flags.
- only `tr` accepted in Phase 2.

This matches the macro already documented in `skills/sysdoc/SKILL.md`: `/sysdoc create [pasta] [tipo]`.

### Cache behavior

If `ETP.txt` is missing, `create` should run `prepare(project)` automatically, following the `analyze()` pattern. If mandatory inputs are missing, `prepare()` already fails clearly through `ensure_project_inputs()`.

### Output naming

Recommended output:

```text
tr_[modelo_ia]_[data].docx
tr_[modelo_ia]_[data]_2.docx
```

Use `slug(modelo_ia)` and `extract_date(data_análise)` to mirror `publish()`.

Add a helper equivalent to `resolve_next_json_archive()` for `.docx`, but without content equality deduplication because binary `.docx` output may contain metadata differences. Auto-increment when a file already exists.

### Testing strategy

Use `pytest` and `tmp_path` like existing tests. Avoid requiring Word/LibreOffice.

Recommended tests:

- `create --help` exposes `create`, `[tipo]` and `--tipo`.
- `sysdoc.create()` runs `prepare()` automatically when `ETP.txt` cache is missing.
- successful create writes `tr_gpt-5_2026-05-08.docx`.
- generated `.docx` can be opened as ZIP and `word/document.xml` contains:
  - JSON header values;
  - revised ETP clause from `para`;
  - no unreplaced `{{...}}` placeholders.
- unresolved substitutions produce a "Substituições pendentes" section with the item id.
- missing `dados_consolidados.json` fails clearly.
- unsupported `tipo` fails through argparse or `create()`.

## Recommended Implementation Summary

Implement Phase 2 as one focused plan:

1. Add `python-docx>=1.1.2`.
2. Add a fixed `templates/tr_template.docx`.
3. Add deterministic helpers in `sysdoc.py`:
   - load analysis JSON;
   - ensure ETP cache;
   - filter applicable ETP items;
   - exact replacement with pending list;
   - placeholder replacement in docx paragraphs/tables;
   - output filename resolver;
   - `create(project, tipo="tr")`.
4. Add `create` parser and `main()` dispatch.
5. Add CLI tests and docx XML assertions.
6. Update README, CHANGELOG and version metadata.

## Risks

- `python-docx` dependency must be installed in the runtime before tests pass.
- Placeholder replacement can fail if a placeholder is split across runs; keep the initial template simple, one placeholder per paragraph.
- Exact text replacement may miss clauses due to PDF extraction line breaks. This is acceptable for MVP if failures are surfaced in "Substituições pendentes".
- Generating a polished official TR is out of scope. The output is a base for human editing.

## Research Complete

Recommendation for planning: generate one executable plan, `02-01-PLAN.md`, covering `SYSD-04` and `SYSD-05` in a single wave.
