# Phase 2 Pattern Map: Comando Create (Word/PDF)

**Phase:** 2 - Comando Create (Word/PDF)  
**Date:** 2026-05-08  
**Status:** Complete

## Closest Existing Patterns

### CLI subcommand routing

**Analog:** `sysdoc.py:build_parser()` and `sysdoc.py:main()`

Use the existing subparser pattern:

- create a parser with `sub.add_parser(...)`;
- add `project` argument;
- add any flags or optional positional arguments;
- dispatch in `main()` with `if args.command == "...": return ...`.

Phase 2 should add:

```python
create_parser = sub.add_parser("create", help="Gera documento Word a partir da análise.")
create_parser.add_argument("project", nargs="?", default=".", help="Pasta do projeto SysDoc.")
create_parser.add_argument("tipo", nargs="?", default="tr", choices=["tr"], help="Tipo de documento.")
create_parser.add_argument("--tipo", dest="tipo_flag", choices=["tr"], help="Tipo de documento.")
```

And dispatch:

```python
if args.command == "create":
    return create(args.project, tipo=args.tipo_flag or args.tipo)
```

### Cache preparation before agent handoff

**Analog:** `sysdoc.py:analyze()`

`analyze()` checks `paths.context` and runs `prepare(project)` when cache is missing. Phase 2 should mirror this for `paths.source_cache / "ETP.txt"`:

```python
if not etp_txt.is_file():
    result = prepare(project)
    if result != 0:
        return result
```

### Versioned output naming

**Analog:** `sysdoc.py:publish()` and `resolve_next_json_archive()`

`publish()` derives output identity from `modelo_ia` and `data_análise`. Phase 2 should mirror:

```python
model = slug(data.get("modelo_ia", "modelo"))
date = extract_date(data.get("data_análise", ""))
```

Recommended new helper:

```python
def resolve_next_docx_output(project_dir: Path, prefix: str, model: str, date: str) -> Path:
    stem = f"{prefix}_{model}_{date}"
    candidate = project_dir / f"{stem}.docx"
    ...
```

### Deterministic renderer behavior

**Analog:** `templates/render_analise.py`

The Word generator should behave like the HTML renderer in principle:

- input is data + deterministic template;
- output is generated, not manually edited;
- no LLM calls;
- clear error if inputs are missing;
- print generated output path.

### Tests

**Analog:** `tests/test_cli.py`

Use:

- `tmp_path` for isolated projects;
- monkeypatching `sysdoc.prepare` when testing automatic cache behavior;
- subprocess help tests for parser behavior;
- direct function calls for deterministic internals.

For `.docx`, inspect the ZIP directly:

```python
with zipfile.ZipFile(docx_path) as docx:
    xml = docx.read("word/document.xml").decode("utf-8")
assert "Objeto revisado" in xml
```

## Files Expected To Change During Execution

- `sysdoc.py`
- `pyproject.toml`
- `tests/test_cli.py`
- `README.md`
- `CHANGELOG.md`
- `templates/tr_template.docx` (new)

## Files To Avoid

These are immutable for analysis flows and should not be changed for Phase 2 unless the user explicitly re-scopes the project:

- `templates/analise_template.html`
- `templates/render_analise.py`
- `templates/validate_sysdoc.py`

## Pattern Mapping Complete
