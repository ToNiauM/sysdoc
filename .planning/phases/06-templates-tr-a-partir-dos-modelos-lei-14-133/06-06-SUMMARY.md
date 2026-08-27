---
phase: 06-templates-tr-a-partir-dos-modelos-lei-14-133
plan: 06
subsystem: docx-generation
tags: [docx, dvi, despacho, e2e, documentation, changelog]

requires:
  - phase: 06-01
    provides: "templates/dvi/despacho_geral.docx e despacho_tic.docx"
  - phase: 06-02
    provides: "sysdoc_docx.corpo_dvi.build_corpo_despacho_xml"
  - phase: 06-04
    provides: "render_docx_template(..., raw_xml=...) e valores_despacho(config)"
  - phase: 06-05
    provides: "sysdoc create <pasta> dvi ligado ao builder real, por tipo, via canal raw_xml"
provides:
  - "tests/test_dvi_despacho_e2e.py — E2E sobre processo-teste (49 itens reais) provando as duas variantes, override do projeto e ausência de {{ remanescente"
  - "processo-teste/.sysdoc/config.yaml com tipo: geral e bloco despacho: (não versionado)"
  - "CHANGELOG/README/SKILL.md/AGENTS.md descrevendo a Rodada 1 como entregue"
  - "correção de bug em sysdoc_docx/corpo_dvi.py: seção de pendências agora é numerada no XML renderizado"
affects: ["06-07"]

tech-stack:
  added: []
  patterns:
    - "E2E isolado por shutil.copytree em tmp_path, nunca escrevendo no projeto real do usuário"
    - "Numeração de seção resolvida só no ponto de renderização (_titulo_numerado), preservando o campo titulo de montar_apontamentos() intacto para os testes unitários que já comparam esse campo sem número"

key-files:
  created:
    - tests/test_dvi_despacho_e2e.py
  modified:
    - sysdoc_docx/corpo_dvi.py
    - processo-teste/.sysdoc/config.yaml (não versionado, ver Deviations)
    - CHANGELOG.md
    - README.md
    - skills/sysdoc/SKILL.md
    - AGENTS.md

key-decisions:
  - "Cópia de teste ignora referencias/dvi.docx (via padrão *.docx do shutil.ignore_patterns), porque o arquivo hoje presente em processo-teste/referencias/ é um DOCX no formato relatório legado (título 'DOCUMENTO DE VERIFICAÇÃO INICIAL — DVI', placeholders {{tabela_itens}}) gerado antes desta fase — sem ignorá-lo, a precedência do projeto (D-14) faria os testes de variante geral/tic renderizarem o formato errado"
  - "TestDespachoTic.test_variante_tic_via_config remove explicitamente referencias/dvi.docx mesmo já estando ausente por causa do ignore acima, para deixar a intenção literal do plano visível no teste"

requirements-completed: [SYSD-18]

duration: 55min
completed: 2026-08-27
---

# Phase 6 Plan 06: E2E do despacho sobre o processo real + documentação da Rodada 1 Summary

**`tests/test_dvi_despacho_e2e.py` prova, sobre o processo real de 49 itens em `processo-teste/`, que `sysdoc create <pasta> dvi` produz o despacho institucional completo — geral e TIC, com override de template do projeto — sem nenhum `{{` remanescente; um bug real na numeração da seção de pendências foi encontrado e corrigido no caminho; CHANGELOG, README, SKILL.md e AGENTS.md agora descrevem a Rodada 1 como entregue.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-08-27T04:30:00Z (herdado do fim do Plano 05)
- **Completed:** 2026-08-27T05:25:00Z
- **Tasks:** 2/2
- **Files modified:** 7 (1 criado rastreado, 1 corrigido, 4 documentação, 1 edição não rastreada em `processo-teste/`)

## Accomplishments
- `tests/test_dvi_despacho_e2e.py` — 13 testes em 4 classes (`TestDespachoGeral`, `TestDespachoTic`, `TestOverrideDoProjeto`, `TestNomeDoArtefato`), todos rodando sobre uma cópia isolada (`shutil.copytree` em `tmp_path`) do `processo-teste/dados_consolidados.json` real (24 `conforme`, 14 `pendente`, 7 `ajuste_necessário`, 4 `risco`), com `skipif` de módulo quando o projeto não existe no checkout.
- Confirmado sobre o dataset real: 3 seções (5, 6 e 14 alíneas — ETP, TR, Pendências), exatamente 2 referências cruzadas automáticas, os 24 itens `conforme` nunca aparecem no XML, nenhum `(SEI` nem `não informado` vaza no cabeçalho (porque `secao_etp.numero`/`secao_tr.numero` valem `"não informado"`), os três marcadores `[PREENCHER: <campo>]` aparecem para os campos institucionais vazios, e `DELIC`/`À COLOG` aparecem para os campos preenchidos.
- **Bug real encontrado e corrigido (Rule 1):** `build_corpo_despacho_xml` (Plano 02) não numerava o título da seção de pendências no XML final — produzia `"PENDÊNCIAS DE DOCUMENTAÇÃO"` em vez de `"3) PENDÊNCIAS DE DOCUMENTAÇÃO"`, divergindo do modelo institucional real (`processo-teste/referencias/dvi.md`: `"3) CRONOGRAMA FÍSICO-FINANCEIRO:"`) e do critério de aceite explícito desta rodada (`test_tres_secoes_numeradas`). Corrigido com `_titulo_numerado()`, aplicado só no ponto de renderização — o campo `titulo` devolvido por `montar_apontamentos()` continua sem número, preservando os testes unitários de `tests/test_dvi_corpo.py` que comparam esse campo literalmente (`secoes[-1]["titulo"] == TITULO_PENDENCIAS`).
- `processo-teste/.sysdoc/config.yaml` recebeu `tipo: geral` e o bloco `despacho:` com `unidade: DELIC` e `destinatario` preenchidos (dados estruturais do fluxo, presentes no modelo real) e os cinco campos de nome de pessoa (`vocativo`, `signatario`, `cargo_signatario`, `autoridade`, `cargo_autoridade`) deixados vazios de propósito — o E2E prova o marcador `[PREENCHER: ...]`, nunca um nome real, mitigando T-06-06-02.
- CHANGELOG.md, README.md, `skills/sysdoc/SKILL.md` e AGENTS.md documentam o bloco `despacho:`, a chave `tipo`, a precedência de template e o canal `raw_xml`/`RAW_XML_KEYS` — a Rodada 1 está descrita como entregue nos quatro documentos operacionais.

## Task Commits

1. **Task 1: Preparar processo-teste e escrever o E2E** - `f800b0e` (test)
2. **Task 2: Documentação operacional e CHANGELOG da Rodada 1** - `4c4fa9b` (docs)

**Plan metadata:** commit deste SUMMARY (a seguir)

## Files Created/Modified
- `tests/test_dvi_despacho_e2e.py` (novo) — 13 testes: `TestDespachoGeral` (9), `TestDespachoTic` (2), `TestOverrideDoProjeto` (1), `TestNomeDoArtefato` (1); helpers `_copiar_projeto`, `_definir_tipo`, `_rodar_create`, `_document_xml`, `_texto_do_docx`.
- `sysdoc_docx/corpo_dvi.py` — nova função privada `_titulo_numerado(secao)`, usada por `build_corpo_despacho_xml` para garantir `"{numero}) "` no título de toda seção renderizada (peças já o tinham via `_cabecalho_peca`; pendências não tinha).
- `processo-teste/.sysdoc/config.yaml` — **não versionado** (ver Deviations). `tipo: geral` acrescentado; bloco `despacho:` acrescentado com `unidade`/`destinatario` preenchidos e os cinco campos de pessoa vazios; bloco `pecas:` preexistente preservado intacto.
- `CHANGELOG.md` — entrada `**Rodada 1 da Phase 6 — template do Despacho de Verificação Inicial**` sob `[Não publicado]` > `Adicionado`.
- `skills/sysdoc/SKILL.md` — bullet de `/sysdoc create [pasta] [tipo]` expandido para `tipo=dvi`, com exemplo do bloco `despacho:`.
- `AGENTS.md` — seção "Template do despacho DVI", regra do marcador `[PREENCHER: <campo>]`, e `.sysdoc/config.yaml` no diagrama de estrutura atualizado com `tipo`/`despacho:`.
- `README.md` — subseção "Template do despacho e configuração institucional" na seção do motor DVI.

## Decisions Made
- A cópia de teste do E2E exclui `referencias/dvi.docx` via `shutil.ignore_patterns("output", "cache", "*.docx")` — não só os artefatos `.docx` na raiz do projeto (`01_processo-teste_dvi_2026-08-26.docx`, `02_...`), mas também `referencias/dvi.docx`, que hoje é um DOCX real gerado por uma execução anterior do formato relatório legado (`{{tabela_itens}}`, título "DOCUMENTO DE VERIFICAÇÃO INICIAL — DVI"), não a nova moldura de despacho. Sem excluí-lo, a regra de precedência do projeto (D-14) faria `selecionar_template_dvi` escolher esse arquivo como "customizado" em toda execução — inclusive nos testes de variante `geral`/`tic`, que ficariam sempre testando o formato errado. Medido e confirmado por hash SHA-256 (o arquivo do projeto não é byte-idêntico a nenhuma semente do repo).
- `TestDespachoTic.test_variante_tic_via_config` mantém a chamada explícita `unlink(missing_ok=True)` em `referencias/dvi.docx` mesmo já estando ausente por causa do ignore acima — redundante na prática, mas deixa a intenção do teste (forçar o template do repo) literal e legível, como pedido pelo texto do plano.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Seção de pendências sem número no XML renderizado**
- **Found during:** Task 1, ao escrever `test_tres_secoes_numeradas` contra o dataset real
- **Issue:** `build_corpo_despacho_xml` (herdado do Plano 02) emitia `secao["titulo"]` diretamente. Seções por peça já carregam o número embutido no `titulo` (via `_cabecalho_peca`, ex.: `"1) ESTUDO TÉCNICO PRELIMINAR - ETP"`), mas a seção de pendências guarda apenas `TITULO_PENDENCIAS = "PENDÊNCIAS DE DOCUMENTAÇÃO"`, sem número — decisão original do Plano 02 para não acoplar `montar_apontamentos()` a uma posição de renderização (`tests/test_dvi_corpo.py::test_pendencias_viram_secao_propria_ao_final` compara esse campo com igualdade estrita, sem número). O efeito colateral não intencional: o DOCX final também saía sem número na seção de pendências, contrariando D-05 ("seções... renumeradas 1), 2), 3)") e o modelo institucional real (`processo-teste/referencias/dvi.md`: `"3) CRONOGRAMA FÍSICO-FINANCEIRO:"`), além do critério de aceite explícito desta rodada.
- **Fix:** Nova função `_titulo_numerado(secao)` em `sysdoc_docx/corpo_dvi.py`, chamada só dentro de `build_corpo_despacho_xml` no momento de gerar o parágrafo do título — adiciona `"{numero}) "` quando o `titulo` ainda não começa com esse prefixo. O campo `titulo` devolvido por `montar_apontamentos()` continua exatamente como antes.
- **Files modified:** `sysdoc_docx/corpo_dvi.py`
- **Verification:** `python3 -m pytest tests/ -q` → 567 passed (554 anteriores + 13 novos), incluindo `tests/test_dvi_corpo.py` (nenhuma regressão nos testes que comparam `titulo` sem número) e `tests/test_dvi_despacho_e2e.py::TestDespachoGeral::test_tres_secoes_numeradas` (verde com `"3) PENDÊNCIAS DE DOCUMENTAÇÃO"` no texto extraído).
- **Committed in:** `f800b0e`

---

**Total deviations:** 1 auto-fixed (1 bug — Rule 1). Nenhuma mudança arquitetural, nenhum gate de segurança novo além dos já cobertos pelo `<threat_model>` do plano.

## Non-Standard Staging (leitura obrigatória)

`processo-teste/.sysdoc/config.yaml` foi editado em disco (adicionado `tipo: geral` e o bloco `despacho:`) para que o E2E pudesse rodar sem `skipped` — mas **não foi `git add`ado nem commitado**. `processo-teste/` inteiro permanece intencionalmente fora do controle de versão (`git status --porcelain processo-teste` mostra apenas `?? processo-teste/` antes e depois desta execução), porque contém dados reais de um processo institucional (SEI, valores, objeto) que o usuário não optou por versionar. Nenhum `git add -A`/`git add .` foi usado em nenhum commit desta plano; cada `git add` listou arquivos explícitos.

## Known Stubs

Nenhum. O E2E prova conteúdo real ponta a ponta; os marcadores `[PREENCHER: <campo>]` são o comportamento intencional documentado (T-06-06-02), não um stub.

## Threat Flags

Nenhum flag novo — a superfície do `<threat_model>` do plano (T-06-06-01 a T-06-06-05, T-06-06-SC) foi mitigada e verificada exatamente como especificado: isolamento por `tmp_path`, ausência de nome real no config de teste, marcador `[PREENCHER: ...]` documentado em `AGENTS.md`/`SKILL.md`, `skipif` de módulo, nenhuma dependência nova instalada.

## Verification Results

```
python3 -m pytest tests/test_dvi_despacho_e2e.py -v   → 13 passed, 0 skipped
python3 -m pytest tests/ -q                            → 567 passed
python3 -m pytest tests/test_sigla_dvi.py -q           → 4 passed (nenhuma regressão de terminologia)
ruff check tests/test_dvi_despacho_e2e.py sysdoc_docx/corpo_dvi.py → All checks passed!
git status --porcelain processo-teste                  → "?? processo-teste/" (idêntico antes/depois)
```

Mutação de controle exigida pelo critério de aceite: `CLASSIFICACOES_CORPO` temporariamente ampliado para incluir `"conforme"` fez `test_nenhum_item_conforme` falhar (`AssertionError: item conforme ETP-001 vazou para o despacho`), confirmando que o teste de fato detecta a regressão; revertido com edição direta (nenhum `git checkout`/`reset`/`clean` necessário, mudança não estava commitada ainda).

## Issues Encountered

Nenhum bloqueio. O único achado de execução foi o bug de numeração de pendências, tratado acima como deviation.

## User Setup Required

None - nenhuma configuração de serviço externo necessária.

## Next Phase Readiness

- Rodada 1 da Phase 6 (Despacho de Verificação Inicial) está completa: templates, builder, canal raw_xml, resolução de variante por `tipo`, E2E sobre processo real e documentação operacional — todos os 5 critérios de sucesso da rodada (`06-CONTEXT.md`) verificados.
- `SYSD-18` completo.
- Nenhum bloqueio para a próxima rodada da fase (templates de TR, 4 categorias Lei 14.133) nem para a decisão pendente de aposentar `templates/dvi_base.docx` (mencionada no CHANGELOG desta rodada, decisão formal adiada para quando a rodada de TR começar).
- Suíte completa em 567 testes verdes (554 antes desta rodada + 13 novos em `tests/test_dvi_despacho_e2e.py`).

---
*Phase: 06-templates-tr-a-partir-dos-modelos-lei-14-133*
*Completed: 2026-08-27*

## Self-Check: PASSED

- FOUND: tests/test_dvi_despacho_e2e.py
- FOUND: sysdoc_docx/corpo_dvi.py
- FOUND commit: f800b0e
- FOUND commit: 4c4fa9b
