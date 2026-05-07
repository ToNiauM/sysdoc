# External Integrations

**Analysis Date:** 2026-05-07

## APIs & External Services

**LLM Providers:**
- OpenRouter - LLM API access for analysis
  - SDK/Client: `requests` (REST API)
  - Auth: `OPENROUTER_API_KEY` env var or `~/.sysdoc/config.json`
- OpenAI - LLM API access for analysis
  - SDK/Client: `requests` (REST API)
  - Auth: `OPENAI_API_KEY` env var or `~/.sysdoc/config.json`
- Google Gemini - LLM API access for analysis
  - SDK/Client: `requests` (REST API)
  - Auth: `GEMINI_API_KEY` env var or `~/.sysdoc/config.json`
- Anthropic - LLM API access for analysis
  - SDK/Client: `requests` (REST API)
  - Auth: `ANTHROPIC_API_KEY` env var or `~/.sysdoc/config.json`

**Document Extraction Tools:**
- pdftotext (poppler-utils) - Extract text from PDF files (`sysdoc prepare`)
- pandoc - Convert DOCX reference files to text (`sysdoc prepare`)

## Data Storage

**Databases:**
- None (file-based storage only)

**File Storage:**
- Local filesystem only (project directories store `dados_consolidados.json`, `.sysdoc/cache/` stores extracted texts and manifests)

**Caching:**
- Local filesystem (`.sysdoc/cache/` per project directory, stores `manifest.json`, `textos/*.txt`, `contexto_sysdoc.md`)

## Authentication & Identity

**Auth Provider:**
- Custom (API key-based authentication for LLM providers)
  - Implementation: API keys passed via `Authorization` headers in HTTP requests to LLM provider endpoints

## Monitoring & Observability

**Error Tracking:**
- None

**Logs:**
- No structured logging (uses `print()` statements for CLI output)

## CI/CD & Deployment

**Hosting:**
- VPS (deployment via `sysdoc deploy` using SCP to transfer HTML reports)

**CI Pipeline:**
- None

## Environment Configuration

**Required env vars:**
- `OPENROUTER_API_KEY` (optional, can use config.json)
- `OPENAI_API_KEY` (optional, can use config.json)
- `GEMINI_API_KEY` (optional, can use config.json)
- `ANTHROPIC_API_KEY` (optional, can use config.json)
- `SYSDOC_MAX_LLM_CONTEXT_CHARS` (optional, default: 700000)

**Secrets location:**
- `~/.sysdoc/config.json` (plain text JSON) or environment variables

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- LLM provider API endpoints (OpenRouter, OpenAI, Gemini, Anthropic)
- VPS SSH/SCP endpoint (for `sysdoc deploy`)

---

*Integration audit: 2026-05-07*
