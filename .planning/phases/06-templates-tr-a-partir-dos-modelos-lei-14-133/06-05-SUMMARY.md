---
phase: 06-templates-tr-a-partir-dos-modelos-lei-14-133
plan: 05
subsystem: docx-generation
tags: [docx, dvi, despacho, xml-escape, config-yaml, cli]

requires:
  - phase: 06-01
    provides: "templates/dvi/despacho_geral.docx e despacho_tic.docx com placeholder raw isolado"
  - phase: 06-02
    provides: "sysdoc_docx.corpo_dvi.build_corpo_despacho_xml — builder do corpo dos apontamentos"
  - phase: 06-04
    provides: "render_docx_template(..., raw_xml=...) separado de values; valores_despacho(config)"
provides:
  - "resolver_tipo_verificacao/caminho_template_dvi/_e_semente_do_repo/selecionar_template_dvi em sysdoc.py — resolução de variante DVI por tipo (D-13) com precedência do projeto (D-14)"
  - "sysdoc create <pasta> dvi ligado ao builder do corpo real, injetado pelo canal raw_xml"
  - "seed_dvi_template/init_command conscientes de tipo (semeiam despacho_geral.docx ou despacho_tic.docx)"
  - "tests/test_dvi_create_variante.py — 22 testes ponta a ponta (precedência, variante, conteúdo, não-injeção)"
affects: ["06-06", "06-07"]

tech-stack:
  added: []
  patterns:
    - "Escada de precedência com hash SHA-256 para distinguir semente intocada do repo de template realmente customizado pelo órgão (D-14)"
    - "Mensagem de erro de configuração espelhando sysdoc_dvi/pipeline.py, trocando --tipo pelo caminho do config quando o comando não tem essa flag"

key-files:
  created:
    - tests/test_dvi_create_variante.py
  modified:
    - sysdoc.py
    - tests/test_dvi_template_base.py

key-decisions:
  - "Quando não há template no projeto E o projeto nunca rodou sysdoc init (paths.config ausente), selecionar_template_dvi preserva a mensagem antiga (\"Nenhum template DVI encontrado... referencias/\") em vez de pedir tipo — ver Deviations"
  - "tipo_config = resolver_tipo_verificacao(obrigatorio=False) roda incondicionalmente antes de selecionar_template_dvi (literal ao plano): um tipo inválido no config bloqueia create mesmo quando o template customizado do projeto tornaria tipo irrelevante"

requirements-completed: [SYSD-17, SYSD-18]

duration: 55min
completed: 2026-08-27
---

# Phase 6 Plan 05: Ligação do create dvi ao builder real, por tipo e sem injeção Summary

**`sysdoc create <pasta> dvi` agora resolve `despacho_geral.docx`/`despacho_tic.docx` pelo `tipo` do `.sysdoc/config.yaml` (respeitando template customizado do órgão), injeta o corpo real montado por `sysdoc_docx.corpo_dvi` pelo canal `raw_xml` — nunca por `values` — e `sysdoc init` semeia a variante correspondente.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-08-27T03:56:00Z (herdado do fim do Plano 04)
- **Completed:** 2026-08-27T04:27:19Z
- **Tasks:** 2/2
- **Files modified:** 3 (1 criado, 2 modificados)

## Accomplishments
- `resolver_tipo_verificacao(paths, obrigatorio)` lê `tipo: geral|tic` de `.sysdoc/config.yaml` com mensagens de erro que espelham `sysdoc_dvi/pipeline.py:285-293`, trocando a menção a `--tipo` (que `create` não tem) pelo caminho do config.
- `selecionar_template_dvi` implementa a escada de precedência combinada D-13+D-14 do `06-CONTEXT.md`: `--template` explícito > template customizado do projeto (SHA-256 diferente de toda variante do repo) > variante do `tipo` quando a semente em `referencias/` está intocada ou ausente.
- `seed_dvi_template`/`init_command` semeiam `despacho_geral.docx` ou `despacho_tic.docx` conforme `tipo` do config (ou `geral` por padrão quando ainda não escolhido); `init` nunca falha por causa de `tipo` não escolhido.
- O ramo `dvi` de `create()` monta `raw_xml["corpo_apontamentos_xml"] = build_corpo_despacho_xml(data)` — o corpo real dos apontamentos (filtrado, agrupado por peça, com referência cruzada) passa a substituir o antigo formato relatório (`{{tabela_itens}}`). O corpo **nunca** é escrito em `values`.
- `tests/test_dvi_create_variante.py` prova, chamando `sysdoc.create()` de ponta a ponta: os 4 caminhos de precedência (D-14), os 3 caminhos de resolução de `tipo` incluindo erro (D-13), 3 cenários de não-injeção por JSON — chave homônima de topo, aninhada, e payload de escape em `parecer` (D-09) —, 7 cenários de conteúdo filtrado (D-03/D-06/D-08) e 3 de semeadura por variante (D-14).
- Mutação de controle manual (trocar `raw_xml[...]` por `values[...]`) faz os dois testes esperados falharem (`test_json_com_chave_homonima_nao_injeta_xml_no_create` e `test_corpo_usa_estilos_nomeados`), confirmando que a suíte de fato detecta a regressão de segurança — revertida em seguida.

## Task Commits

1. **Task 1: Resolução de variante, semeadura consciente de tipo e injeção pelo canal raw_xml** - `aca21fb` (feat)
2. **Task 2: Testes de precedência, variante, conteúdo e não-injeção no create** - `226e6cb` (test)

**Plan metadata:** commit deste SUMMARY (a seguir)

## Files Created/Modified
- `sysdoc.py` — `TIPOS_VERIFICACAO`, `DVI_TEMPLATES_DIR`, `TIPO_VERIFICACAO_PADRAO`; `resolver_tipo_verificacao`, `caminho_template_dvi`, `_e_semente_do_repo`, `selecionar_template_dvi`, `_tipo_efetivo_para_semeadura`; `seed_dvi_template` e `init_command` reescritos para semear por variante; ramo `dvi` de `create()` reescrito (canal `raw_xml`, campos institucionais via `valores_despacho`, print de origem do template); import de `sysdoc_docx.corpo_dvi.build_corpo_despacho_xml` no topo do módulo.
- `tests/test_dvi_create_variante.py` (novo) — 22 testes em 5 classes: `TestResolucaoDeTipo`, `TestPrecedenciaDoProjeto`, `TestNaoInjecaoPeloJson`, `TestConteudoDoDespacho`, `TestSeedPorVariante`.
- `tests/test_dvi_template_base.py` — `TestSeedDviTemplate.test_init_cria_referencias_dvi_docx_byte_identico` agora compara contra `templates/dvi/despacho_geral.docx`; `TestCreateAposInit.test_create_dvi_funciona_logo_apos_init` grava `tipo: geral` no config antes de chamar `create` (a semente do repo agora exige `tipo`); fixture `titulo` da correção do Plano 03 preservada, com comentário citando a grafia maiúscula do modelo institucional.

## Decisions Made
- Ao resolver o template quando não há `.docx` de projeto: se `.sysdoc/config.yaml` **não existe** (projeto nunca rodou `sysdoc init`), a mensagem de erro continua sendo a antiga ("Nenhum template DVI encontrado... referencias/"), preservando compatibilidade com `tests/test_dvi_create.py::test_create_dvi_missing_template_fails_with_instructions` (que não roda `init_command`). Se o config **existe** mas `tipo` está vazio, a mensagem passa a ser "aplicabilidade não declarada" apontando para o config — o cenário coberto por `test_sem_tipo_e_sem_template_no_projeto_falha_com_remedio`. Essa distinção (config ausente vs. config presente com `tipo` vazio) não está escrita literalmente no plano, mas é a única forma de satisfazer os dois testes simultaneamente sem alterar nenhum já existente.
- `caminho_template_dvi` e `resolver_tipo_verificacao` levantam `SystemExit` "ruidoso" (falha explícita antes de qualquer leitura de ZIP), consistente com o padrão do módulo.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Assertões de estilo nomeado fracas demais para provar a mutação de controle**
- **Found during:** Task 2, ao executar a mutação de controle exigida pelo critério de aceite ("trocar `raw_xml[...]` por `values[...]` faz o teste falhar")
- **Issue:** A primeira versão dos testes usava `assert 'w:val="DviPecaTitulo"' in xml`. Como `xml.sax.saxutils.escape` (usado por `render_docx_template` para `values`) não escapa aspas (`"`), a substring `w:val="DviPecaTitulo"` sobrevive intacta mesmo dentro de um `<w:t>` cujo conteúdo é XML cru inteiramente escapado — a mutação de controle **não** fazia o teste falhar, violando o critério de aceite explícito da Task 2.
- **Fix:** Assertões trocadas para checar a tag de abertura completa (`'<w:pStyle w:val="DviPecaTitulo"/>' in xml`), que inclui `<`/`>` — caracteres que `xml_escape` de fato escapa. Aplicado em `test_json_com_chave_homonima_nao_injeta_xml_no_create` e `test_corpo_usa_estilos_nomeados`.
- **Files modified:** `tests/test_dvi_create_variante.py`
- **Verification:** Mutação manual (`raw_xml["corpo_apontamentos_xml"]` → `values["corpo_apontamentos_xml"]`) reexecutada após o ajuste: os dois testes falham como esperado; revertida com `git checkout -- sysdoc.py` (nenhum uso de `clean`/`reset --hard`). Suíte completa voltou a 554 verdes.
- **Committed in:** `226e6cb` (parte do commit da Task 2)

---

**Total deviations:** 1 auto-fixed (1 bug — Rule 1)
**Impact on plan:** Necessário para que a suíte de fato prove o que o critério de aceite da Task 2 exige; nenhuma mudança de comportamento em `sysdoc.py`.

## Known Stubs

Nenhum. O corpo do despacho é montado inteiramente a partir de dado real (`dados_consolidados.json` + `sysdoc_docx.corpo_dvi`); campos institucionais ausentes já viram marcador visível `[PREENCHER: <campo>]` (Plano 04), não um stub silencioso.

## Threat Flags

Nenhum flag novo — a superfície coberta pelo `<threat_model>` do plano (T-06-05-01 a T-06-05-07) foi mitigada e testada conforme especificado; nenhuma rota de rede, autenticação ou schema nova foi introduzida.

## Issues Encountered
- `ruff check sysdoc.py` acusava import mal ordenado (`I001`) após adicionar `from sysdoc_docx.corpo_dvi import build_corpo_despacho_xml` — corrigido com `ruff check --select I001 --fix sysdoc.py` (remoção de uma linha em branco excedente). Os 2 erros `F401` pré-existentes (`time`, `urllib.request` não usados) permanecem fora de escopo, já documentados como pré-existentes no SUMMARY do Plano 04.

## User Setup Required

None - nenhuma configuração de serviço externo necessária.

## Next Phase Readiness
- `sysdoc create <pasta> dvi` produz o despacho real (D-01 a D-14 da fase) a partir de qualquer `dados_consolidados.json` já produzido por `sysdoc-dvi run`; `sysdoc init` semeia a variante certa desde o primeiro `create`.
- Suíte completa em 554 testes verdes (532 antes desta rodada + 22 novos de `tests/test_dvi_create_variante.py`).
- Nenhum bloqueio para as próximas rodadas desta fase (06-06, 06-07) nem para a fase de TR/ETP subsequente.
- `SYSD-17`/`SYSD-18` completos: o assembly de `sysdoc create dvi` (canal `raw_xml` + builder real + resolução de variante) está em produção nesta rodada.

---
*Phase: 06-templates-tr-a-partir-dos-modelos-lei-14-133*
*Completed: 2026-08-27*

## Self-Check: PASSED

- FOUND: sysdoc.py
- FOUND: tests/test_dvi_create_variante.py
- FOUND: tests/test_dvi_template_base.py
- FOUND commit: aca21fb
- FOUND commit: 226e6cb
