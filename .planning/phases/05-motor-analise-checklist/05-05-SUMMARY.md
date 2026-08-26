---
phase: 05-motor-analise-checklist
plan: 05
subsystem: testing
tags: [decimal, arithmetic-audit, tdd, pytest, checklist-engine]

# Dependency graph
requires:
  - phase: 05-motor-analise-checklist plan 01
    provides: sysdoc_dvi/tipos.py (contratos ItemChecklist/ResultadoItem) e sysdoc_dvi/checklist.py (carregador YAML)
provides:
  - "sysdoc_dvi/verificacoes/calculo.py: auditoria aritmética determinística da pesquisa de preços (verificação `calculo` do RF4)"
  - "tests/fixtures/mcp_sintetico.json: fixture sintética com erros aritméticos plantados para CA2"
  - "tests/test_dvi_calculo.py: suíte de 25 testes provando zero falso negativo/positivo na detecção"
affects: [05-09 (síntese/apontamentos consumindo memoria_calculo), orquestrador de agentes (plano futuro)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Verificação determinística: LLM extrai dados em schema fechado, Python puro recalcula e decide (RF4/T-05-14)"
    - "Decimal + ROUND_HALF_UP em todo cálculo monetário, float proibido e verificado por grep no critério de aceite (T-05-15)"
    - "Divergência só é registrada quando excede tolerância absoluta E relativa simultaneamente"

key-files:
  created:
    - sysdoc_dvi/verificacoes/calculo.py
    - tests/fixtures/mcp_sintetico.json
    - tests/test_dvi_calculo.py
  modified: []

key-decisions:
  - "Método declarado inválido (fora de {media, mediana, menor}) usa 'media' como base de recálculo apenas para compor a memória de cálculo, gera exatamente uma Divergencia(campo='metodo') e não dispara checagens adicionais de unitário/total na mesma linha"
  - "diferenca_relativa é calculada em relação ao valor recalculado (referência 'correta'), arredondada a 4 casas antes da comparação de tolerância"
  - "Limites de max_linhas (500) e max_cotacoes_por_linha (50), configuráveis via parâmetro, mitigam DoS por tabela sintetizada indefinidamente (T-05-16, Rule 2)"

patterns-established:
  - "Módulo de verificação determinística sem nenhuma dependência de rede/LLM/arquivo — testável em isolamento com Decimal puro"

requirements-completed: [RF4, RNF4, RNF2]

# Metrics
duration: ~10min
completed: 2026-08-26
---

# Phase 5 Plan 5: Auditoria Aritmética Determinística (`calculo`) Summary

**Módulo `sysdoc_dvi/verificacoes/calculo.py` que recalcula média, mediana e unitário × quantidade em `Decimal`/`ROUND_HALF_UP` (nunca aceita do modelo), com memória de cálculo determinística e bateria de 6 erros sintéticos plantados detectados com zero falso negativo/positivo.**

## Performance

- **Duration:** ~10 min (commits entre 11:33:41 e 11:35:48 -03:00)
- **Tasks:** 3/3 completos
- **Files modified:** 3 (todos novos)

## Accomplishments
- `media()`, `mediana()` e `auditar_tabela_precos()` implementados exatamente conforme o contrato `<interfaces>` do plano, com `Decimal`/`ROUND_HALF_UP` em toda a aritmética e rejeição explícita de `float`.
- Fixture `tests/fixtures/mcp_sintetico.json` com 6 linhas sintéticas (1 controle correto, 4 com erro plantado, 1 dentro da tolerância) — nenhum dado real de processo.
- Suíte `tests/test_dvi_calculo.py` com 25 testes (`TestMedia`, `TestMediana`, `TestTolerancia`, `TestAuditoria`, `TestErrosPlantados`) provando CA2: 100% de detecção, zero falso negativo, zero falso positivo.
- Suíte completa do repositório (`tests/`) passa: 141 testes verdes.

## Task Commits

Each task was committed atomically:

1. **Task 1: Funções aritméticas puras e auditoria da tabela de preços** (TDD)
   - RED: `a0e51db` — `test(05-05): add failing tests for auditoria aritmética de preços`
   - GREEN: `0aa3fe5` — `feat(05-05): implement auditoria aritmética determinística da tabela de preços`
2. **Task 2: Fixture de MCP sintético com erros plantados** — `a2b5089` — `test(05-05): add MCP sintético fixture com erros aritméticos plantados`
3. **Task 3: Suíte de detecção sem falso negativo** (TDD) — `f2dc578` — `test(05-05): suíte de detecção de erros plantados sem falso negativo (CA2)`

**Plan metadata:** committed with this SUMMARY.md (see final commit in this plan's execution).

## Files Created/Modified
- `sysdoc_dvi/verificacoes/calculo.py` — `Cotacao`, `LinhaTabela`, `Divergencia`, `ResultadoCalculo`, `ErroTabelaPrecos`, `media`, `mediana`, `auditar_tabela_precos`; recálculo determinístico com memória de cálculo em português culto.
- `tests/fixtures/mcp_sintetico.json` — 6 linhas de tabela de preços com `divergencia_esperada` (4 não nulas), valores monetários sempre em string.
- `tests/test_dvi_calculo.py` — 25 testes cobrindo média/mediana, limites de tolerância, auditoria (conforme, método inválido, lista vazia, memória de cálculo, rejeição de float, limites de DoS) e detecção sem falso negativo/positivo contra a fixture.

## Decisions Made
- Método declarado inválido gera **apenas** `Divergencia(campo="metodo")` para a linha, usando `"media"` como base de recálculo somente para compor a memória de cálculo — evita disparar divergências adicionais de "unitario"/"total" incoerentes na mesma linha quando o método já está errado.
- `diferenca_relativa` é calculada relativa ao **valor recalculado** (referência correta), não ao declarado, e arredondada a 4 casas antes da comparação com a tolerância.
- Adicionados limites configuráveis `max_linhas=500` e `max_cotacoes_por_linha=50` em `auditar_tabela_precos` — não estavam no bloco `<interfaces>` do plano, mas o `<threat_model>` do próprio plano (T-05-16, disposition=`mitigate`) exige essa proteção contra DoS por tabela com número absurdo de linhas/cotações; adicionados como parâmetros opcionais com default explícito, sem quebrar a assinatura original (Rule 2).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Limites de linhas e cotações por linha em `auditar_tabela_precos`**
- **Found during:** Task 1 (implementação de `calculo.py`)
- **Issue:** O bloco `<interfaces>` do plano não incluía parâmetros de limite, mas o `<threat_model>` do próprio plano (T-05-16) exige mitigação explícita de DoS por tabela com número absurdo de linhas/cotações
- **Fix:** Adicionados parâmetros opcionais `max_linhas=500` e `max_cotacoes_por_linha=50` a `auditar_tabela_precos`, levantando `ErroTabelaPrecos` quando excedidos, sem alterar as assinaturas dos demais itens do contrato
- **Files modified:** `sysdoc_dvi/verificacoes/calculo.py`
- **Verification:** `TestAuditoria::test_limite_de_linhas_excedido_levanta_erro` e `test_limite_de_cotacoes_por_linha_excedido_levanta_erro` cobrem o comportamento
- **Committed in:** `0aa3fe5` (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical — mitigação de ameaça do próprio plano)
**Impact on plan:** Aditivo e não-invasivo (parâmetros opcionais com default); nenhuma quebra de contrato do bloco `<interfaces>`.

## Issues Encountered
None.

## TDD Gate Compliance

- **RED (Task 1):** confirmado — `tests/test_dvi_calculo.py` falhou por `ModuleNotFoundError: No module named 'sysdoc_dvi.verificacoes.calculo'` antes da implementação (commit `a0e51db`).
- **GREEN (Task 1):** confirmado — após `sysdoc_dvi/verificacoes/calculo.py` (commit `0aa3fe5`), os 13 testes `Media`/`Mediana`/`Tolerancia` passam.
- **Task 3 (tdd="true"), nota de conformidade:** o bloco `<behavior>` da Task 1 já exigia a implementação completa de `auditar_tabela_precos` (incluindo divergência de unitário, total e método, e memória de cálculo) — não apenas média/mediana/tolerância. Por isso, ao adicionar `TestAuditoria` e `TestErrosPlantados` na Task 3, os testes passaram imediatamente contra a implementação já existente da Task 1, sem uma fase RED com falha real. Isso é uma consequência do desenho do próprio plano (a Task 1 entrega o contrato de interface inteiro), não uma omissão do executor. Investigação confirmou que os testes exercitam lógica real (contagem exata de divergências, campo correto por linha, conteúdo da memória de cálculo) e não são tautológicos — servem como suíte de regressão/cobertura de CA2, não como driver de nova implementação. A sequência de gates do plano como um todo permanece válida: `test` (RED, Task 1) → `feat` (GREEN, Task 1) → `test` (Task 2, fixture) → `test` (Task 3, cobertura CA2).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `sysdoc_dvi.verificacoes.calculo.ResultadoCalculo.memoria_calculo` está pronto para alimentar o campo `parecer`/`fundamento` do apontamento no plano 05-09 (síntese).
- `auditar_tabela_precos` é independente de I/O e de rede — pode ser chamado diretamente pelo orquestrador de agentes (fase futura) assim que a extração LLM da tabela de preços em schema fechado estiver disponível.
- Nenhum bloqueio para as próximas plans da onda 2/3 desta fase.

---
*Phase: 05-motor-analise-checklist*
*Completed: 2026-08-26*

## Self-Check: PASSED

- FOUND: `sysdoc_dvi/verificacoes/calculo.py`
- FOUND: `tests/fixtures/mcp_sintetico.json`
- FOUND: `tests/test_dvi_calculo.py`
- FOUND: `.planning/phases/05-motor-analise-checklist/05-05-SUMMARY.md`
- FOUND commit: `a0e51db` (test — RED)
- FOUND commit: `0aa3fe5` (feat — GREEN)
- FOUND commit: `a2b5089` (test — fixture)
- FOUND commit: `f2dc578` (test — CA2 coverage)
