# Codebase Concerns

**Analysis Date:** 2026-05-07

## Tech Debt

**Custom Template Engine (`templates/render_analise.py` lines 340-491):**
- Issue: Implements a mini Jinja2-like template engine with `{{ var }}`, `{% for %}`, `{% if %}` syntax without using established libraries
- Files: `templates/render_analise.py`
- Impact: Custom implementation lacks features, may have edge-case bugs, harder to maintain than using Jinja2 or similar
- Fix approach: Consider migrating to Jinja2 for maintainability, or extensively document the custom engine's limitations

**Missing `analyze()` Function Implementation:**
- Issue: ROADMAP.md references `analyze()` function in `sysdoc.py` (lines 105, 116, 553 in ROADMAP) but the function is not present in the current `sysdoc.py`
- Files: `sysdoc.py`, `ROADMAP.md`
- Impact: The core LLM analysis workflow may be incomplete or was moved/renamed
- Fix approach: Verify if analyze functionality exists elsewhere or needs implementation; update ROADMAP to reflect actual state

**Incomplete OMISSION Pattern Support (M2-C):**
- Issue: `[OMISSÃO]` marker support in validator is incomplete - ROADMAP shows task unchecked
- Files: `templates/validate_sysdoc.py` (line 288), `skills/sysdoc/SKILL.md`
- Impact: When LLM documents absence of clauses, the `de` field lacks proper formatting guidance
- Fix approach: Implement per ROADMAP M2-C: document format `[OMISSÃO: descrição]` in SKILL.md and improve regex in validator

## Known Bugs

**No Known Runtime Bugs Identified:**
- The codebase appears stable for its core functions (prepare, validate, render, publish)
- Error handling uses try/except blocks in `sysdoc.py` (lines 132-135, 481-489, 496-500)
- Tests in `tests/test_validate.py` cover core validation scenarios

## Security Considerations

**Hardcoded SSH Server Credentials:**
- Risk: Server IP address and username hardcoded in deploy function
- Files: `sysdoc.py` (lines 478, 492-493)
- Current mitigation: None - credentials are embedded in source code
- Recommendations:
  - Move server details to `~/.sysdoc/config.json` or environment variables
  - Line 478: `"ssh", "root@76.13.170.15"` should read from config
  - Line 492: `target_path = f"root@76.13.170.15:/opt/web/cfc-analise/html/{target_name}"` should be configurable
  - Consider using SSH config or deployment config file

**API Key Management:**
- Risk: LLM API keys stored in `~/.sysdoc/config.json` (line 41, `sysdoc.py`)
- Files: `sysdoc.py` (line 41), `CONFIG_FILE = Path.home() / ".sysdoc" / "config.json"`
- Current mitigation: Keys stored in user home directory, not committed to repo
- Recommendations: Ensure config.json is in `.gitignore`; consider encrypting sensitive values

## Performance Bottlenecks

**PDF Text Extraction Memory Usage:**
- Problem: `extract_pdf()` in `sysdoc.py` (lines 131-147) reads entire PDF into memory
- Files: `sysdoc.py` (lines 131-147)
- Cause: `pypdf.PdfReader` loads full document; for large PDFs this could be heavy
- Improvement path: Process pages sequentially if memory becomes an issue; current approach is acceptable for typical ETP/TR document sizes

**Traceability Validation Complexity:**
- Problem: `is_traceable()` in `templates/validate_sysdoc.py` (lines 281-303) does multiple passes over text
- Files: `templates/validate_sysdoc.py` (lines 281-303)
- Cause: Token normalization, stopword removal, and sliding window matching are O(n²) in worst case
- Improvement path: For large documents, consider indexing source tokens once; current approach works for typical document sizes

**Custom Template Rendering:**
- Problem: `render_template()` in `templates/render_analise.py` (lines 340-418) processes templates line-by-line
- Files: `templates/render_analise.py`
- Cause: Custom implementation without optimization
- Improvement path: If template rendering becomes slow for large HTML, consider pre-compiling templates or using Jinja2

## Fragile Areas

**Deploy Function Error Handling:**
- Files: `sysdoc.py` (lines 465-502)
- Why fragile: Basic SSH/SCP operations with minimal error recovery
- Safe modification: Always test deploy to staging first; wrap SSH commands with more robust error checking and rollback
- Test coverage: No automated tests for deploy functionality

**PDF Extraction Reliability:**
- Files: `sysdoc.py` (lines 131-147 for PDF, 150-168 for DOCX)
- Why fragile: Depends on `pypdf` which may fail on malformed or scanned PDFs
- Safe modification: The code has basic detection for short text (line 143-146) but could be enhanced with OCR fallback
- Test coverage: Basic tests needed for various PDF formats

**Dynamic LLM Provider Routing:**
- Files: `sysdoc.py` (referenced in ROADMAP lines 126-144 for `call_openrouter_json`)
- Why fragile: Provider detection and JSON schema mode selection based on model name patterns
- Safe modification: Add more robust provider detection; validate response format before processing
- Test coverage: No tests visible for LLM integration functions

## Scaling Limits

**Single-Project CLI Operations:**
- Current capacity: CLI operates on one project at a time
- Limit: No batch operations across multiple projects
- Scaling path: Add batch flags or project glob patterns; ROADMAP M3-C (`sysdoc compare`) is implemented but only for comparison, not batch operations

**In-Memory JSON Processing:**
- Current capacity: Entire `dados_consolidados.json` loaded into memory
- Limit: For extremely large analyses (hundreds of items), memory usage could be high
- Scaling path: Stream processing if needed; current approach fine for typical use

**No Parallel Processing:**
- Current capacity: Operations are sequential (prepare → analyze → validate → render)
- Limit: Large projects with many reference files processed one at a time
- Scaling path: Consider parallel reference file extraction; low priority given typical project sizes

## Dependencies at Risk

**pypdf (PDF Processing):**
- Risk: Relatively new fork/continuation of PyPDF2
- Impact: If pypdf development stalls, PDF extraction could break
- Migration plan: The codebase already migrated from PyPDF2 to pypdf (M1-A completed per ROADMAP); monitor project health on PyPI

## Missing Critical Features

**GitHub Actions CI (M5-A):**
- Problem: No continuous integration configured
- Blocks: Automated testing on PRs, deployment automation
- Files needed: `.github/workflows/ci.yml`
- Priority: Medium (per ROADMAP)

**PyPI Publication Workflow (M5-B):**
- Problem: Not publishable via `pip install sysdoc`
- Blocks: Easy installation for users
- Files needed: `.github/workflows/publish.yml`
- Priority: Low (per ROADMAP)

**Test Coverage for Preparation Functions (M4-A):**
- Problem: `tests/test_prepare.py` does not exist
- Blocks: Ensuring `detect_values()`, `detect_object()`, `render_context()` work correctly
- Files needed: `tests/test_prepare.py`
- Priority: High (per ROADMAP)

## Test Coverage Gaps

**Preparation Functions:**
- What's not tested: `detect_values()`, `detect_object()`, `render_context()`, `detect_process()`, `detect_sections()`, `snippets_for_term()`
- Files: `sysdoc.py` (lines 221-346)
- Risk: Text detection and context generation could silently break
- Priority: High - these functions are critical for LLM context preparation

**AI Harness Skill Wrappers:**
- What's not tested: `.claude/skills/sysdoc-analise/SKILL.md`, `.opencode/skills/sysdoc-analise/SKILL.md`
- Risk: wrappers may drift from canonical `skills/sysdoc/SKILL.md`
- Priority: Low — they are thin pointers; manual review on changes is sufficient

**Deploy Functionality:**
- What's not tested: SSH/SCP deploy operations
- Files: `sysdoc.py` (lines 465-502)
- Risk: Deploy could fail silently or break remote server
- Priority: Medium - needs integration tests with test server

**LLM Integration:**
- What's not tested: API calls to OpenRouter, OpenAI, Gemini, Anthropic
- Files: Referenced in ROADMAP but functions not visible in current `sysdoc.py`
- Risk: Provider API changes could break analysis workflow
- Priority: High - mocking and integration tests needed

---

*Concerns audit: 2026-05-07*
