# Codebase Structure

**Analysis Date:** 2026-05-07

## Directory Layout

```
SysDoc/
├── .claude/                # Claude Code configuration and skills
│   └── skills/             # Claude-specific skill wrappers
│       └── sysdoc-analise/ # SysDoc analysis skill for Claude
├── .git/                   # Git repository data (ignored by sysdoc)
├── .planning/              # GSD planning artifacts (generated)
│   └── codebase/           # Codebase analysis documents (generated)
├── backup/                 # Backup files (ignored by sysdoc)
├── skills/                 # Canonical IA-agnostic SysDoc skills
│   └── sysdoc/             # Canonical operational flow (single source of truth)
├── templates/              # Immutable templates and validators
│   ├── analise_template.html  # HTML report template
│   ├── render_analise.py      # Deterministic HTML renderer
│   ├── validate_sysdoc.py     # JSON validator
│   └── schema_sysdoc.json     # Canonical JSON schema
├── tests/                  # Automated pytest tests
│   └── test_validate.py    # Tests for JSON validator
├── [project-folders]/      # Analysis projects (e.g., licitacao-001/)
│   ├── ETP.pdf             # Required: Technical Requirements Document
│   ├── TR.pdf              # Required: Technical Report
│   ├── modelos/            # Required: Reference models (PDF, DOCX, TXT, MD)
│   ├── .sysdoc/            # Project-specific cache and metadata
│   │   └── cache/          # Extracted text and context
│   ├── dados_consolidados.json  # Active analysis output
│   └── analise_*.html      # Rendered report
├── sysdoc.py               # CLI entrypoint
├── sysdoc_gui.py           # tkinter GUI
├── run_sysdoc.sh           # Shell script wrapper
├── ROADMAP.md              # Planned improvements
├── CHANGELOG.md            # Version history
├── CLAUDE.md               # Claude Code instructions
└── .gitignore              # Git ignore rules
```

## Directory Purposes

**.claude/:**
- Purpose: Claude Code configuration, custom skills, and local settings
- Contains: `settings.local.json` (MCP pre-authorizations), `skills/` (Claude-specific wrappers)
- Key files: `.claude/skills/sysdoc-analise/SKILL.md`

**skills/:**
- Purpose: Canonical IA-agnostic operational flow for SysDoc
- Contains: `sysdoc/SKILL.md` (single source of truth for analysis workflow)
- Key files: `skills/sysdoc/SKILL.md`

**templates/:**
- Purpose: Immutable deterministic tools for validation and rendering
- Contains: HTML template, renderer, validator, JSON schema
- Key files: `templates/analise_template.html`, `templates/render_analise.py`, `templates/validate_sysdoc.py`
- Note: All files in this directory are immutable — never edit during analysis

**tests/:**
- Purpose: Automated tests for core deterministic tools
- Contains: pytest test scripts
- Key files: `tests/test_validate.py`

**[project-folders]/:**
- Purpose: Self-contained analysis projects for individual procurement processes
- Contains: Source PDFs/DOCX, reference models, cache, analysis outputs
- Key files: `ETP.pdf`, `TR.pdf`, `dados_consolidados.json`, `analise_*.html`
- Ignored by sysdoc: `.git`, `.claude`, `backup`, `skills`, `templates` (per `IGNORED_DIRS` in `sysdoc.py`)

## Key File Locations

**Entry Points:**
- `sysdoc.py`: CLI entrypoint for all sysdoc commands
- `sysdoc_gui.py`: tkinter GUI for offline features
- `run_sysdoc.sh`: Shell script for sequential workflow execution

**Configuration:**
- `~/.sysdoc/config.json`: User-level config for API keys and provider preferences
- `CLAUDE.md`: Claude Code-specific instructions and rules
- `.claude/settings.local.json`: Local Claude settings (e.g., MCP pre-authorizations)

**Core Logic:**
- `sysdoc.py`: CLI routing, prepare, validate, render, publish, deploy workflows
- `templates/validate_sysdoc.py`: JSON schema and coherence validation
- `templates/render_analise.py`: Deterministic HTML rendering from JSON

**Testing:**
- `tests/test_validate.py`: Automated pytest tests for validator

**Schema:**
- `templates/schema_sysdoc.json`: Canonical JSON schema for `dados_consolidados.json`

## Naming Conventions

**Files:**
- Project folders: Arbitrary lowercase names, often with hyphens (e.g., `licitacao-001/`, `pregao-2026-05/`)
- Cache text files: `ETP.txt`, `TR.txt`, `REF-[name].txt` (located in `[pasta]/.sysdoc/cache/textos/`)
- Analysis JSON: `dados_consolidados.json` (active), `dados_consolidados_[model]_[date].json` (versioned, e.g., `dados_consolidados_claude-sonnet-4-6_2026-05-07.json`)
- HTML reports: `analise_[model]_[date].html` (e.g., `analise_gpt-5_2026-05-07.html`)
- Python scripts: snake_case (e.g., `sysdoc.py`, `validate_sysdoc.py`)

**Directories:**
- Hidden directories: `.sysdoc/`, `.claude/`, `.git/`
- Project subdirectories: `modelos/` (reference models), `.sysdoc/cache/` (extracted text)
- Skills: `skills/sysdoc/` (canonical), `.claude/skills/sysdoc-analise/` (Claude wrapper)

## Where to Add New Code

**New CLI Command:**
- Primary code: `sysdoc.py` (add new subparser to argparse)
- Tests: `tests/` directory (add test for new command)

**New Validation Rule:**
- Schema: Update `templates/schema_sysdoc.json`
- Logic: Update `templates/validate_sysdoc.py`
- Tests: Update `tests/test_validate.py`

**New Project:**
- Implementation: Create new subdirectory in root (use `sysdoc init [pasta]` to automate)

**New Skill:**
- Canonical: Add to `skills/` directory
- Claude-specific: Add to `.claude/skills/` directory

**Utilities:**
- Shared helpers: `sysdoc.py` (core logic) or new `utils/` directory (if needed)

## Special Directories

**.sysdoc/cache/:**
- Purpose: Stores extracted text from PDFs/DOCX and deterministic context map
- Generated: Yes (by `sysdoc prepare [pasta]`)
- Committed: Yes (deterministic, required for offline rendering)

**templates/:**
- Purpose: Immutable deterministic tools
- Generated: No
- Committed: Yes
- Rule: Never edit files in this directory during analysis

**skills/:**
- Purpose: Canonical operational flow
- Generated: No
- Committed: Yes
- Edit only: When updating IA-agnostic workflow

**backup/:**
- Purpose: User backups of project files
- Generated: Yes (by user)
- Committed: No (ignored by sysdoc and git)

---

*Structure analysis: 2026-05-07*
