---
phase: 01-cli-style-gsd
reviewed: 2026-05-08T21:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - .claude/settings.local.json
  - .claude/skills/sysdoc-analise/SKILL.md
  - .gitignore
  - .opencode/skills/sysdoc-analise/SKILL.md
  - AGENTS.md
  - CHANGELOG.md
  - CLAUDE.md
  - pyproject.toml
  - README.md
  - setup.py
  - skills/sysdoc/SKILL.md
  - sysdoc.py
  - tests/test_cli.py
findings:
  critical: 3
  warning: 7
  info: 5
  total: 15
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-05-08T21:00:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Review of Phase 1 (`01-cli-style-gsd`) covering the CLI-style GSD transformation of SysDoc. Thirteen files reviewed at standard depth: the main CLI entry point (`sysdoc.py`), configuration, harness wrappers, tests, documentation, and build files.

Three **blocker** issues found: a hardcoded production VPS IP address in `deploy()`, version/dependency conflicts between `setup.py` and `pyproject.toml`, and a version mismatch between `pyproject.toml` (1.2.0) and `sysdoc.py`/`README.md` (1.3.0). Seven **warnings** cover silent error suppression, missing exception handling for corrupted files, and stale permission patterns. Five **info** items flag dead code, documentation inconsistencies, and test rigor gaps.

---

## Critical Issues

### CR-01: Hardcoded production VPS IP and path as fallback values

**File:** `sysdoc.py:717-718`
**Issue:** The `deploy()` function contains hardcoded fallback values for `vps_host` (`root@76.13.170.15`) and `vps_path` (`/opt/web/cfc-analise/html`). This exposes what appears to be a real production server IP address in source code. If a project's `.sysdoc/config.yaml` has empty `vps_host`/`vps_path`, deployment will silently target this hardcoded server — potentially sending sensitive analysis output to an unintended destination. This is both a security exposure (server address in repo) and an operational risk (accidental production deployment).

**Fix:**
```python
# lines 717-718, replace:
    vps_host = (config.get("vps_host") or "").strip() or "root@76.13.170.15"
    vps_path = (config.get("vps_path") or "").strip() or "/opt/web/cfc-analise/html"
# with:
    vps_host = (config.get("vps_host") or "").strip()
    vps_path = (config.get("vps_path") or "").strip()
    if not vps_host or not vps_path:
        print("VPS não configurada. Use 'sysdoc config -vps <host> -path <dir>' para configurar.")
        return 1
```

---

### CR-02: Stale `setup.py` with wrong version and deprecated dependency

**File:** `setup.py:1-17`
**Issue:** `setup.py` still declares `version="0.1.0"` and depends on `"PyPDF2>=3.0.0"` (a deprecated, renamed package). Meanwhile `pyproject.toml` correctly declares version `1.2.0` (or should be 1.3.0, see CR-03) and depends on `pypdf>=4.0.0`. If `pip install -e .` resolves via `setup.py` instead of `pyproject.toml` (possible in older pip/setuptools configurations), the installed package will have the wrong version, the wrong PDF library (PyPDF2 is unmaintained), and will be missing `pyyaml>=6.0` (required for config support added in this phase).

**Fix:** Update `setup.py` to match `pyproject.toml`, or remove `setup.py` entirely (since `pyproject.toml` with `[build-system]` and `setuptools.build_meta` is the modern standard and `setup.py` is vestigial).

```python
# setup.py — update to:
from setuptools import setup

setup(
    name="sysdoc",
    version="1.3.0",
    py_modules=["sysdoc"],
    install_requires=[
        "pypdf>=4.0.0",
        "pyyaml>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "sysdoc=sysdoc:main",
        ],
    },
)
```

---

### CR-03: Version mismatch between `pyproject.toml` and source code

**File:** `pyproject.toml:7` vs `sysdoc.py:39` vs `README.md:228`
**Issue:** Three different version sources are inconsistent:
- `pyproject.toml` line 7: `version = "1.2.0"`
- `sysdoc.py` line 39: `VERSION = "1.3.0"`
- `README.md` line 228: `(1.3.0)`

The `sysdoc --version` output comes from `sysdoc.py`, so the CLI reports 1.3.0. But `pip show sysdoc` would report 1.2.0 (from `pyproject.toml`). The CHANGELOG documents 1.3.0 additions (handoff visual, `guia` command, `--dry-run`) that are present in the code, confirming 1.3.0 is the intended version. `pyproject.toml` was not bumped.

**Fix:** Update `pyproject.toml` line 7:
```toml
version = "1.3.0"
```

---

## Warnings

### WR-01: Silent swallowing of YAML parse errors

**File:** `sysdoc.py:104-109`
**Issue:** `load_config()` catches bare `Exception` on YAML parsing and silently returns `{}`. If a user's `.sysdoc/config.yaml` has a typo or invalid YAML syntax, the config is silently ignored with no warning. The user will not know why their VPS deploy settings (or other config) aren't being applied.

**Fix:**
```python
    try:
        data = yaml.safe_load(paths.config.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        print(f"⚠️  Erro ao ler {rel(paths.config)}: {exc}", file=sys.stderr)
        return {}
    except Exception:
        return {}
```

---

### WR-02: Unhandled exceptions in PDF extraction with corrupted files

**File:** `sysdoc.py:175-191`
**Issue:** `extract_pdf()` only wraps the `import pypdf` statement in a try/except. The actual `PdfReader`, `extract_text()`, and page iteration (lines 181-191) are unprotected. If a PDF is corrupted, encrypted, or malformed, `pypdf` will raise exceptions (e.g., `PdfReadError`, `PyPdfError`) that propagate as unhandled crashes to the user with a raw traceback.

**Fix:** Wrap the extraction logic in a try/except:
```python
    try:
        reader = pypdf.PdfReader(str(path))
    except Exception as exc:
        raise RuntimeError(f"Erro ao ler PDF {path.name}: {exc}") from exc
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = "[ERRO DE EXTRAÇÃO]"
        pages.append(f"\n\n--- Página {index} ---\n{text.strip()}")
```

---

### WR-03: Unhandled exceptions in DOCX extraction with corrupted files

**File:** `sysdoc.py:194-212`
**Issue:** `extract_docx()` has no try/except around `zipfile.ZipFile` (corrupted ZIP), `docx.read()` (missing `word/document.xml`), or `ElementTree.fromstring()` (malformed XML). Any of these failures produce a raw traceback crash instead of a helpful error message.

**Fix:** Wrap the extraction logic:
```python
    try:
        with zipfile.ZipFile(path) as docx:
            xml = docx.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise RuntimeError(f"Erro ao ler DOCX {path.name}: {exc}") from exc
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise RuntimeError(f"Erro ao analisar XML de {path.name}: {exc}") from exc
```

---

### WR-04: Silent data corruption via `errors="replace"` in text reading

**File:** `sysdoc.py:221`
**Issue:** `path.read_text(encoding="utf-8", errors="replace")` silently replaces undecodable bytes with the Unicode replacement character `�`. If a text file contains Latin-1 or Windows-1252 encoded characters (common in Brazilian Portuguese documents), they are silently corrupted instead of raising an error or attempting fallback encodings. This is especially dangerous because the corrupted text becomes the basis for legal analysis.

**Fix:** At minimum, log a warning when replacement occurs. Better: attempt common Brazilian encodings first.
```python
    if suffix in TEXT_SUFFIXES:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "\ufffd" in text:
            print(f"⚠️  {path.name}: caracteres não-decodificáveis encontrados (substituídos por �).",
                  file=sys.stderr)
        return text
```

---

### WR-05: Overly broad exception handling in main() stdout reconfigure

**File:** `sysdoc.py:991-996`
**Issue:** The `main()` function catches bare `Exception` when attempting `stream.reconfigure()`:
```python
    except Exception:
        pass
```
This silently swallows ALL exceptions — not just `AttributeError` when `reconfigure` doesn't exist (e.g., older Python), but also `OSError`, `ValueError`, etc. If there's a real issue with stdout/stderr encoding configuration, the user gets no error and may experience garbled output.

**Fix:** Narrow the exception:
```python
    except (AttributeError, OSError):
        pass
```

---

### WR-06: Unbounded loop with file reads in `resolve_next_json_archive`

**File:** `sysdoc.py:803-807`
**Issue:** `resolve_next_json_archive()` uses `while True` with `index += 1` to scan for the next available archive slot. On each iteration, it calls `candidate.read_text()` to compare payloads. If a project accumulates hundreds of versioned JSONs, this loop reads and compares every file. While not an infinite loop in practice, there is no upper bound and no caching of file contents.

**Fix:** Add a reasonable upper bound or use directory listing:
```python
    import itertools
    for idx in itertools.count(start=2):
        candidate = project_dir / f"{stem}_{idx}.json"
        if not candidate.exists() or candidate.read_text(encoding="utf-8", errors="replace") == payload:
            return candidate
```

---

### WR-07: Stale permission patterns in Claude Code settings

**File:** `.claude/settings.local.json:15-16`
**Issue:** Two permission patterns appear to be debugging leftovers from implementation:
- `"Bash(python -c \"import yaml; print\\(yaml.__version__\\)\")"` — authorizes a command with unnecessary escaped parentheses in the pattern
- `"Bash(python -m pip install \"pyyaml>=6.0\")"` — authorizes pip install, which is no longer needed since `pyyaml` is now a hard dependency in `pyproject.toml`

These stale permissions broaden the Claude Code attack surface without serving any current purpose.

**Fix:** Remove lines 15 and 16 from the permissions allowlist.

---

## Info

### IN-01: Dead code — unused `DEFAULT_LLM_MODEL` constant

**File:** `sysdoc.py:36`
**Issue:** `DEFAULT_LLM_MODEL = "openai/gpt-4o-mini"` is defined but never referenced anywhere in the codebase. Since Phase 1 removed all LLM API calls (the CLI is now strictly deterministic), this constant is dead code.

**Fix:** Remove line 36.

---

### IN-02: Dead code — `ImportError` catch for `yaml` in `load_config`

**File:** `sysdoc.py:103-105`
**Issue:** `load_config()` does `try: import yaml; except ImportError: return {}`. Since `pyyaml>=6.0` is now a hard dependency in `pyproject.toml`, yaml should always be available. The `ImportError` catch is dead code (and harmless, but misleading).

**Fix:** Remove the try/except for ImportError; let it propagate if yaml is somehow missing (fail-fast is better for hard dependencies).

---

### IN-03: Documentation inconsistency — `--dry-run` claimed as new in three versions

**File:** `CHANGELOG.md:12,37,82`
**Issue:** The `sysdoc analyze --dry-run` flag is listed as a new feature in three different CHANGELOG sections:
- `[1.0.0]` line 82: "prepara o contexto e exibe o prompt completo sem chamar a LLM"
- `[1.2.0]` line 37 (implicit in `analyze` subcommand addition) 
- `[1.3.0]` line 12: "reimprime o handoff sem reextrair PDFs"

Similarly, `sysdoc analyze` is listed as "novo subcomando" in 1.2.0 (line 37) but was present in 1.0.0. This suggests copy-paste or incomplete CHANGELOG editing during rapid iteration.

**Fix:** Consolidate: remove the 1.0.0 reference (that version had a different `analyze` that called LLMs) and clarify that 1.2.0 introduced the handoff-only `analyze` while 1.3.0 improved it with the visual handoff box and `--dry-run`.

---

### IN-04: Redundant `.git/` entry in `.gitignore`

**File:** `.gitignore:2`
**Issue:** `.git/` is listed in `.gitignore`, but Git always ignores its own repository directory. This entry has no effect and adds noise.

**Fix:** Remove line 2 (`.git/`).

---

### IN-05: Test `test_guia_missing_inputs` doesn't verify input was not called

**File:** `tests/test_cli.py:400-412`
**Issue:** The test mocks `builtins.input` but never asserts that `input_calls` (or equivalent) remains empty. If a regression caused `guia()` to call `input()` despite missing inputs, the test would still pass because the input mock returns `""` (empty string), and `guia()` would eventually fail with the same `rc == 1` for a different reason.

**Fix:** Track input calls and assert they are zero:
```python
        input_calls: list = []
        monkeypatch.setattr("builtins.input", lambda *a, **kw: input_calls.append(a) or "")
        # ... after guia() call:
        assert input_calls == [], "guia() não deve chamar input() quando entradas estão faltando"
```

---

_Reviewed: 2026-05-08T21:00:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
