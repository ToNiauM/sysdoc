---
phase: 06-templates-tr-a-partir-dos-modelos-lei-14-133
plan: 07
subsystem: docx-generation
tags: [docx, dvi, despacho, checkpoint-decision, changelog, cleanup]

requires:
  - phase: 06-05
    provides: "sysdoc init deixou de semear templates/dvi_base.docx (semeia templates/dvi/despacho_{geral,tic}.docx)"
  - phase: 06-06
    provides: "Rodada 1 fechada; decisão de aposentadoria explicitamente adiada para este plano"
provides:
  - "Decisão do usuário (aposentar) registrada e executada: templates/dvi_base.docx e templates/build_dvi_base.py removidos do repositório"
  - "tests/test_dvi_template_base.py trimado para cobrir só a semeadura de templates/dvi/ (TestSeedDviTemplate)"
  - "CHANGELOG.md com entrada Removido nomeando os dois arquivos e a decisão"
affects: []

tech-stack:
  added: []
  patterns:
    - "Checkpoint bloqueante que coleta decisão do usuário antes de qualquer remoção destrutiva, executada só na task seguinte"

key-files:
  created: []
  modified:
    - tests/test_dvi_template_base.py
    - CHANGELOG.md
  deleted:
    - templates/dvi_base.docx
    - templates/build_dvi_base.py

key-decisions:
  - "USER DECISION (Task 1, checkpoint:decision): aposentar — remover templates/dvi_base.docx e templates/build_dvi_base.py. Registrada literalmente pelo orquestrador antes da execução deste plano; não foi reperguntada."

requirements-completed: [SYSD-18]

duration: 20min
completed: 2026-08-27
---

# Phase 6 Plan 07: Destino do formato relatório dvi_base — decisão e execução Summary

**O usuário escolheu `aposentar` no checkpoint bloqueante da Task 1; a Task 2 removeu `templates/dvi_base.docx` e `templates/build_dvi_base.py` do repositório, trimou `tests/test_dvi_template_base.py` para as duas classes de teste que dependiam do arquivo, confirmou o `skipif` já existente em `tests/test_sigla_dvi.py` absorvendo a ausência sem erro, e registrou a decisão no CHANGELOG com a recuperabilidade via git history.**

## Performance

- **Duration:** ~20 min
- **Started:** herdado do fim do Plano 06 (checkpoint já resolvido pelo orquestrador antes desta execução)
- **Completed:** 2026-08-27
- **Tasks:** 2/2 (Task 1 resolvida pelo orquestrador antes do spawn deste executor; Task 2 executada nesta sessão)
- **Files modified:** 2 modificados (`tests/test_dvi_template_base.py`, `CHANGELOG.md`), 2 removidos (`templates/dvi_base.docx`, `templates/build_dvi_base.py`)

## Accomplishments

- **Task 1 (checkpoint:decision, gate="blocking") — já resolvida antes desta execução.** O orquestrador apresentou ao usuário as três opções do plano (`aposentar`, `descontinuar`, `manter`) com o conjunto real de placeholders do arquivo (`{{parecer_executivo}}`, `{{secao_etp.parecer_documento}}`, `{{secao_tr.parecer_documento}}`, `{{tabela_itens}}`, `{{total_itens}}`, `{{total_bloqueantes}}`, `{{total_pendentes}}`, `{{nota_integridade}}`, `{{titulo}}`, `{{subtitulo}}`, `{{modelo_ia}}`, `{{data_análise}}`) e a informação factual de que `sysdoc init` já não semeia mais esse arquivo desde o Plano 05. **Resposta literal do usuário: `aposentar`.** Nenhum arquivo foi alterado antes dessa resposta.
- **Task 2 — executada a opção `aposentar`:**
  - `git rm templates/dvi_base.docx templates/build_dvi_base.py`
  - `tests/test_dvi_template_base.py` reescrito: removidas as classes `TestTemplateBaseValido` (3 testes) e `TestCreateAposInit` (2 testes), a constante `TEMPLATE_BASE`, o helper `_placeholders_no_xml` e o helper `_escrever_dvi_json` — todos dependiam exclusivamente do arquivo removido e ficariam sem uso (F401/dead code) se mantidos. `_base_dvi_json` também removido (só era consumido pelos dois helpers/classes eliminados). `TestSeedDviTemplate` (4 testes) preservada **intacta**, incluindo a comparação byte-a-byte contra `templates/dvi/despacho_geral.docx` já estabelecida pelo Plano 05. Docstring do módulo reescrita para descrever o estado atual (aposentadoria + o que o módulo cobre agora).
  - `tests/test_sigla_dvi.py::test_docx_base_usa_a_expansao_correta` confirmado passando pelo caminho `skipped` (`pytest.skip("templates/dvi_base.docx aposentado.")`), sem erro — verificado isoladamente (`pytest tests/test_sigla_dvi.py -q` → 3 passed, 1 skipped) e na suíte completa.
  - `CHANGELOG.md`: nova entrada em `[Não publicado] > Removido`, nomeando os dois arquivos, a decisão literal do usuário, o conjunto de placeholders inspecionado, a garantia de que o conteúdo permanece disponível via HTML de análise (`templates/render_analise.py`) e `dados_consolidados.json`, que `create()` continua fornecendo `{{tabela_itens}}`/`total_*` para templates legados de terceiros, e a recuperabilidade via git history (`git show d180b24^:templates/dvi_base.docx`).
- **Verificação de acceptance criteria da Task 2 (todas passaram):**
  - `python3 -m pytest tests/ -q` → 561 passed, 1 skipped (0 falhas)
  - `ruff check tests/test_dvi_template_base.py tests/test_sigla_dvi.py` → All checks passed
  - `test ! -f templates/dvi_base.docx && test ! -f templates/build_dvi_base.py` → sai 0
  - `grep -c "TestTemplateBaseValido" tests/test_dvi_template_base.py` → 0
  - `python3 -m pytest tests/test_sigla_dvi.py -q` → 3 passed, 1 skipped (0 falhas)

## Task Commits

1. **Task 2: Executar a decisão (código + testes)** - `d180b24` (feat)
2. **Task 2: Registro no CHANGELOG** - `e38f8bf` (docs)

**Plan metadata:** commit deste SUMMARY (a seguir)

## Files Created/Modified

- `templates/dvi_base.docx` (removido) — formato relatório aposentado, recuperável via `git show d180b24^:templates/dvi_base.docx`
- `templates/build_dvi_base.py` (removido) — gerador determinístico do formato acima, recuperável via `git show d180b24^:templates/build_dvi_base.py`
- `tests/test_dvi_template_base.py` — trimado de 210 para 66 linhas; só `TestSeedDviTemplate` permanece, docstring do módulo atualizada
- `CHANGELOG.md` — nova entrada `### Removido` sob `[Não publicado]`

## Decisions Made

- **USER DECISION (Task 1):** `aposentar` — coletada pelo orquestrador antes do spawn deste executor, conforme instruído. Não foi reperguntada nesta sessão.
- Ao trimar `tests/test_dvi_template_base.py`, removidos junto com as duas classes todos os helpers que ficariam órfãos (`TEMPLATE_BASE`, `_placeholders_no_xml`, `_base_dvi_json`, `_escrever_dvi_json`, e os imports `json`, `re`, `zipfile`, `pytest` que só eram usados por esse código) — decisão de limpeza completa em vez de deixar dead code, para o arquivo passar em `ruff check` sem exceções.
- Nenhuma referência a `dvi_base` sobrou em `pyproject.toml` ou `MANIFEST.in` (nunca existiu) — nenhuma limpeza adicional de packaging necessária.

## Deviations from Plan

Nenhuma. Plano executado exatamente como escrito: opção `aposentar` da Task 2, sem achados de Rule 1/2/3/4.

## Non-Standard Staging (leitura obrigatória)

Nenhuma exceção nesta execução. Cada commit usou `git add` com arquivos explícitos (nunca `git add -A`/`git add .`). `.planning/config.json` foi deixado intocado (modificado pelo orquestrador, fora do escopo deste plano). `processo-teste/` permanece intencionalmente fora do controle de versão — `git status --porcelain processo-teste` mostrou apenas `?? processo-teste/` antes e depois de toda a execução.

## Known Stubs

Nenhum.

## Threat Flags

Nenhum flag novo. A superfície do `<threat_model>` do plano (T-06-07-01 a T-06-07-04, T-06-07-SC) foi mitigada exatamente como especificado: remoção só ocorreu após a resposta do checkpoint bloqueante; CHANGELOG nomeia arquivo e decisão (T-06-07-02); `TestTemplateBaseValido`/`TestCreateAposInit` removidos e `skipif` absorveu a ausência do arquivo sem quebrar a suíte (T-06-07-03); `create()` continua fornecendo `{{tabela_itens}}`/`total_*` (T-06-07-04); nenhuma dependência nova instalada (T-06-07-SC).

## Verification Results

```
python3 -m pytest tests/ -q                              → 561 passed, 1 skipped
python3 -m pytest tests/ -q -rs                           → SKIPPED tests/test_sigla_dvi.py:104 (aposentado, esperado)
python3 -m pytest tests/test_sigla_dvi.py -q              → 3 passed, 1 skipped
ruff check tests/test_dvi_template_base.py tests/test_sigla_dvi.py → All checks passed!
test ! -f templates/dvi_base.docx && test ! -f templates/build_dvi_base.py → 0
grep -c "TestTemplateBaseValido" tests/test_dvi_template_base.py → 0
git status --porcelain processo-teste                     → "?? processo-teste/" (idêntico antes/depois)
```

`ruff check .` (repo inteiro) reporta 33 erros pré-existentes em arquivos não tocados por este plano (`sysdoc.py`, `sysdoc_dvi/`, `templates/render_analise.py`, `templates/validate_sysdoc.py`, `tests/test_dvi_*.py` diversos, `tests/test_validate.py`, `setup.py`) — fora de escopo (Rule: scope boundary), não corrigidos aqui. `ruff check` restrito aos dois arquivos deste plano passa limpo.

## Issues Encountered

Nenhum bloqueio.

## User Setup Required

None.

## Next Phase Readiness

- Rodada 1 da Phase 6 (Despacho de Verificação Inicial) está completamente fechada: 7/7 planos concluídos, decisão pendente de aposentadoria do formato relatório resolvida e executada.
- Nenhum bloqueio para a próxima rodada da fase (templates de TR, 4 categorias Lei 14.133 — ver `<deferred>` de `06-CONTEXT.md`).
- Suíte completa em 561 testes verdes + 1 skip esperado (era 567 antes; -5 testes removidos junto com o arquivo aposentado, +1 skip que já era condicional à existência do arquivo).

---
*Phase: 06-templates-tr-a-partir-dos-modelos-lei-14-133*
*Completed: 2026-08-27*

## Self-Check: PASSED

- MISSING: templates/dvi_base.docx (esperado — removido intencionalmente nesta execução)
- MISSING: templates/build_dvi_base.py (esperado — removido intencionalmente nesta execução)
- FOUND: tests/test_dvi_template_base.py
- FOUND commit: d180b24
- FOUND commit: e38f8bf
