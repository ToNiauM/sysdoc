# Phase 1 Research: CLI-style GSD

**Phase:** 1 - CLI-style GSD
**Date:** 2026-05-07

## Current State

### CLI Structure (`sysdoc.py`, 650 lines)

Current argparse-based CLI with subcommands:
- `status` — list projects
- `init [project]` — create project structure
- `prepare [project]` — extract PDF/DOCX → .sysdoc/cache/
- `validate [project]` — validate dados_consolidados.json
- `render [project]` — render HTML from JSON
- `publish [project]` — validate + version JSON + render HTML
- `deploy [project]` — SCP html to VPS
- `compare [project]` — compare versioned JSONs

Entry point: `pyproject.toml` registers `sysdoc = "sysdoc:main"` as console script.

### Agent Integration (Current)

1. **Claude Code**: `.claude/skills/sysdoc-analise/SKILL.md` — thin wrapper that delegates to `skills/sysdoc/SKILL.md`
2. **SKILL.md** (`skills/sysdoc/SKILL.md`): Defines macro commands (`sysdoc init`, `sysdoc all`, `sysdoc create TR`)
3. **CLAUDE.md**: Root instructions for Claude Code

### What Needs to Change

**Current gap:** The CLI is designed for `python sysdoc.py [command]`, not for `/sysdoc [command]` invocation from AI harnesses.

**GSD-like model:**
- GSD is invoked via slash commands (`/gsd-plan-phase`, `/gsd-execute-phase`)
- Each command triggers a skill that reads SKILL.md for instructions
- The skill orchestrates the AI agent + CLI tools

**Key insight:** SysDoc already HAS this pattern partially:
- `.claude/skills/sysdoc-analise/SKILL.md` triggers on "sysdoc [pasta]"
- `skills/sysdoc/SKILL.md` defines the operational flow
- `sysdoc.py` provides the deterministic CLI tools

### Architecture for GSD-style

**What GSD does that SysDoc doesn't yet:**
1. Multi-harness support (Claude Code, OpenCode, Codex, Antigravity)
2. Standardized `.sysdoc/config.yaml` per project (vs just `.sysdoc/cache/`)
3. AGENTS.md for project-level instructions
4. `create` command for document generation (Word/PDF)

**What already works:**
1. CLI is offline/deterministic ✓
2. SKILL.md is IA-agnostic ✓
3. Claude Code integration via `.claude/skills/` ✓
4. `prepare` extracts to cache ✓
5. `validate` + `render` are deterministic ✓

### Multi-Harness Integration Points

| Harness | Skill Location | Config | Invocation |
|---------|---------------|--------|------------|
| Claude Code | `.claude/skills/` | `.claude/settings.local.json` | `/sysdoc` |
| OpenCode | `.opencode/skills/` or `CLAUDE.md` | `opencode.json` | `/sysdoc` |
| Codex | `AGENTS.md` | `codex.json` | `sysdoc` |
| Antigravity | `AGENTS.md` | — | `sysdoc` |

### Commands to Implement/Refactor

| Command | Current State | Action Needed |
|---------|--------------|---------------|
| `/sysdoc status` | ✓ Works | No change |
| `/sysdoc init [pasta]` | ✓ Works | No change |
| `/sysdoc prepare [pasta]` | ✓ Works | Add MD output option |
| `/sysdoc analyze [pasta] [prompt]` | ✗ Missing | New: harness reads cache + LLM |
| `/sysdoc render [pasta]` | ✓ Works | No change |
| `/sysdoc deploy [pasta]` | ✓ Works | No change |
| `/sysdoc create [pasta] pdf/docx` | ✗ Missing | New: Phase 2 |
| `/sysdoc validate [pasta]` | ✓ Works | No change |

### Key Files to Modify

1. `sysdoc.py` — add `analyze` command, refactor `create` placeholder
2. `skills/sysdoc/SKILL.md` — update macro commands for new flow
3. `.claude/skills/sysdoc-analise/SKILL.md` — update trigger patterns
4. New: `AGENTS.md` — project-level instructions
5. New: `.opencode/skills/sysdoc-analise/SKILL.md` — OpenCode integration
6. New: `.sysdoc/config.yaml` support — per-project configuration

### Dependencies

- `pypdf>=4.0.0` — already in pyproject.toml
- `python-docx` — NOT in dependencies yet (needed for `create` in Phase 2)
- No new Python dependencies needed for Phase 1

### Risks

1. **Multi-harness skill format divergence** — each harness has different skill formats
2. **Breaking existing CLAUDE.md** — must maintain backward compatibility
3. **analyze command scope** — how much should CLI do vs harness? Keep CLI minimal.
