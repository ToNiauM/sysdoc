# Coding Conventions

**Analysis Date:** 2026-05-07

## Naming Patterns

**Files:**
- Python modules: `snake_case.py` — e.g., `sysdoc.py`, `validate_sysdoc.py`
- Test files: `test_<module>.py` — e.g., `test_validate.py`
- Templates: `snake_case.py` — e.g., `render_analise.py`, `validate_sysdoc.py`

**Functions:**
- `snake_case` — e.g., `extract_pdf()`, `validate()`, `slug()`, `detect_process()`
- Private/internal helpers: `snake_case` with leading underscore — e.g., `_base_item()`, `_base_data()`

**Variables:**
- `snake_case` — e.g., `data`, `errors`, `item`, `paths`
- Loop variables: short names — e.g., `i`, `x`, `line`, `index`

**Classes:**
- `PascalCase` — e.g., `ProjectPaths`, `TestRequiredFields`, `TestModeloIA`
- Inner/private classes: `PascalCase`

**Constants:**
- `UPPER_SNAKE_CASE` — e.g., `ROOT`, `IGNORED_DIRS`, `KEY_TERMS`, `ENUMS`, `REQUIRED_TOP`
- Module-level constants defined at top of file after imports

**Type Variables:**
- Not extensively used; when present, `PascalCase` — e.g., `T` (implicit in type hints)

## Code Style

**Formatting:**
- Tool: `ruff` (configured in `pyproject.toml`)
- Line length: 100 characters (`line-length = 100`)
- Quote style: Double quotes preferred for strings
- Indentation: 4 spaces (Python standard)

**Linting:**
- Tool: `ruff>=0.4`
- Enabled rules: `E` (pycodestyle errors), `F` (pyflakes), `W` (pycodestyle warnings), `I` (isort)
- Ignored rules: `E501` (line too long — handled by line-length setting)
- Configuration in `pyproject.toml`:
  ```toml
  [tool.ruff]
  line-length = 100

  [tool.ruff.lint]
  select = ["E", "F", "W", "I"]
  ignore = ["E501"]
  ```

**String Literals:**
- Double quotes for strings: `"texto"`
- Docstrings use triple double quotes: `"""docstring"""`
- F-strings preferred for interpolation: `f"Texto {variable}"`

## Import Organization

**Order (enforced by ruff `I` rule):**
1. Future imports: `from __future__ import annotations`
2. Standard library: `import argparse`, `import json`, `from pathlib import Path`
3. Third-party: `import pytest`, `import pypdf`
4. Local modules: `from validate_sysdoc import validate`, `from sysdoc import slug`

**Example from `tests/test_validate.py`:**
```python
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "templates"))

from validate_sysdoc import validate, is_traceable, trace_tokens, word_count
from sysdoc import slug, extract_date, detect_process, sanitize_filename
```

**Path manipulation:** Use `sys.path.insert()` to add project root for imports in test files.

## Error Handling

**Patterns:**
- Use `try/except` with specific exceptions — e.g., `except ImportError as exc:`, `except subprocess.CalledProcessError as exc:`
- Raise `SystemExit` for CLI errors with descriptive messages — e.g., `raise SystemExit(f"JSON não encontrado: {rel(json_path)}")`
- Return error codes from main functions: `return 0` (success), `return 1` (error), `return 2` (argument error)
- Validate inputs early and fail fast

**Example from `sysdoc.py`:**
```python
def ensure_project_inputs(paths: ProjectPaths) -> None:
    missing = []
    if _find_file_case_insensitive(paths.root, "ETP.pdf") is None:
        missing.append("ETP.pdf")
    if _find_file_case_insensitive(paths.root, "TR.pdf") is None:
        missing.append("TR.pdf")
    if paths.modelos is None:
        missing.append("modelos/ ou Modelos/")
    if missing:
        raise SystemExit(f"Entradas obrigatórias ausentes em {rel(paths.root)}: {', '.join(missing)}")
```

**Subprocess errors:**
```python
try:
    result = subprocess.run(ssh_cmd, capture_output=True, text=True, check=True)
    next_idx = result.stdout.strip()
except subprocess.CalledProcessError as exc:
    print(f"Erro na conexão SSH: {exc.stderr}")
    return 1
```

## Logging

**Framework:** `print()` statements for CLI output (no formal logging framework)

**Patterns:**
- Status messages: `print(f"Contexto preparado: {rel(paths.context)}")`
- Errors: `print(f"Erro: {message}", file=sys.stderr)` or `raise SystemExit()`
- Success indicators: `print("✅ Deploy concluído com sucesso!")`
- Progress: `print(f"JSON versionado: {rel(archive)}")`

**No logging module usage observed in codebase.**

## Comments

**When to Comment:**
- Docstrings at module, class, and function level
- Inline comments for non-obvious logic
- TODO/FIXME not extensively used

**Docstring Style:**
- Google-style or simple docstrings
- Triple double quotes with summary line

**Example from `templates/validate_sysdoc.py`:**
```python
def is_traceable(excerpt, source):
    """
    Verifica se um trecho (de) é rastreável no texto fonte.
    """
    if str(excerpt or "").strip().startswith("[OMISSÃO]"):
        return True
    # ... implementation
```

**Multilingual Comments:**
- Code comments primarily in English (utility functions)
- Business logic comments in Portuguese
- Docstrings in Portuguese (project-specific)

## Function Design

**Size:**
- Functions typically 10-50 lines
- Large functions decomposed (e.g., `validate()` in `validate_sysdoc.py` at ~80 lines)

**Parameters:**
- Use type hints on dataclasses and public functions in `sysdoc.py`
- Default values for optional parameters: `def validate(path, project_dir=None):`
- **kwargs not extensively used

**Return Values:**
- Explicit return values: `return errors` (list), `return 0/1/2` (status codes)
- `None` implicit return for procedures

**Example with type hints (from `sysdoc.py`):**
```python
@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    modelos: Path | None
    cache: Path
    source_cache: Path
    manifest: Path
    context: Path
    config: Path
```

## Module Design

**Exports:**
- No `__all__` defined; public API implied by function/class names
- Main entry points: `main()` function in each module

**Module Structure Pattern:**
1. Shebang line: `#!/usr/bin/env python3`
2. Module docstring
3. `from __future__ import annotations`
4. Standard library imports
5. Third-party imports
6. Local imports
7. Constants
8. Dataclasses/Types
9. Functions
10. Classes
11. `if __name__ == "__main__":` block

**Example from `sysdoc.py`:**
```python
#!/usr/bin/env python3
"""
CLI operacional do SysDoc.
"""

from __future__ import annotations

import argparse
import json
# ... more imports ...

ROOT = Path(__file__).resolve().parent
# ... constants ...

@dataclass(frozen=True)
class ProjectPaths:
    # ...

def ensure_project_inputs(paths: ProjectPaths) -> None:
    # ...

def main(argv: list[str] | None = None) -> int:
    # ...

if __name__ == "__main__":
    raise SystemExit(main())
```

## Dataclasses

**Usage:**
- `from dataclasses import dataclass`
- Frozen dataclasses for immutable config: `@dataclass(frozen=True)`
- Used for structured data: `ProjectPaths` in `sysdoc.py`

**Example:**
```python
@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    modelos: Path | None
    cache: Path
    source_cache: Path
    manifest: Path
    context: Path
```

## Path Handling

**Preferred Library:** `pathlib.Path` (not `os.path`)

**Patterns:**
- Resolve paths early: `Path(__file__).resolve().parent`
- Use `/` operator for path joining: `ROOT / "templates"`
- Convert to string when needed for subprocess: `str(path)`

**Example:**
```python
ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
paths = project_paths(project)  # Returns ProjectPaths with Path objects
```

## Language and Localization

**Primary Language:**
- Code: English (function names, variables) mixed with Portuguese (business terms)
- Strings/Output: Portuguese (user-facing messages, error messages)
- Comments: Mixed (English for utilities, Portuguese for business logic)

**Portuguese Accentuation:**
- Validated by `validate_sysdoc.py` — requires correct Brazilian Portuguese accents
- `PT_BR_ACCENT_TERMS` dictionary defines mappings from unaccented to accented terms
- Validation error if terms like "analise" used instead of "análise"

---

*Convention analysis: 2026-05-07*
