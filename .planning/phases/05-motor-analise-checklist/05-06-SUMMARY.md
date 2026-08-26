---
phase: 05-motor-analise-checklist
plan: 06
subsystem: motor-dvi
tags: [mecanica, grounding, rf4, rf5, tdd, difflib]
dependency-graph:
  requires:
    - sysdoc_dvi.tipos (ItemChecklist, ResultadoItem) — plano 05-01
  provides:
    - sysdoc_dvi.verificacoes.mecanica (verificar_numeracao, verificar_codigos_catalogo, verificar_cronograma, verificar_item_mecanico, AchadoMecanico)
    - sysdoc_dvi.grounding (normalizar_texto, verificar_trecho, aplicar_grounding, LIMIAR_GROUNDING_DEFAULT)
  affects:
    - orquestrador futuro (planos 05-07+) que despacha itens tipo=mecanica e aplica grounding sobre itens tipo=llm
tech-stack:
  added: []
  patterns:
    - "Verificação mecânica por dicionário de despacho (parametros['verificacao']) sem fallback silencioso — chave ausente ou inválida levanta ValueError explícito"
    - "Grounding por janela deslizante ancorada no primeiro token significativo (evita varredura O(n) completa do texto para peças grandes)"
    - "aplicar_grounding usa dataclasses.replace para preservar o de original e devolver cópia imutável do resultado reclassificado"
key-files:
  created:
    - sysdoc_dvi/verificacoes/mecanica.py
    - sysdoc_dvi/grounding.py
    - tests/test_dvi_mecanica.py
    - tests/test_dvi_grounding.py
  modified: []
decisions:
  - "Achados de ausência (catalogo/cronograma sem seção correspondente) usam trecho='' no AchadoMecanico — não há linha literal específica para citar quando o problema é a falta de algo; achados de numeração sempre citam a linha literal ofensiva"
  - "aplicar_grounding define risco_jurídico='informativo' no resultado reclassificado como pendente — escolha segura que nunca viola a regra de coerência risco_jurídico=bloqueante→severidade∈{crítica,alta}, já que severidade original é preservada sem alteração"
  - "verificar_item_mecanico mapeia achados presentes para classificação=risco com risco_jurídico bloqueante (severidade crítica/alta) ou relevante (demais severidades); ausência de achados sempre vira conforme/informativo/severidade='informativa'"
  - "Task 3 do plano (criar as suítes de teste) foi absorvida pelas fases RED de TDD das Tasks 1 e 2: os arquivos tests/test_dvi_mecanica.py e tests/test_dvi_grounding.py já nasceram com o conteúdo completo exigido (todas as classes de teste especificadas) durante o RED de cada tarefa, então a Task 3 não gerou diffs adicionais — apenas confirmou os critérios de aceite (35 testes combinados, >=18 exigidos; suíte completa de 151 testes verde)"
metrics:
  duration: "~50min"
  completed: "2026-08-26"
---

# Phase 5 Plan 06: Verificações mecânicas (RF4) e grounding check (RF5) Summary

Implementados os dois módulos puros que fecham a porta para alucinação estrutural (numeração fora de sequência, ausência de código de catálogo, cronograma mencionado sem constar) e para citação fabricada no campo `de` (grounding check com `difflib.SequenceMatcher`, sem dependência nova), com 35 testes novos cobrindo comportamento, coerência de `ResultadoItem` e o caso CA3 (trecho fabricado → `pendente` + `falha_grounding`).

## What Was Built

- **`sysdoc_dvi/verificacoes/mecanica.py`** — `AchadoMecanico` (frozen dataclass: `tipo`, `descricao`, `trecho`); `verificar_numeracao` reaproveita o padrão de seção numerada `^\s*(\d+(?:\.\d+)*)\.?\s+` (mesmo regex-base de `sysdoc.detect_sections`) e rastreia o último número visto por prefixo hierárquico para detectar salto, repetição e ordem incorreta dentro do mesmo nível; `verificar_codigos_catalogo` aceita `CATMAT`/`CATSER` seguidos de 4–8 dígitos e a forma "código do item" (com variação de acento/caixa) seguida de 3–8 dígitos; `verificar_cronograma` compara menção ("cronograma físico-financeiro" / "cronograma de execução") com presença de seção numerada cujo título contém "cronograma" ou de um bloco tipo tabela (linha com "etapa" e "valor"/"parcela"/"%"); `verificar_item_mecanico` despacha pela chave `item.parametros["verificacao"]`, levanta `ValueError` explícito se a chave estiver ausente ou fora de `{numeracao, catalogo, cronograma}`, e produz `ResultadoItem` com `origem_verificacao="deterministico"` e coerência classificação/severidade/risco_jurídico.
- **`sysdoc_dvi/grounding.py`** — `LIMIAR_GROUNDING_DEFAULT = 0.85`; `normalizar_texto` aplica remoção de hifenização de fim de linha, `unicodedata.normalize("NFKD")` para remover acentos, minúsculas e colapso de espaços; `verificar_trecho` extrai os tokens significativos (≥3 chars, fora de stopwords PT-BR) do trecho normalizado, localiza as posições do primeiro token significativo no texto normalizado (máx. 200 candidatas — mitigação de DoS), testa janelas de tamanho igual ao trecho ao redor de cada posição (deslocamento + passo proporcional ao tamanho do trecho) com `difflib.SequenceMatcher.ratio()`, e devolve `(score >= limiar, score)`; trecho iniciado por `[OMISSÃO]` devolve `(True, 1.0)` sem consultar o texto; trecho com menos de 3 tokens significativos devolve `(False, 0.0)`. `aplicar_grounding` não altera resultado com `origem_verificacao` em `{deterministico, lookup}`; para os demais, se `verificar_trecho(resultado.de, texto_peca, limiar)` falhar, devolve cópia (`dataclasses.replace`) com `classificação="pendente"`, `risco_jurídico="informativo"`, `falha_grounding=True` e `parecer` original mais o motivo da rejeição — preservando o `de` original para o relatório (RF9).
- **`tests/test_dvi_mecanica.py`** — `TestNumeracao` (5), `TestCatalogo` (4), `TestCronograma` (4), `TestItemMecanico` (5) = 18 testes.
- **`tests/test_dvi_grounding.py`** — `TestNormalizacao` (3), `TestVerificarTrecho` (4), `TestOmissao` (2), `TestLimiar` (3), `TestCA3` (4, incluindo o caso simétrico "trecho literal → nada muda" e a preservação do `de` original), `TestDesempenho` (1, peça de ~552 KB processada em bem menos de 5 s) = 17 testes.

## Verification

- `python -m pytest tests/test_dvi_mecanica.py -x -q` → 18 passed.
- `python -m pytest tests/test_dvi_grounding.py -x -q` → 17 passed.
- `python -m pytest tests/test_dvi_mecanica.py tests/test_dvi_grounding.py -q` → 35 passed (≥ 18 exigido).
- `python -m pytest tests/ -q` → **151 passed** (116 preexistentes + 35 novos).
- `grep -c "requests\|urllib\|openai\|anthropic" sysdoc_dvi/verificacoes/mecanica.py` → `0`.
- `grep -c "LIMIAR_GROUNDING_DEFAULT" sysdoc_dvi/grounding.py` → `3`; `grep -c "difflib" sysdoc_dvi/grounding.py` → `3`; `grep -c "rapidfuzz\|fuzzywuzzy\|Levenshtein" sysdoc_dvi/grounding.py` → `0`.
- `grep -c "class TestCA3" tests/test_dvi_grounding.py` → `1`.
- Acceptance-criteria one-liners do plano (numeração salto, CATMAT presente, trecho literal ancorado × trecho fabricado rejeitado) reproduzidos manualmente antes de cada commit GREEN — todos com o resultado esperado.

## Deviations from Plan

### Consolidação documentada (não é bug nem achado fora de escopo)

**1. Task 3 (criação das suítes) absorvida pelo RED das Tasks 1/2**
- **Encontrado em:** início da Task 3.
- **Situação:** as Tasks 1 e 2 são `tdd="true"` e exigem RED antes do GREEN; como o RED precisa de testes reais e completos para provar a ausência do módulo (não apenas um teste-placeholder), os arquivos `tests/test_dvi_mecanica.py` e `tests/test_dvi_grounding.py` já foram escritos com todas as classes/comportamentos exigidos pela Task 3 (`TestNumeracao`, `TestCatalogo`, `TestCronograma`, `TestItemMecanico`, `TestNormalizacao`, `TestVerificarTrecho`, `TestOmissao`, `TestLimiar`, `TestCA3`, mais o caso simétrico e o teste de desempenho) durante os commits RED de cada tarefa.
- **Ação:** Task 3 executada como verificação (todos os critérios de aceite confirmados: 35 testes combinados, `TestCA3` único, suíte completa de 151 testes verde) — nenhum diff de código adicional foi necessário, então nenhum commit extra foi gerado para ela.
- **Nenhuma alteração de escopo:** todo o conteúdo textual exigido no `<action>` da Task 3 está presente nos dois arquivos, comprovável pelos `grep`/contagens acima.

### Nenhuma outra alteração fora do escopo do plano.

## Decisions Made

Ver seção `decisions` do frontmatter.

## Known Stubs

Nenhum. Os dois módulos são funções puras completas e cobertas por teste; não há dado mockado, placeholder ou caminho de código morto introduzido nesta plan.

## Threat Flags

Nenhuma superfície de ameaça nova fora do `<threat_model>` do plano. As quatro mitigações do registro STRIDE foram implementadas e testadas:
- **T-05-17** (spoofing de trecho fabricado): `TestCA3.test_trecho_fabricado_reclassifica_para_pendente`.
- **T-05-18** (trecho curto genérico passando por ancoragem): `TestVerificarTrecho.test_trecho_curto_demais_nao_ancora` (rejeitado por construção, <3 tokens significativos).
- **T-05-19** (DoS via janela deslizante em peça grande): candidatas limitadas a 200 posições do primeiro token significativo + `TestDesempenho` (peça de ~552 KB processada em frações de segundo, bem abaixo do limite de 5 s).
- **T-05-20** (trecho rejeitado descartado sem rastro): `TestCA3.test_trecho_fabricado_reclassifica_para_pendente` confirma `reclassificado.de == de_original`.

## Self-Check: PASSED

- FOUND: sysdoc_dvi/verificacoes/mecanica.py
- FOUND: sysdoc_dvi/grounding.py
- FOUND: tests/test_dvi_mecanica.py
- FOUND: tests/test_dvi_grounding.py
- FOUND commit 207870c (test: RED — testes das verificações mecânicas)
- FOUND commit d88782e (feat: GREEN — mecanica.py)
- FOUND commit b0cc5f3 (test: RED — testes do grounding check)
- FOUND commit 30479c8 (feat: GREEN — grounding.py)

## TDD Gate Compliance

Task 1 (`tdd="true"`): RED confirmado (`ModuleNotFoundError: No module named 'sysdoc_dvi.verificacoes.mecanica'` antes da implementação, commit `207870c`) → GREEN confirmado (18/18 testes passando após implementação, commit `d88782e`). Nenhum commit `refactor` necessário.

Task 2 (`tdd="true"`): RED confirmado (`ModuleNotFoundError: No module named 'sysdoc_dvi.grounding'` antes da implementação, commit `b0cc5f3`) → GREEN confirmado (17/17 testes passando após implementação, commit `30479c8`). Nenhum commit `refactor` necessário.

Task 3 (`type="auto"`, sem gate TDD): verificação executada sobre o estado já GREEN das Tasks 1/2 — sem commit próprio (ver "Deviations from Plan").
