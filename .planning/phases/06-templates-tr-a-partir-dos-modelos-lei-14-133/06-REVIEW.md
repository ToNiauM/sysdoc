---
phase: 06-templates-tr-a-partir-dos-modelos-lei-14-133
reviewed: 2026-08-27T04:55:24Z
depth: deep
files_reviewed: 12
files_reviewed_list:
  - sysdoc.py
  - sysdoc_docx/__init__.py
  - sysdoc_docx/corpo_dvi.py
  - templates/build_despacho_templates.py
  - tests/test_dvi_corpo.py
  - tests/test_dvi_render_raw.py
  - tests/test_dvi_create_variante.py
  - tests/test_dvi_despacho_e2e.py
  - tests/test_despacho_templates.py
  - tests/test_sigla_dvi.py
  - tests/test_cli.py
  - pyproject.toml
findings:
  critical: 3
  warning: 2
  info: 1
  total: 6
status: issues
---

# Phase 6 (Rodada 1 — Despacho de Verificação Inicial): Code Review Report

**Reviewed:** 2026-08-27T04:55:24Z
**Depth:** deep
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Scope: 26 commits, `90d8348..HEAD`, covering the new `raw_xml` injection channel in
`render_docx_template`, the `sysdoc_docx/corpo_dvi.py` despacho body builder, the
deterministic `templates/build_despacho_templates.py` generator, and the DVI
variant/precedence resolution logic (`resolver_tipo_verificacao`,
`selecionar_template_dvi`, `_e_semente_do_repo`, `seed_dvi_template`).

**The headline result of the priority security review is good news:** the
raw-XML injection channel itself is sound. I could not get JSON-derived data to
reach `word/document.xml` unescaped. Specifically I verified, with working
reproductions (not just code reading):

- A top-level JSON key literally named `corpo_apontamentos_xml`, and the same
  key nested one level down (`projeto.corpo_apontamentos_xml`), both fail to
  reach the raw channel — `render_docx_template` pops the colliding
  `values`-derived replacement before the second substitution pass runs, and
  the builder's own XML always wins. `RAW_XML_KEYS` is never consulted for
  `values`, exactly as documented.
- `sysdoc_docx/corpo_dvi.py::_paragrafo` is genuinely the only place JSON text
  becomes XML, and it escapes correctly. I fed it a payload designed to close
  `</w:t></w:r></w:p>` and open a forged `<w:sectPr>`/`<w:p>` — it came out
  fully entity-encoded and the resulting envelope still parsed as a single,
  intact paragraph.
- `w:pStyle` values are always one of the two module constants
  (`DviPecaTitulo`/`DviAlinea`); no code path lets JSON data reach a style
  attribute.
- The host-paragraph regex in `render_docx_template` cannot swallow a
  neighboring paragraph: the negative lookahead `(?!</w:p>)` blocks the lazy
  quantifier from crossing a `</w:p>` boundary, so if the placeholder isn't
  found before the first closing tag, the match attempt fails and `re.search`
  retries at the next `<w:p>`, i.e. it always resolves to the paragraph that
  actually contains the placeholder text. No catastrophic backtracking (no
  nested unbounded quantifiers, no alternation ambiguity — it's a bounded,
  single-negative-lookahead lazy scan, O(n) in the size of the template).

**What is not sound is the plumbing around that channel.** Three critical
defects were found, all independently reproduced against the real `sysdoc.py`
code (not hypothetical): (1) the raw-XML placeholder can be silently absent
from the target `.xml`, in which case the entire despacho body — every audit
finding — is dropped with `create()` still printing success; (2) the DVI
template-selection fallback can silently pick an unrelated `.docx` file out of
`referencias/` and label it "customizado" with no validation that it is a DVI
template at all; and (3) the second substitution pass (`values`) is a blind
global string replace that runs *after* the raw XML has been spliced in, so
`values` placeholder syntax occurring verbatim inside `parecer`/`fundamento`
text gets silently rewritten inside the already-injected, already-escaped
despacho content. Findings (1) and (2) compound: I reproduced an end-to-end
`sysdoc create <pasta> dvi` run that returns `rc == 0`, prints
`DOCX gerado: ...` and `Template DVI: .../referencias/norma_referencia.docx
(origem: projeto)`, and produces a despacho `.docx` containing **zero** of the
project's audit findings — the exact "silent fabrication/omission" failure
mode CLAUDE.md explicitly forbids, except here it's an omission, not an
invention, which is arguably worse for a document whose entire purpose is to
list what must be corrected.

I also assessed the one documented deviation the task asked me to evaluate
(`_chave_equivalencia` keying D-07 cross-references on `parecer` alone): the
false-positive risk is real and I reproduced it — two items with different
`documento`, `seção`, and `fundamento` but coincidentally identical `parecer`
boilerplate collapse into a cross-reference, and the second item's distinct
`fundamento` (i.e. its actual substantive finding) is discarded entirely and
replaced by "Vide apontamento...". This is flagged as Warning, not Critical,
because it was a measured, documented tradeoff against a real dataset
constraint — but the residual risk is larger than "against the real dataset it
worked", because nothing in the code guards against unrelated items sharing
generic phrasing.

All 561 existing tests pass; none of the findings below are caught by the
current suite (I confirmed this by running `python3 -m pytest tests/ -q`
before writing this review).

## Critical Issues

### CR-01: `create dvi` silently drops the entire despacho body when the template's raw-XML placeholder is missing, absent, or misnamed — reports success anyway

**File:** `sysdoc.py:1502-1533` (`render_docx_template`)

**Issue:** The raw-XML substitution loop only acts when the placeholder text
is found:

```python
if padrao.search(text):
    text = padrao.sub(_substituir_hospedeiro, text)
elif placeholder in text:
    raise SystemExit(...)
```

If the placeholder string `{{corpo_apontamentos_xml}}` is **absent from every
`word/*.xml` part** (neither found as a matched host paragraph nor as a bare
substring), neither branch fires. No error, no warning, no log line — the
`raw_xml["corpo_apontamentos_xml"]` payload built by
`build_corpo_despacho_xml(data)` (i.e. every risk/ajuste finding in the whole
analysis) is discarded, and `create()` proceeds to print `DOCX gerado: ...`
and return `0`.

I confirmed this is not a paper concern: the project's actual reference
template `processo-teste/referencias/dvi.docx` (the pre-Phase-6 "relatório"
format) has no `corpo_apontamentos_xml` placeholder at all. Any org template
that adopts the new despacho style but has a typo in the placeholder name, or
is missing that one paragraph because someone edited it out in Word, silently
produces a despacho with **no findings section**, while the CLI reports
success.

`.planning/phases/06-templates-tr-a-partir-dos-modelos-lei-14-133/06-05-SUMMARY.md`
explicitly states (Deviations section): *"Nenhum. O corpo do despacho é
montado inteiramente a partir de dado real ... campos institucionais ausentes
já viram marcador visível `[PREENCHER: <campo>]`, não um stub silencioso."*
That claim covers `despacho.*` fields (correctly, via `MARCADOR_DESPACHO`) but
does **not** hold for the raw-XML channel itself — there is no equivalent
"stub" or hard failure when the raw placeholder never gets substituted.

**Failure scenario (reproduced):**
```python
# template word/document.xml has {{despacho.vocativo}} but no
# {{corpo_apontamentos_xml}} anywhere
sysdoc.render_docx_template(
    "tpl_no_placeholder.docx", "out.docx",
    {"despacho.vocativo": "Senhor Fulano,"},
    raw_xml={"corpo_apontamentos_xml": "<w:p>...APONTAMENTO CRÍTICO...</w:p>"},
)
# -> no exception; out.docx contains ONLY "Senhor Fulano," — the entire
#    findings body is gone.
```

**Fix:** After the per-file substitution loop, assert that every key in
`brutos` was actually consumed at least once across the whole template
(track a "matched" flag per key, or diff `set(brutos) - matched_keys`), and
raise `SystemExit` listing the missing placeholder(s) if not. This turns a
silent, catastrophic content-loss into a loud, fixable template error —
consistent with the "never silently omit — fail loud or mark visibly" rule in
CLAUDE.md.

```python
encontrados: set[str] = set()
...
for chave, valor in brutos.items():
    ...
    if padrao.search(text):
        text = padrao.sub(_substituir_hospedeiro, text)
        encontrados.add(chave)
    elif placeholder in text:
        raise SystemExit(...)
...
faltantes = set(brutos) - encontrados
if faltantes:
    raise SystemExit(
        f"Placeholder(s) de raw_xml não encontrados no template: {sorted(faltantes)}."
    )
```

---

### CR-02: DVI template resolution can silently pick an unrelated `.docx` from `referencias/` and label it "template customizado do projeto"

**File:** `sysdoc.py:441-481` (`selecionar_template_dvi`), `sysdoc.py:1550-1604`
(`_select_reference_template`)

**Issue:** `selecionar_template_dvi` resolves step 2 of its precedence ladder
via:

```python
try:
    projeto_template = _select_reference_template(paths, "dvi", "", None)
except SystemExit:
    projeto_template = None
if projeto_template is not None and not _e_semente_do_repo(projeto_template):
    return projeto_template, "projeto"
```

`_select_reference_template`'s final fallback tier
(`candidatos_finais`, `sysdoc.py:1590-1604`) excludes only files whose
basename matches a reserved name belonging to a **different** `tipo` key in
`RESERVED_TEMPLATE_NAMES`. That dict currently has exactly one key, `"dvi"`.
When called with `tipo="dvi"`, the exclusion comprehension's guard
`if tipo_reservado != tipo_norm` is always false (the only key equals the
tipo being resolved), so the exclusion filter removes nothing — `candidatos_finais`
becomes **every** `.docx` file in `referencias/` (or `modelos/`), regardless
of name or content. `_select_reference_template` only raises `SystemExit`
when there are zero `.docx` files at all; any single `.docx` — a TR template,
a scanned law text kept as reference material, anything — is returned as if
it were the project's customized DVI template.

Because `_e_semente_do_repo` only rules out byte-identical copies of the two
shipped seeds, an unrelated file trivially passes as "customized" and
`selecionar_template_dvi` returns `(caminho, "projeto")` — `create()` then
prints `Template DVI: <path> (origem: projeto)`, actively asserting to the
operator that this unrelated file is the intentional institutional template.

**Failure scenario (reproduced end-to-end):** a project ran `sysdoc init`
(which seeds `referencias/dvi.docx`), the operator later deleted that seed
(or the project predates Phase 6 and never had it), and `referencias/`
contains one unrelated reference `.docx` (e.g. a law text kept for LLM
context). Running `sysdoc create <pasta> dvi`:

```
DOCX gerado: .../01_proj_dvi_2026-08-27.docx
Template DVI: .../referencias/norma_referencia.docx (origem: projeto)
```
`rc == 0`. The generated `.docx` is verbatim the unrelated reference file —
`{{corpo_apontamentos_xml}}` was never present, so **CR-01 fires silently at
the same time**, and the "audit finding" injected into the despacho vanishes
along with the rest of the despacho frame (title, vocative, observations,
signature block — none of it exists in the unrelated file either).

**Fix:** `selecionar_template_dvi`'s step 2 must not delegate to the generic,
maximally-permissive `_select_reference_template` fallback tier. Either (a)
restrict the "customized project template" candidate search to files whose
name matches the DVI-reserved set or contains `dvi` in the stem (mirroring
`seed_dvi_template`'s own detection logic at `sysdoc.py:486-489`, which
already does this correctly), or (b) require the candidate to actually contain
the literal string `{{corpo_apontamentos_xml}}` (or at minimum
`{{despacho.` — any despacho-shaped placeholder) before accepting it as a
"projeto" override, falling through to the repo `tipo` variant otherwise.
Either fix should raise/skip loudly rather than silently accept an arbitrary
file.

---

### CR-03: the second (`values`) substitution pass is a blind global string
replace that runs over content already injected via the raw-XML channel,
so literal placeholder syntax inside audit findings gets silently rewritten

**File:** `sysdoc.py:1523-1531` (`render_docx_template`)

**Issue:** Substitution order in `render_docx_template` is: (1) raw-XML host
paragraphs are replaced first, splicing `sysdoc_docx.corpo_dvi`'s output
(built from `parecer`/`fundamento`/`seção`, i.e. **LLM-produced JSON text**)
into `text`; (2) *then* `for placeholder, value in replacements.items():
text = text.replace(placeholder, value)` runs over the *entire* `text`
string, with no awareness of which spans came from step 1. `str.replace` has
no concept of "already-injected content is out of bounds" — it is a
whole-buffer, unconditional replace.

Consequence: if any `itens[].parecer` or `itens[].fundamento` string (data
that the priority-review brief explicitly calls "LLM-produced output and
therefore untrusted input") happens to contain the literal substring of any
`values` placeholder key used anywhere in the same template — e.g.
`{{despacho.vocativo}}`, `{{projeto.objeto}}`, `{{despacho.signatario}}`, or
any of the ~15+ other keys `flatten_json`/`create()` populates for the DVI
branch — that substring gets rewritten with the corresponding institutional
value **inside the already-escaped, already-placed despacho finding text**,
after the raw channel already committed it as "safe, final content".

**Reproduced:**
```python
# itens[0]["parecer"] = "O campo {{despacho.vocativo}} deveria ser revisado
#                         quanto ao subitem 4.20."
# despacho.vocativo (config) = "Senhora Coordenadora Administrativa,"
sysdoc.create(str(project), "dvi")
# resulting alínea text in the generated .docx:
# "a) 1: O campo Senhora Coordenadora Administrativa, deveria ser revisado
#  quanto ao subitem 4.20. fund"
```
The audit finding's literal text was altered without any error or trace. This
is not an arbitrary-code/XML-injection risk (the substituted value is still
escaped, so the document stays well-formed) — it is a content-integrity
defect: the "official" despacho text, which by design (D-06/D-08 in
`corpo_dvi.py`) must faithfully reproduce `parecer`+`fundamento` without
alteration, can be silently mutated by unrelated institutional data.

This is a low-probability-but-nonzero trigger (requires literal `{{...}}`
syntax matching an actual key name inside LLM-produced prose — plausible if
an ETP/TR itself quotes unresolved template markup, or if a future
`values` key name is short/generic enough to appear in normal legal prose),
but it directly contradicts the "channel separation" invariant the whole
Phase 6 threat model is built on: raw-injected content is supposed to be
final, not still subject to the values pass.

**Fix:** Make the two passes structurally non-overlapping. Simplest options:
(a) perform the raw-XML substitution *last*, after the `values` pass, so
injected content is never re-scanned; or (b) if raw-first ordering is
required for other reasons, protect injected spans (e.g. substitute a
one-shot sentinel token for each raw span, run the `values` pass, then
replace the sentinel with the real payload) so `values` replacement can never
reach inside content that already went through the raw channel.

## Warnings

### WR-01: D-07 cross-reference key (`parecer` alone) has a real, demonstrated false-positive collapse risk

**File:** `sysdoc_docx/corpo_dvi.py:90-107` (`_chave_equivalencia`)

**Issue:** This is the deviation already flagged and documented in
`06-02-SUMMARY.md`/`06-CONTEXT.md` D-07 (keying equivalence on `parecer`
alone because `parecer + fundamento` dropped a real cross-reference pair in
`processo-teste`). The task asked me to specifically assess the false-positive
risk, and it is real and reproducible, not merely theoretical:

```python
dados = {"itens": [
    {"documento": "ETP", "seção": "3.1", "classificação": "ajuste_necessário",
     "parecer": "Adequar a redação ao art. 18 da Lei 14.133/2021.",
     "fundamento": "Trata da fase de planejamento de compras."},
    {"documento": "TR", "seção": "9.9", "classificação": "risco",
     "parecer": "Adequar a redação ao art. 18 da Lei 14.133/2021.",
     "fundamento": "Trata de cláusula de reajuste de preços, tema totalmente distinto."},
]}
build_corpo_despacho_xml(dados)
# -> TR item's alínea text becomes:
#    'Vide apontamento constante na alínea "a" do item 1 do presente documento.'
# The TR item's actual finding — "cláusula de reajuste de preços" — never
# appears anywhere in the despacho.
```
Two genuinely distinct legal findings (different `documento`, different
`seção`, different `fundamento`, and in this example different `severidade`/
`risco_jurídico` too — one is `relevante`, the other `bloqueante`) collapse
into a single cross-reference because they share generic parecer boilerplate.
The second item's `bloqueante` risk finding is **entirely erased from the
despacho** and replaced by a pointer to an unrelated section.

Given that `parecer` text is model-generated and boilerplate legal phrasing
("Adequar a redação para atender à Lei nº 14.133/2021", "Corrigir o
dispositivo legal indicado", etc.) is exactly the kind of text an LLM is
likely to reuse across genuinely different findings, this is not an edge
case restricted to adversarial input — it's a plausible outcome of normal
analysis on real documents beyond the one dataset (`processo-teste`) this was
measured against.

**Fix:** Strengthen the equivalence key without regressing the ETP-016/TR-002
pair that motivated dropping `fundamento`. Candidates: (1) require *both*
`parecer` equality *and* `fundamento` textual similarity above a threshold
(e.g. normalized Jaccard/ratio on tokens) rather than exact equality, which
would likely still match ETP-016/TR-002 (same finding, peça name differs)
while rejecting the reajuste-vs-planejamento case above where the fundamento
content is topically unrelated; or (2) additionally require
`risco_jurídico`/`severidade` equality (a `bloqueante` finding should never be
silently absorbed into a cross-reference to a `relevante` one). At minimum,
document this residual risk in `06-CONTEXT.md` as an accepted known
limitation rather than "measured against the real dataset" (which reads as
validated, when it is only validated for false negatives, not false
positives).

### WR-02: `sysdoc create dvi` prints a template origin claim it cannot actually verify

**File:** `sysdoc.py:1678-1679` (`create`)

**Issue:** `print(f"Template DVI: {rel(template)} (origem: {origem})")` — the
`origem` value ("projeto"/"repo"/"argumento") is derived purely from
`selecionar_template_dvi`'s precedence ladder (see CR-02), which as shown can
attach `"projeto"` to a file that has no relationship to DVI at all. This is
a lower-severity restatement of CR-02 from the UX/observability angle: even
once CR-02 is fixed at the selection layer, consider having this print line
(or an equivalent check before rendering) verify the selected template
actually contains at least one `despacho.*` or `corpo_apontamentos_xml`
placeholder before claiming "origem: projeto" — so a wrong-template selection
degrades to a clear error message rather than a confidently-printed but false
provenance claim.

## Info

### IN-01: `templates/build_despacho_templates.py` emits a `<w:body>` with no `<w:sectPr>`

**File:** `templates/build_despacho_templates.py:161-168` (`_documento_xml`)

**Issue:** The generated `word/document.xml` has no `<w:sectPr>` (section
properties: page size, margins). This is optional per OOXML (Word applies
defaults), and all tests pass because they only inspect paragraph/style
content, so this is not a functional defect — just worth a deliberate note
since every other structural part of the minimal package (`[Content_Types].xml`,
rels, styles) was clearly built with care. If the two shipped templates are
meant to look presentable out of the box (not just be valid XML), consider
adding a `<w:sectPr>` with sane A4/Carta margins so the generated `.docx`
doesn't inherit Word's built-in default page geometry unpredictably.

---

_Reviewed: 2026-08-27T04:55:24Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
