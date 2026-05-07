# Technology Stack

**Analysis Date:** 2026-05-07

## Languages

**Primary:**
- Python 3.x - Core CLI logic (`sysdoc.py`), GUI (`sysdoc_gui.py`), validation (`templates/validate_sysdoc.py`), rendering (`templates/render_analise.py`)

**Secondary:**
- HTML - HTML template (`templates/analise_template.html`), rendered reports (`analise_*.html`)
- JSON - Data storage (`dados_consolidados.json`, `templates/schema_sysdoc.json`)

## Runtime

**Environment:**
- Python 3.x (no specific version pinned, uses standard library features compatible with 3.6+)

**Package Manager:**
- pip (Python package manager)
- Lockfile: Missing (no `requirements.txt` or lockfile present)

## Frameworks

**Core:**
- Standard Library (argparse for CLI, tkinter for GUI, json, os, subprocess for core logic)

**Testing:**
- pytest - Test runner for `tests/test_validate.py`

**Build/Dev:**
- No build tools (script-based project, no compilation step)

## Key Dependencies

**Critical:**
- `jsonschema` - JSON validation against `templates/schema_sysdoc.json` (`templates/validate_sysdoc.py`)
- `jinja2` - HTML rendering from `templates/analise_template.html` (`templates/render_analise.py`)
- `requests` - HTTP calls to LLM provider APIs (OpenRouter, OpenAI, Gemini, Anthropic) (`sysdoc.py`)

**Infrastructure:**
- `pdftotext` (poppler-utils) - PDF text extraction (`sysdoc prepare` command)
- `pandoc` - DOCX to text conversion for reference files (`sysdoc prepare` command)
- `pytest` - Test execution (dev dependency)

## Configuration

**Environment:**
- Configured via `~/.sysdoc/config.json` (API keys, provider preferences) or environment variables
- Key configs: `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `SYSDOC_MAX_LLM_CONTEXT_CHARS` (default: 700000)

**Build:**
- No build configuration files (project uses interpreted Python scripts)

## Platform Requirements

**Development:**
- Python 3.x, pip, pdftotext, pandoc, pytest

**Production:**
- Python 3.x runtime, SSH/SCP client (for VPS deployment via `sysdoc deploy`)

---

*Stack analysis: 2026-05-07*
