# Testing Patterns

**Analysis Date:** 2026-05-07

## Test Framework

**Runner:**
- `pytest>=7.0` (defined in `pyproject.toml` under `[project.optional-dependencies]` dev)
- Config: `pyproject.toml` with `[tool.pytest.ini_options]`

**Assertion Library:**
- Built-in `assert` statements (pytest native)

**Run Commands:**
```bash
python -m pytest                          # Run all tests
python -m pytest -v                       # Verbose mode
python -m pytest tests/test_validate.py   # Run specific test file
python -m pytest -x                       # Stop on first failure
```

## Test File Organization

**Location:**
- Centralized in `tests/` directory at project root

**Naming:**
- Pattern: `test_<module>.py`
- Current file: `tests/test_validate.py`

**Structure:**
```
tests/
├── __pycache__/
└── test_validate.py          # Tests for validate_sysdoc.py and sysdoc.py utilities
```

## Test Configuration

**pytest configuration in `pyproject.toml`:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Test Dependencies (from `pyproject.toml`):**
```toml
[project.optional-dependencies]
dev = ["pytest>=7.0", "ruff>=0.4"]
```

Install dev dependencies:
```bash
pip install -e ".[dev]"
```

## Test Structure

**Suite Organization:**
- Tests organized in classes grouped by functionality
- Class naming: `Test<Feature>` (PascalCase)
- Test method naming: `test_<behavior>` (snake_case)

**Example from `tests/test_validate.py`:**
```python
class TestRequiredFields:
    def test_valid_data_passes(self, tmp_path):
        # Cria arquivos placeholder para que validate_document_paths não recuse
        (tmp_path / "ETP.pdf").write_bytes(b"%PDF-1.4 placeholder")
        (tmp_path / "TR.pdf").write_bytes(b"%PDF-1.4 placeholder")
        data = _base_data()
        json_file = tmp_path / "dados_consolidados.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")
        errors = validate(str(json_file), str(tmp_path))
        assert errors == [], f"Erros inesperados: {errors}"

    def test_missing_titulo(self, tmp_path):
        data = _base_data()
        del data["titulo"]
        # ... test implementation
```

**Current Test Classes:**
- `TestRequiredFields` — Tests for required JSON fields
- `TestModeloIA` — Tests for modelo_ia validation
- `TestCoherence` — Tests for enum coherence rules
- `TestWordCount` — Tests for word count validation
- `TestTraceability` — Tests for text traceability
- `TestSlug` — Tests for `slug()` utility
- `TestExtractDate` — Tests for `extract_date()` utility
- `TestDetectProcess` — Tests for `detect_process()` utility
- `TestSanitizeFilename` — Tests for `sanitize_filename()` utility

## Fixtures

**Built-in fixtures used:**
- `tmp_path` — pytest built-in fixture providing temporary directory Path object

**Custom fixtures (helper functions):**
```python
def _base_item(doc="ETP", num=1, **overrides):
    item = {
        "id": f"{doc}-{num:03d}",
        "número": num,
        "item": "Objeto da contratação",
        # ... default fields
    }
    item.update(overrides)
    return item


def _base_data(**overrides):
    data = {
        "titulo": "Análise Comparativa",
        "modelo_ia": "gpt-4o-mini",
        "itens": [_base_item("ETP", 1), _base_item("TR", 1)],
        # ... default structure
    }
    data.update(overrides)
    return data
```

**Pattern:** Helper functions (not pytest fixtures) used to create test data with sensible defaults and override capability.

## Test Patterns

**Setup Pattern:**
- Create temporary JSON files using `tmp_path`
- Use `_base_data()` and `_base_item()` helpers
- Create placeholder PDF files for validation tests

**Assertion Pattern:**
```python
# Assert no errors
assert errors == [], f"Erros inesperados: {errors}"

# Assert error contains specific text
assert any("titulo" in e for e in errors)

# Assert specific condition
assert slug("claude-sonnet-4-6") == "claude-sonnet-4-6"
assert word_count("olá mundo") == 2
```

**Error Testing Pattern:**
```python
def test_missing_titulo(self, tmp_path):
    data = _base_data()
    del data["titulo"]  # Remove required field
    json_file = tmp_path / "dados_consolidados.json"
    json_file.write_text(json.dumps(data), encoding="utf-8")
    errors = validate(str(json_file), str(tmp_path))
    assert any("titulo" in e for e in errors)  # Expect validation error
```

## Mocking

**Framework:** Not explicitly used

**Patterns:**
- No `unittest.mock` or `pytest-mock` usage observed
- Tests use real functions with controlled inputs
- File system mocking via `tmp_path` fixture

**What to Mock:**
- External API calls (none in current codebase)
- File system operations (use `tmp_path` instead)

**What NOT to Mock:**
- Internal validation logic — test with real data
- Utility functions — test directly

## Fixtures and Factories

**Test Data:**
```python
def _base_item(doc="ETP", num=1, **overrides):
    # Creates a valid item dict with defaults
    # Supports overrides via **overrides
```

**Location:**
- Defined at top of `tests/test_validate.py`
- Module-level helper functions (not in `conftest.py`)

**Factory Pattern:**
- `_base_data()` creates complete valid JSON structure
- `_base_item()` creates individual items
- Both support customization via `**overrides`

## Coverage

**Requirements:** No enforced coverage threshold

**View Coverage:**
```bash
python -m pytest --cov=sysdoc --cov=validate_sysdoc
python -m pytest --cov --cov-report=html
```

**Note:** Coverage tools not configured in `pyproject.toml`. Would require `pytest-cov` package.

## Test Types

**Unit Tests:**
- Scope: Individual functions and validation rules
- Examples: `test_slug_with_accents()`, `test_iso_date()`
- Approach: Call function with specific inputs, assert expected outputs

**Integration Tests:**
- Scope: End-to-end JSON validation
- Example: `test_valid_data_passes()` — validates complete JSON structure
- Approach: Create complete test data, run full validation, check results

**E2E Tests:**
- Not used currently
- Could be added for CLI commands (`sysdoc status`, `sysdoc prepare`)

## Common Patterns

**Testing Validation Errors:**
```python
def test_missing_field(self, tmp_path):
    data = _base_data()
    del data["field_name"]
    json_file = tmp_path / "dados_consolidados.json"
    json_file.write_text(json.dumps(data), encoding="utf-8")
    errors = validate(str(json_file), str(tmp_path))
    assert any("field_name" in e for e in errors)
```

**Testing Utility Functions:**
```python
class TestSlug:
    def test_basic_slug(self):
        assert slug("claude-sonnet-4-6") == "claude-sonnet-4-6"

    def test_slug_with_accents(self):
        assert slug("Análise Técnica") == "analise-tecnica"

    def test_slug_empty(self):
        assert slug("") == "modelo"
```

**Testing with Temporary Files:**
```python
def test_valid_data_passes(self, tmp_path):
    # Create required files
    (tmp_path / "ETP.pdf").write_bytes(b"%PDF-1.4 placeholder")
    (tmp_path / "TR.pdf").write_bytes(b"%PDF-1.4 placeholder")
    # Create test JSON
    data = _base_data()
    json_file = tmp_path / "dados_consolidados.json"
    json_file.write_text(json.dumps(data), encoding="utf-8")
    # Run validation
    errors = validate(str(json_file), str(tmp_path))
    assert errors == [], f"Erros inesperados: {errors}"
```

**Assertion with Error Messages:**
```python
assert errors == [], f"Erros inesperados: {errors}"
assert word_count("") == 0
assert is_traceable(excerpt, source), f"Expected traceable: {excerpt}"
```

## Running Tests

**From project root:**
```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run specific test class
python -m pytest tests/test_validate.py::TestSlug -v

# Run specific test method
python -m pytest tests/test_validate.py::TestSlug::test_basic_slug -v

# Stop on first failure
python -m pytest -x

# Show local variables on failure
python -m pytest -l
```

**In CI/CD:**
```bash
pip install -e ".[dev]"
python -m pytest
```

## Test File Pattern

**Complete example structure:**
```python
"""
Tests automatizados do SysDoc.

Cobertura:
  - module: feature 1, feature 2
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "templates"))

from module_under_test import function1, function2


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _base_data(**overrides):
    data = {"default": "value"}
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# Test Class
# ---------------------------------------------------------------------------

class TestFeature:
    def test_valid_case(self, tmp_path):
        # Arrange
        data = _base_data()
        # Act
        result = function1(data)
        # Assert
        assert result is True
```

---

*Testing analysis: 2026-05-07*
