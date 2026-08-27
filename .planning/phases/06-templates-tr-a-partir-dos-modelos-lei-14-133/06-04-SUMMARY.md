---
phase: 06-templates-tr-a-partir-dos-modelos-lei-14-133
plan: 04
subsystem: infra
tags: [docx, xml-escaping, security, config-yaml, zipfile]

requires:
  - phase: 06-01
    provides: templates/dvi/despacho_geral.docx e despacho_tic.docx com placeholder raw único {{corpo_apontamentos_xml}}
  - phase: 06-02
    provides: sysdoc_docx/corpo_dvi.py — builder que emite XML de parágrafo para o canal raw
provides:
  - "render_docx_template(template, output, values, raw_xml=None) com canal raw_xml estruturalmente separado de values"
  - "RAW_XML_KEYS allowlist fechada (defesa em profundidade sobre o canal já separado)"
  - "valores_despacho(config) — resolução dos sete campos institucionais do despacho a partir de .sysdoc/config.yaml, com marcador [PREENCHER: <campo>] quando ausente"
  - "init_config semeia tipo: e despacho: {sete campos vazios}"
affects: ["06-05 (call site de create() dvi passa a usar raw_xml e valores_despacho)"]

tech-stack:
  added: []
  patterns:
    - "Canal de dado confiável separado por parâmetro de função, não por allowlist de nome de chave sobre dado não confiável"
    - "Validação de bem-formação de XML via envelope + xml.etree.ElementTree antes de abrir qualquer ZIP de saída"
    - "Substituição de parágrafo hospedeiro via regex ancorado em <w:p>...</w:p>, com checagem de que o placeholder é o único conteúdo textual do parágrafo"

key-files:
  created:
    - tests/test_dvi_render_raw.py
  modified:
    - sysdoc.py
    - tests/test_cli.py

key-decisions:
  - "XML cru só entra pelo parâmetro raw_xml, nunca por nome de chave em values — elimina por construção o vetor de chave homônima vinda do dados_consolidados.json (T-06-04-02)"
  - "RAW_XML_KEYS permanece como allowlist fechada de uma única chave, mas só é consultada em _validar_chave_raw — nunca no corpo de render_docx_template, travado por teste de introspecção de código-fonte"
  - "Campos institucionais do despacho vêm exclusivamente de .sysdoc/config.yaml bloco despacho:, nunca do JSON — campo ausente vira marcador visível [PREENCHER: <campo>], nunca inventado"

patterns-established:
  - "Pattern: canal de injeção XML cru como parâmetro dedicado (raw_xml), não como exceção de nome de chave — reutilizável para qualquer futuro builder de XML injetado em render_docx_template"

requirements-completed: [SYSD-17]

duration: 45min
completed: 2026-08-27
---

# Phase 6 Plan 04: Canal raw_xml separado e origem dos campos institucionais Summary

**`render_docx_template` ganha parâmetro `raw_xml` estruturalmente separado de `values` (fechando por construção o vetor de chave homônima do JSON), e `.sysdoc/config.yaml` ganha um bloco `despacho:` que alimenta `valores_despacho()` com marcador `[PREENCHER: <campo>]` para dado institucional ausente.**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-08-27
- **Tasks:** 3/3
- **Files modified:** 3 (1 criado, 2 modificados)

## Accomplishments
- `render_docx_template(template, output, values, raw_xml=None)` — `values` é escapado integralmente, sem nenhuma exceção por nome de chave; `raw_xml` é o único canal para XML cru, validado contra `RAW_XML_KEYS` e contra bem-formação (`ElementTree.fromstring` sobre envelope `w:body`) antes de abrir qualquer ZIP.
- Substituição por parágrafo hospedeiro: o placeholder `_xml` precisa ser o único conteúdo textual do seu `<w:p>`; caso contrário, `SystemExit` explícito.
- `valores_despacho(config)` resolve os sete campos institucionais (`vocativo`, `unidade`, `destinatario`, `signatario`, `cargo_signatario`, `autoridade`, `cargo_autoridade`) só a partir do config, nunca do JSON; `init_config` agora semeia `tipo: ""` e `despacho: {7 campos vazios}`.
- 17 novos testes em `tests/test_dvi_render_raw.py` provam, isoladamente (sem depender de `create()` nem de outra wave), que uma chave de `values` homônima a `corpo_apontamentos_xml` sai sempre escapada — inclusive quando `raw_xml` também está presente, caso em que o canal cru vence a colisão de nome.

## Task Commits

Each task was committed atomically:

1. **Task 1: Canal raw_xml separado em render_docx_template** - `d08a8e7` (feat)
2. **Task 2: Bloco despacho: no config e resolução dos campos institucionais** - `4bb74d0` (feat)
3. **Task 3: Suíte de segurança do canal raw** - `8bd44b2` (test)

_Note: nenhuma task usou TDD explícito (`tdd="true"` não declarado no plano); Task 3 foi validada com testes de mutação manuais (remover `_validar_chave_raw`/`_validar_xml_bruto` faz os testes correspondentes falharem, revertido em seguida) antes do commit._

## Files Created/Modified
- `sysdoc.py` — `RAW_XML_SUFFIX`, `RAW_XML_KEYS`, `_RAW_XML_ENVELOPE`, `_validar_chave_raw`, `_validar_xml_bruto`, `render_docx_template` reescrito com `raw_xml`; `CAMPOS_DESPACHO`, `MARCADOR_DESPACHO`, `valores_despacho`; `init_config` semeando `tipo`/`despacho`.
- `tests/test_cli.py` — `test_config_yaml_format` estendido para `tipo`/`despacho`; nova classe `TestValoresDespacho` (5 testes).
- `tests/test_dvi_render_raw.py` — novo arquivo, 17 testes em 5 classes (`TestCanalSeparado`, `TestAllowlist`, `TestEscapeDeCamposDoJson`, `TestValidacaoDoXmlBruto`, `TestNaoRegressao`).

## Decisions Made
- Nenhum desvio de escopo do plano: a decisão de canal separado (revisão do checker, D-09) já estava fixada no plano e foi implementada literalmente, incluindo o teste de introspecção que impede reintrodução de comparação por nome de chave (`RAW_XML_KEYS` não pode aparecer em `inspect.getsource(render_docx_template)`).
- Ajuste de implementação sobre a especificação literal do plano: a substituição do parágrafo hospedeiro adicionou uma checagem de que o `<w:t>` do parágrafo casado é **exatamente** o placeholder (não apenas "contém"), porque o regex ancorado em `<w:p>...</w:p>` sozinho, como descrito na `<action>`, casa qualquer parágrafo que contenha o placeholder em qualquer posição — inclusive misturado a outro texto no mesmo `<w:t>` — o que violaria o critério de aceite "placeholder misturado a outro texto levanta SystemExit". Essa checagem adicional é necessária para cumprir literalmente o próprio critério de aceite do plano; nenhum comportamento de D-09 foi alterado.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Regex de parágrafo hospedeiro precisava validar isolamento do placeholder, não só presença**
- **Found during:** Task 1 (verificação do critério de aceite "placeholder misturado a outro texto levanta SystemExit")
- **Issue:** O regex `<w:p\b[^>]*>...{{chave}}...</w:p>` especificado na `<action>` casa qualquer `<w:p>` que contenha o placeholder em qualquer posição, inclusive com texto adicional no mesmo `<w:t>` — o teste manual de aceite (`texto {{corpo_apontamentos_xml}} texto` no mesmo parágrafo) não levantava `SystemExit` como exigido.
- **Fix:** Adicionado passo de verificação, dentro do callback de substituição, que soma todo texto visível (`<w:t>...</w:t>`) do parágrafo casado e confirma que é exatamente igual ao placeholder antes de substituir; caso contrário, levanta `SystemExit` com a mesma mensagem sobre parágrafo hospedeiro.
- **Files modified:** `sysdoc.py`
- **Verification:** Testado manualmente com os 6 cenários dos critérios de aceite da Task 1 e via `tests/test_dvi_render_raw.py::TestValidacaoDoXmlBruto::test_placeholder_nao_isolado_levanta_systemexit`.
- **Committed in:** `d08a8e7` (parte do commit da Task 1)

---

**Total deviations:** 1 auto-fixed (1 bug — Rule 1)
**Impact on plan:** Necessário para cumprir literalmente o critério de aceite da Task 1; não altera nenhuma garantia de segurança de D-09, apenas fecha uma lacuna do regex especificado.

## Issues Encountered
- `ruff check sysdoc.py` reporta 3 erros pré-existentes e não relacionados a este plano (`time` e `urllib.request` importados sem uso, bloco de import desordenado) — confirmado via `git stash` que já existiam antes deste plano; fora de escopo (SCOPE BOUNDARY), não corrigidos.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `render_docx_template` está pronto para o Plano 05 injetar `raw_xml={"corpo_apontamentos_xml": build_corpo_despacho_xml(dados)}` e `values` com `valores_despacho(load_config(paths))` no ramo `dvi` de `create()` — nenhuma mudança de assinatura será necessária, o call site de `sysdoc.py:1415` (agora deslocado pelas novas linhas) segue compatível com três argumentos posicionais.
- Nenhum bloqueio identificado. `sysdoc-dvi` (motor que chama modelo) não foi tocado nesta rodada.

---
*Phase: 06-templates-tr-a-partir-dos-modelos-lei-14-133*
*Completed: 2026-08-27*

## Self-Check: PASSED

- FOUND: sysdoc.py
- FOUND: tests/test_cli.py
- FOUND: tests/test_dvi_render_raw.py
- FOUND: .planning/phases/06-templates-tr-a-partir-dos-modelos-lei-14-133/06-04-SUMMARY.md
- FOUND commit: d08a8e7
- FOUND commit: 4bb74d0
- FOUND commit: 8bd44b2
