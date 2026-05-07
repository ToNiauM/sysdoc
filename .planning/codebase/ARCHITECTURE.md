<!-- refreshed: 2026-05-07 -->
# Architecture

**Analysis Date:** 2026-05-07

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                      User Interaction Layer                  │
├──────────────────┬──────────────────┬───────────────────────┤
│   CLI (`sysdoc.py`)  │   GUI (`sysdoc_gui.py`)  │  Shell Script (`run_sysdoc.sh`) │
└────────┬─────────┴────────┬─────────┴──────────┬────────────┘
         │                  │                     │
         ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Core Workflow Layer                       │
│  `sysdoc.py` (routing) | `templates/validate_sysdoc.py` | `templates/render_analise.py` │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                              │
│  `[project-folder]/` (ETP.pdf, TR.pdf, .sysdoc/cache/) | `dados_consolidados.json` | `analise_*.html` │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                  External Integration Layer                  │
│  LLM Providers (OpenRouter, OpenAI, Gemini, Anthropic) | VPS (SSH/SCP Deploy) │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| CLI Entrypoint | Route user commands to core workflows | `sysdoc.py` |
| GUI | tkinter interface wrapping CLI subprocesses | `sysdoc_gui.py` |
| Shell Script Wrapper | Sequential execution of prepare, analyze, deploy | `run_sysdoc.sh` |
| Canonical Operational Flow | IA-agnostic workflow definition for LLM agents | `skills/sysdoc/SKILL.md` |
| JSON Validator | Enforce schema, coherence, and PT-BR rules on analysis output | `templates/validate_sysdoc.py` |
| HTML Renderer | Deterministic HTML generation from validated JSON | `templates/render_analise.py` |
| JSON Schema | Canonical schema for `dados_consolidados.json` | `templates/schema_sysdoc.json` |
| HTML Template | Immutable template for analysis reports | `templates/analise_template.html` |
| Automated Tests | pytest tests for validator and renderer | `tests/test_validate.py` |

## Pattern Overview

**Overall:** CLI-first, offline-first workflow with deterministic validation/rendering and LLM-agnostic analysis orchestration.

**Key Characteristics:**
- Offline deterministic core: Prepare, validate, render steps require no network access
- LLM-agnostic analysis: Supports multiple providers via OpenRouter, OpenAI, Gemini, Anthropic
- Project-based isolation: Each analysis project is a self-contained subdirectory
- Schema-enforced outputs: All analysis JSON must pass strict schema and coherence validation
- Immutable templates: Rendering and validation templates are never modified during analysis

## Layers

**User Interaction Layer:**
- Purpose: Accept user input and trigger workflows
- Location: Root directory
- Contains: CLI script, GUI script, shell wrapper
- Depends on: Core Workflow Layer
- Used by: End users, LLM agents

**Core Workflow Layer:**
- Purpose: Execute analysis workflow steps (prepare, analyze, validate, render, deploy)
- Location: `sysdoc.py`, `templates/`, `skills/`
- Contains: CLI routing logic, validation, rendering, operational flow definitions
- Depends on: Data Layer, External Integration Layer
- Used by: User Interaction Layer

**Data Layer:**
- Purpose: Store project inputs, cache, and analysis outputs
- Location: `[project-folder]/`, `[project-folder]/.sysdoc/cache/`
- Contains: Source PDFs/DOCX, extracted text, analysis JSON, rendered HTML
- Depends on: None
- Used by: Core Workflow Layer

**External Integration Layer:**
- Purpose: Provide LLM analysis capabilities and deploy outputs
- Location: External services
- Contains: LLM provider APIs, VPS hosting
- Depends on: Core Workflow Layer (for API keys/config)
- Used by: Core Workflow Layer

## Data Flow

### Primary Request Path (sysdoc all [pasta])
1. User invokes `sysdoc all [pasta]` → CLI entrypoint `sysdoc.py` (argparse routing in `sysdoc.py`)
2. Fase 1 (Prepare): `sysdoc prepare [pasta]` extracts PDF/DOCX text to `[pasta]/.sysdoc/cache/` using `pdftotext` or `pandoc`
3. Fase 2 (Analyze): LLM agent reads `skills/sysdoc/SKILL.md`, `templates/schema_sysdoc.json`, and cache texts to generate `dados_consolidados.json`
4. Fase 3 (Publish): `sysdoc publish [pasta]` runs `templates/validate_sysdoc.py` to validate JSON, then `templates/render_analise.py` to generate HTML
5. Fase 4 (Deploy): `sysdoc deploy [pasta]` uses SSH/SCP to copy HTML to VPS

### Secondary Flow (sysdoc render [pasta])
1. User invokes `sysdoc render [pasta]`
2. `sysdoc.py` runs `templates/render_analise.py` directly on existing `dados_consolidados.json`
3. Outputs `analise_[model]_[date].html` to `[pasta]/`

**State Management:**
- Project state is stored in `[pasta]/dados_consolidados.json` (active) and versioned copies
- User config stored in `~/.sysdoc/config.json` (API keys, provider preferences)
- Cache state stored in `[pasta]/.sysdoc/cache/` (deterministic, regenerated on prepare)

## Key Abstractions

**Analysis Project:**
- Purpose: Self-contained unit of analysis for a single procurement process
- Examples: `[licitacao-001]/`, `[pregao-2026-05]/`
- Pattern: Isolated subdirectory with standard structure (ETP.pdf, TR.pdf, modelos/, .sysdoc/cache/, outputs)

**Validated Analysis Output:**
- Purpose: Schema-enforced JSON containing comparative analysis of ETP and TR
- Examples: `dados_consolidados.json`, `dados_consolidados_claude-sonnet-4-6_2026-05-07.json`
- Pattern: Must pass `templates/validate_sysdoc.py` checks before rendering

## Entry Points

**CLI (`sysdoc.py`):**
- Location: `sysdoc.py`
- Triggers: User running `sysdoc [command] [args]` in terminal
- Responsibilities: Parse commands, route to prepare/validate/render/publish/deploy workflows, manage config

**GUI (`sysdoc_gui.py`):**
- Location: `sysdoc_gui.py`
- Triggers: User running `python sysdoc_gui.py`
- Responsibilities: tkinter interface for offline CLI features, subprocess calls to `sysdoc.py`

**Shell Script (`run_sysdoc.sh`):**
- Location: `run_sysdoc.sh`
- Triggers: User running `bash run_sysdoc.sh [pasta]`
- Responsibilities: Sequential execution of Fase 1 (prepare), Fase 2 (analyze via agent), Fase 4 (deploy)

**Canonical Operational Flow (`skills/sysdoc/SKILL.md`):**
- Location: `skills/sysdoc/SKILL.md`
- Triggers: LLM agent executing `sysdoc all [pasta]` macro
- Responsibilities: Define IA-agnostic workflow for analysis, validation, rendering, deployment

## Architectural Constraints

- **Threading:** Python GIL applies; core workflows are single-threaded, GUI uses subprocess for non-blocking CLI calls
- **Global state:** User config loaded from `~/.sysdoc/config.json` at runtime; no module-level singletons in core logic
- **Circular imports:** None detected; small, modular codebase with clear separation of concerns
- **Immutable templates:** `templates/analise_template.html` and `templates/render_analise.py` are never modified during analysis — enforced by project rules

## Anti-Patterns

### Manual HTML Editing
**What happens:** User edits generated HTML directly instead of updating `dados_consolidados.json` and re-rendering
**Why it's wrong:** HTML is deterministic output; manual changes are overwritten on next render and break traceability
**Do this instead:** Modify `dados_consolidados.json` and run `sysdoc render [pasta]` to regenerate HTML (per `CLAUDE.md` rules)

### Generic Model Slug
**What happens:** `modelo_ia` field in JSON is set to `ia`, `modelo`, or `default`
**Why it's wrong:** Validation fails per `templates/validate_sysdoc.py` — requires real model slug (e.g., `claude-sonnet-4-6`)
**Do this instead:** Set `modelo_ia` to the exact model slug used for analysis (e.g., `gpt-5`, `gemini-2-5-pro`)

## Error Handling

**Strategy:** Deterministic validation with explicit error messages

**Patterns:**
- Schema validation: `templates/validate_sysdoc.py` enforces JSON structure via `templates/schema_sysdoc.json`
- Coherence validation: Enforces rules like `classificação=risco` → `risco_jurídico` ∈ {`relevante`, `bloqueante`}
- CLI error handling: `sysdoc.py` returns non-zero exit codes and print error messages for invalid inputs
- PT-BR validation: Checks for correct Brazilian Portuguese accents in generated fields

## Cross-Cutting Concerns

**Logging:** Print statements for CLI output; no centralized logging framework
**Validation:** Centralized in `templates/validate_sysdoc.py` — all JSON outputs must pass before rendering
**Authentication:** LLM API keys stored in `~/.sysdoc/config.json` or environment variables (`OPENROUTER_API_KEY`, etc.)
**Configuration:** User-level config in `~/.sysdoc/config.json`; project-level config inherits from user config

---

*Architecture analysis: 2026-05-07*
