---
phase: 2
slug: comando-create-word-pdf
status: open
threats_open: 1
asvs_level: 1
created: 2026-05-12
---

# Phase 2 — Security: comando-create-word-pdf

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Project filesystem | `dados_consolidados.json` and ETP/TR source texts are read from the local project folder; generated DOCX is written to the same folder. | JSON analysis data, extracted ETP text, Word template bytes |
| CLI stdout | `create()` prints generated file path and pending substitution count to stdout (consumed by user and harness). | File path strings, integer count |
| DOCX XML layer | Placeholder substitution operates directly on ZIP/XML bytes of the Word template. | Template content, JSON field values, revised ETP text |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-01 | Tampering | ETP substitution (`apply_etp_revisions`) | mitigate | Exact substring check (`before in revised`) + single-replacement (`replace(before, after, 1)`); fuzzy match explicitly rejected; items not found go to pending list | closed |
| T-02 | Integrity | TR DOCX output — pending placeholders | mitigate | `build_pending_text` renders unmatched items with their IDs; result placed into `values["substituicoes_pendentes"]` and written into DOCX XML; count printed on stdout | closed |
| T-03 | Data Loss | TR DOCX output — file overwrite | mitigate | `resolve_next_docx_output` checks `candidate.exists()` and bumps `_2`, `_3`, ... suffix before returning any path | closed |
| T-04 | Repudiation / Misinformation | TR DOCX output — messaging | mitigate | **OPEN** — declared messaging absent from all required locations | open |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Open Threat Detail

### T-04 — Repudiation / Misinformation (BLOCKER)

**Required mitigation (from PLAN.md):** README.md, AGENTS.md, skills/sysdoc/SKILL.md, and the CLI output printed by `create()` must declare that the generated `.docx` is a base for human editing — not a final official document.

**Verification performed:** Full-text grep for phrases `"base para edição"`, `"edição humana"`, `"não.*final"`, `"final.*oficial"`, `"rascunho"`, and `"human edit"` across all four required locations.

**Results:**

| Location | Required wording | Found |
|----------|-----------------|-------|
| `sysdoc.py` — `create()` stdout (lines 1109–1111) | disclaimer after DOCX generation | No match |
| `README.md` — `sysdoc create` description (lines 195–198, 240) | "base para edição humana" or equivalent | No match |
| `AGENTS.md` — macro 6, `/sysdoc create` (line 40–41) | "base para edição humana" or equivalent | No match |
| `skills/sysdoc/SKILL.md` — `/sysdoc create` section (lines 37–41) | "base para edição humana" or equivalent | No match |

The `create()` function prints only `"DOCX gerado: {path}"` (sysdoc.py:1109) with an optional substitution count line. None of the four user-facing surfaces contain any statement that the output is a draft for human editing, not a final official document. The threat (creating false impression of official document) is therefore unmitigated.

---

## Closed Threat Detail

### T-01 — Tampering: exact substitution strategy

**Evidence:** `sysdoc.py:940–950` — `apply_etp_revisions` uses `before in revised` (exact substring lookup, no fuzzy/regex) followed by `revised.replace(before, after, 1)` (first occurrence only). Items where `before` is absent, empty, or `after` is empty skip substitution and append to `pending`. The `applicable_etp_items` filter (sysdoc.py:931–937) also excludes omission markers via `is_omission_marker` (sysdoc.py:927–928).

Tests confirming the not-found/pending path: `tests/test_cli.py:396–443` (`test_create_tr_reports_pending_substitution`) and `tests/test_cli.py:445–488` (`test_create_tr_ignores_omission_markers`).

**Deviation note:** Implementation uses ZIP/XML replacement instead of `python-docx`. The intent of T-01 (no fuzzy match on the ETP text layer) is fully met by the string-level `apply_etp_revisions` helper, which operates before any DOCX rendering. Disposition: CLOSED.

### T-02 — Integrity: pending-substitution section in DOCX

**Evidence:** `sysdoc.py:953–959` — `build_pending_text` returns `"Nenhuma substituição pendente."` when the list is empty, or a line per unmatched item formatted as `"{id}: trecho original não localizado para substituição exata."`. At `sysdoc.py:1096`, `values["substituicoes_pendentes"]` is populated from this function. At `sysdoc.py:999–1012`, `render_docx_template` replaces `{{substituicoes_pendentes}}` inside the DOCX XML. CLI also prints `"Substituições pendentes: {count}"` (sysdoc.py:1111).

Test: `tests/test_cli.py:396–443` verifies that the DOCX XML contains `"ETP-001"` (item ID) when the `de` text is not found in the ETP, and that stdout contains `"Substituições pendentes: 1"`. Disposition: CLOSED.

### T-03 — Data Loss: auto-increment naming

**Evidence:** `sysdoc.py:962–972` — `resolve_next_docx_output` constructs `stem = f"{prefix}_{model}_{date}"`, checks `candidate.exists()`, and returns `candidate` if free. Otherwise loops with `index = 2, 3, ...` until a free name is found. Called at `sysdoc.py:1107` inside `create()`.

**Note on test coverage:** No test exercises the `_2`/`_3` collision branch directly. This is a test coverage gap (quality issue) but the code path implementing the mitigation is present and correct. Disposition: CLOSED.

---

## Accepted Risks Log

No accepted risks.

---

## Unregistered Flags

The SUMMARY.md for phase 02-01 does not contain a `## Threat Flags` section. No new unregistered attack surface was flagged by the executor.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-12 | 4 | 3 | 1 | gsd-security-auditor (claude-sonnet-4-6) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log (none)
- [ ] `threats_open: 0` confirmed — **1 threat open (T-04)**
- [ ] `status: verified` set in frontmatter — **blocked by T-04**

**Approval:** pending — blocked by T-04 (Repudiation / Misinformation)
