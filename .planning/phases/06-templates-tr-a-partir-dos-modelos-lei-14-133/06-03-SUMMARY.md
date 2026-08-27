---
phase: 06-templates-tr-a-partir-dos-modelos-lei-14-133
plan: 03
subsystem: docs
tags: [dvi, terminologia, regressao, changelog, pytest]

# Dependency graph
requires:
  - phase: 06-01
    provides: "templates/dvi/despacho_geral.docx e despacho_tic.docx (moldura fiel ao modelo institucional)"
  - phase: 06-02
    provides: "sysdoc_docx/corpo_dvi.py — builder do corpo de apontamentos"
provides:
  - "Sigla DVI corrigida em todo o repositório fora de .planning/ e do histórico do CHANGELOG"
  - "tests/test_sigla_dvi.py — trava de regressão permanente contra a expansão errada"
  - "templates/dvi_base.docx regerado com título correto"
  - "Entrada no CHANGELOG rastreando a correção e referenciando o erro anterior"
affects: [06-04, 06-05, 06-06, 06-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Varredura de invariante de repositório via git ls-files + suffix filter, com exclusão explícita de arquivos históricos/autorreferentes"

key-files:
  created:
    - tests/test_sigla_dvi.py
  modified:
    - CLAUDE.md
    - AGENTS.md
    - README.md
    - checklists/dvi.yaml
    - skills/sysdoc/SKILL.md
    - .claude/skills/sysdoc-analise/SKILL.md
    - .opencode/skills/sysdoc-analise/SKILL.md
    - templates/build_dvi_base.py
    - templates/dvi_base.docx
    - tests/test_dvi_autocorrecao.py
    - tests/test_dvi_template_base.py
    - CHANGELOG.md

key-decisions:
  - "DVI = Despacho de Verificação Inicial (D-01), confirmado por processo-teste/referencias/dvi.md linha 1 e pelo dono do produto"
  - "tests/test_sigla_dvi.py exclui a si mesmo (tests/test_sigla_dvi.py) da própria varredura, além de .planning/ e CHANGELOG.md — o arquivo cita as expansões erradas como literais de busca, não como propagação do erro"
  - "CHANGELOG.md não teve a entrada histórica [1.5.x] reescrita; a correção entrou como nova entrada em [Não publicado] > Corrigido, referenciando a anterior"

patterns-established:
  - "Trava de invariante de repositório: teste que varre git ls-files inteiro e falha nomeando arquivo+linha, em vez de checar arquivos individuais hardcoded"

requirements-completed: []  # SYSD-18 abrange 06-03/06-04 (ver REQUIREMENTS.md); só marcar completo quando 06-04 also entregar o assembly de `sysdoc create dvi`

# Metrics
duration: 20min
completed: 2026-08-27
---

# Phase 6 Plan 03: Correção da sigla DVI Summary

**DVI corrigido de "Documento de Verificação Inicial" para "Despacho de Verificação Inicial" em 9 arquivos de documentação/código e 2 fixtures de teste, com teste de regressão de varredura total do repositório e entrada rastreável no CHANGELOG.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-08-27T03:59:00Z
- **Completed:** 2026-08-27T04:03:12Z
- **Tasks:** 3/3
- **Files modified:** 13 (11 modificados na Task 1, 1 criado na Task 2, 1 modificado + o criado ajustado na Task 3)

## Accomplishments
- Sigla DVI corrigida em `CLAUDE.md`, `AGENTS.md`, `README.md` (2 ocorrências), `checklists/dvi.yaml`, `skills/sysdoc/SKILL.md`, `.claude/skills/sysdoc-analise/SKILL.md`, `.opencode/skills/sysdoc-analise/SKILL.md`, `templates/build_dvi_base.py` (e `templates/dvi_base.docx` regerado byte-consistente com o novo texto), `tests/test_dvi_template_base.py` e `tests/test_dvi_autocorrecao.py`
- Teste de regressão `tests/test_sigla_dvi.py` (4 testes) trava permanentemente contra a reintrodução de qualquer uma das duas expansões erradas conhecidas
- CHANGELOG registra a correção sob `[Não publicado] > Corrigido`, citando a fonte institucional, os arquivos alterados e referenciando explicitamente a entrada anterior que havia corrigido a sigla para a expansão (também errada) "Documento de Verificação Inicial"

## Task Commits

Each task was committed atomically:

1. **Task 1: Corrigir a expansão da sigla nos 9 arquivos e nas 2 fixtures** - `e44b882` (fix)
2. **Task 2: Teste de regressão contra a expansão errada** - `46d8d33` (test)
3. **Task 3: Registrar a correção no CHANGELOG** - `6ec69b1` (docs)

_Nenhum commit de metadados de plano separado — este SUMMARY e a atualização de STATE/ROADMAP entram no commit final de fechamento do plano._

## Files Created/Modified
- `CLAUDE.md` - linha 42: "DVI significa **Despacho de Verificação Inicial**"
- `AGENTS.md` - linha 33: idem
- `README.md` - linhas 360 e 450: prosa e célula de tabela comparativa corrigidas
- `checklists/dvi.yaml` - linha 3: campo `descricao` do checklist canônico corrigido
- `skills/sysdoc/SKILL.md` - linha 45: prosa corrigida
- `.claude/skills/sysdoc-analise/SKILL.md` - linha 41: prosa corrigida
- `.opencode/skills/sysdoc-analise/SKILL.md` - linha 43: prosa corrigida
- `templates/build_dvi_base.py` - `_PARAGRAFOS[0]` agora `"DESPACHO DE VERIFICAÇÃO INICIAL — DVI"`
- `templates/dvi_base.docx` - regerado via `python3 templates/build_dvi_base.py` no mesmo commit da troca lexical
- `tests/test_dvi_template_base.py` - fixture `titulo` corrigida
- `tests/test_dvi_autocorrecao.py` - fixture `titulo` corrigida
- `tests/test_sigla_dvi.py` (novo) - varredura de `git ls-files` que trava as duas expansões erradas, confirma a expansão correta nos documentos canônicos, valida o DOCX base e confirma a grafia do modelo institucional
- `CHANGELOG.md` - nova entrada em `[Não publicado] > Corrigido`, entrada histórica `[1.5.x]` (linha 21) preservada sem edição

## Decisions Made
- DVI = Despacho de Verificação Inicial (D-01), confirmado por `processo-teste/referencias/dvi.md` linha 1 e pelo dono do produto — nenhuma inferência, fonte institucional literal.
- A correção do CHANGELOG entrou como nova entrada, não reescrita da entrada histórica `[1.5.x]` — preserva o registro do erro anterior, conforme D-02 e T-06-03-02 (Repudiation) do threat model.
- `tests/test_sigla_dvi.py` exclui a si mesmo da própria varredura, além de `.planning/` e `CHANGELOG.md` — necessário porque o arquivo precisa citar as duas expansões erradas como literais Python para poder buscá-las; sem essa exclusão o teste falharia contra sua própria definição de constantes (ver Deviations).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `tests/test_sigla_dvi.py` precisou se auto-excluir da própria varredura**
- **Found during:** Task 3, ao rodar `python3 -m pytest tests/ -q` após adicionar a entrada do CHANGELOG (a suíte inteira já estava verde na Task 2 isoladamente, mas o teste de regressão contém as strings-alvo como literais Python em `_EXPANSOES_ERRADAS`, o que o fazia se autodenunciar assim que a varredura via `git ls-files` incluísse a si mesmo)
- **Issue:** `test_nenhuma_ocorrencia_da_expansao_errada` falhava citando `tests/test_sigla_dvi.py:30-32` — as três strings de busca definidas no próprio módulo
- **Fix:** Adicionado `"tests/test_sigla_dvi.py"` a `_ARQUIVOS_EXCLUIDOS`, ao lado de `CHANGELOG.md`. É uma exclusão análoga à do histórico do CHANGELOG: o arquivo cita as expansões erradas como padrões de busca do próprio guard, não como documentação que propaga o erro para um agente de IA
- **Files modified:** `tests/test_sigla_dvi.py`
- **Verification:** `python3 -m pytest tests/ -q` volta a 510 passed; `ruff check tests/test_sigla_dvi.py` sai limpo
- **Committed in:** `6ec69b1` (junto com a entrada do CHANGELOG, Task 3)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Correção necessária para a suíte compilar sem falso positivo; não altera o comportamento da trava contra os 9+2 pontos reais do repositório, nem contra reintroduções futuras em qualquer outro arquivo.

## Issues Encountered
- Verificado manualmente (task 2, acceptance criteria) que reintroduzir "Documento de Verificação Inicial" em `AGENTS.md` faz `test_nenhuma_ocorrencia_da_expansao_errada` falhar citando `AGENTS.md:33` e o texto da linha; revertido com `git checkout -- AGENTS.md` (nenhum uso de `git clean`/`reset --hard`/blanket restore).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Terminologia DVI consistente em todo o repositório, com trava permanente contra regressão — planos 06-04 a 06-07 (templates de TR/ETP na mesma fase aberta) podem referenciar "Despacho de Verificação Inicial" sem risco de herdar a expansão errada.
- Suíte completa em 510 testes verdes (506 anteriores + 4 novos de `test_sigla_dvi.py`).
- Nenhum bloqueio para a próxima rodada da Phase 6.
- `SYSD-18` permanece `Pending` em `REQUIREMENTS.md`, por desenho: abrange `06-03/06-04` e só fica completo quando `06-04` entregar o assembly de `sysdoc create dvi` (canal `raw_xml` + bloco `despacho:`). Não foi marcado como concluído neste plano.

---
*Phase: 06-templates-tr-a-partir-dos-modelos-lei-14-133*
*Completed: 2026-08-27*

## Self-Check: PASSED
