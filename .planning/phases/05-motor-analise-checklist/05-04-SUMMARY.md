---
phase: 05-motor-analise-checklist
plan: 04
subsystem: motor-dvi
tags: [python, pyyaml, checklist, vigencia, tdd, determinístico]

# Dependency graph
requires:
  - phase: 05-motor-analise-checklist (plan 01)
    provides: sysdoc_dvi package (tipos.py contracts, checklist.py loader), checklists/dvi.yaml
provides:
  - "normas/vigencia.yaml: tabela global curada de vigência de normativos (6 entradas semeadas)"
  - "sysdoc_dvi/normas.py: carregar_vigencia, normalizar_citacao, consultar_norma, normas_desatualizadas, verificar_item_vigencia"
  - "Verificação determinística do tipo `vigencia` do motor DVI, sem chamada a LLM"
affects: [05-motor-analise-checklist plans posteriores (orquestrador, relatório de execução)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lookup exato via tabela curada; nunca correspondência aproximada para vigência"
    - "Normalização determinística de citações legais (acentos, nº/n°/no, datas por extenso, milhar)"
    - "Override por projeto sobrescreve entrada global na indexação (D-10)"

key-files:
  created:
    - normas/vigencia.yaml
    - sysdoc_dvi/normas.py
    - tests/test_dvi_normas.py
  modified: []

key-decisions:
  - "Domínio de status ampliado para incluir `pendente_de_conferencia` (5º valor), necessário para semear a tabela sem inventar revogação/substituição não confirmada — comportamento do task exigia esse valor mas a lista do <behavior> citava só 4"
  - "Prioridade de classificação quando múltiplas citações no mesmo item: risco > pendente (não catalogada) > conforme"
  - "de/para em `vigencia` sempre carregam a citação literal encontrada (ou substituida_por quando houver); ausência de citação usa marcador [OMISSÃO] (convenção RF5 do schema)"

patterns-established:
  - "Pattern: tabela YAML curada + normalizador determinístico + lookup exato é o padrão para qualquer verificação que não deve depender de julgamento de modelo (reaproveitável em futuros tipos de verificação)"

requirements-completed: [RF7, RF4, RNF1, RNF4]

# Metrics
duration: ~15min
completed: 2026-08-26
---

# Phase 5 Plan 04: Tabela de vigência e verificação determinística Summary

**Tabela curada `normas/vigencia.yaml` (6 normativos, override por projeto) + `sysdoc_dvi/normas.py` com lookup exato de citações legais e `verificar_item_vigencia` 100% determinístico, sem qualquer chamada a modelo de linguagem.**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-08-26T14:34:45Z
- **Tasks:** 3 (consolidados em ciclo TDD RED→GREEN de plano, conforme frontmatter `type: tdd`)
- **Files modified:** 3 (2 created source, 1 created test)

## Accomplishments
- `normas/vigencia.yaml` semeado com as 6 normas citadas nos itens semente de `checklists/dvi.yaml` (Lei 14.133/2021, Decreto 10.024/2019, IN SEGES/ME 65/2021, IN SEGES/ME 58/2022, IN SGD/ME 94/2022, Acórdão TCU 1.872/2018-Plenário), com aliases e `conferida_em`
- `carregar_vigencia` funde tabela global + override por projeto (projeto vence em caso de colisão), com validação estrutural completa (`ErroVigencia`)
- `normalizar_citacao` iguala variantes de grafia legal (nº/n°/no/n., data por extenso vs. curta, pontuação de milhar, acentos, caixa)
- `consultar_norma` faz lookup exato (sem correspondência aproximada) — norma ausente devolve `None`
- `normas_desatualizadas` sinaliza normas com `conferida_em` vencido (limiar configurável, default 180 dias), sem duplicar por alias
- `verificar_item_vigencia` produz `ResultadoItem` determinístico (`origem_verificacao="lookup"`) cobrindo vigente→conforme, revogada/substituída→risco relevante (citando a substituta), não catalogada→pendente ("norma não catalogada"), e ausência de citação→pendente
- 30 testes novos em `tests/test_dvi_normas.py` (excede o mínimo de 14 do plano); suíte completa do repositório: 146 testes passando

## Task Commits

TDD de nível de plano (`type: tdd` no frontmatter) — RED único cobrindo os comportamentos das três tasks, seguido de GREEN único implementando os dois artefatos entregáveis:

1. **RED — testes cobrindo Tasks 1, 2 e 3** - `e51e6a8` (test)
2. **GREEN — normas/vigencia.yaml + sysdoc_dvi/normas.py** - `47386f0` (feat)

**Gate sequence verificado:** `test(05-04)` (e51e6a8) antecede `feat(05-04)` (47386f0) no git log; RED confirmado por `ModuleNotFoundError: No module named 'sysdoc_dvi.normas'` antes da implementação.

## Files Created/Modified
- `normas/vigencia.yaml` - tabela global curada de vigência de normativos (6 entradas, comentário no topo declarando curadoria manual)
- `sysdoc_dvi/normas.py` - `ErroVigencia`, `carregar_vigencia`, `normalizar_citacao`, `consultar_norma`, `normas_desatualizadas`, `verificar_item_vigencia`
- `tests/test_dvi_normas.py` - 30 testes: `TestCarga`, `TestOverride`, `TestNormalizacao`, `TestLookup`, `TestCuradoria`, `TestVerificacaoVigencia`

## Decisions Made
- **Status `pendente_de_conferencia` adicionado ao domínio válido:** o `<behavior>` da Task 1 lista apenas `{vigente, revogada, substituida, suspensa}` como domínio de `status`, mas o `<action>` da mesma task exige usar `status: pendente_de_conferencia` quando o status real não é conhecido com segurança. Resolvi a inconsistência tratando `pendente_de_conferencia` como 5º valor válido — sem isso seria impossível semear a tabela real sem violar a regra "não inventar revogação nem substituição" do próprio `<action>`. 5 das 6 normas seedadas usam esse status por não haver confirmação de curadoria disponível nesta sessão.
- **Prioridade de classificação em item com múltiplas citações:** risco > pendente (não catalogada) > conforme, decisão de implementação não detalhada no plano (não havia teste de múltiplas citações conflitantes no plano; adicionei essa regra para tornar a função total e determinística).
- **Regex de extração de citações (T-05-12):** sem alternância aninhada, quantificador limitado (`{0,120}?`), testado com texto de 30k parágrafos (~1MB) processando em bem menos de 2s — mitigação do DoS por retrocesso catastrófico confirmada por teste (`test_regex_citacao_processa_texto_grande_rapidamente`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug/inconsistência de spec] Domínio de `status` ampliado para incluir `pendente_de_conferencia`**
- **Found during:** Task 1 (seed de `normas/vigencia.yaml`)
- **Issue:** `<behavior>` da Task 1 declara domínio de status como 4 valores; `<action>` da mesma task exige um 5º valor (`pendente_de_conferencia`) para status desconhecido — as duas frases do próprio plano se contradiziam.
- **Fix:** `STATUS_VALIDOS` em `sysdoc_dvi/normas.py` inclui os 5 valores; teste `test_status_fora_do_dominio_levanta_erro` cobre um valor realmente inválido (`cancelada`) para confirmar que a validação de domínio continua ativa.
- **Files modified:** sysdoc_dvi/normas.py, normas/vigencia.yaml, tests/test_dvi_normas.py
- **Verification:** `python -m pytest tests/test_dvi_normas.py -q` — 30/30 verdes
- **Committed in:** 47386f0 (GREEN)

---

**Total deviations:** 1 auto-fixed (Rule 1 — spec inconsistency in the plan itself)
**Impact on plan:** Necessário para cumprir literalmente a instrução do `<action>` de não inventar revogação/substituição sem base confirmada. Nenhum scope creep; domínio de status permanece fechado e validado.

## Issues Encountered
None além da inconsistência de spec documentada acima.

## Verification Results

- `python -m pytest tests/ -q` → 146 passed
- `python -c "import yaml;d=yaml.safe_load(open('normas/vigencia.yaml'));print(len(d['normas']))"` → 6
- `grep -c "conferida_em" normas/vigencia.yaml` → 7 (6 entradas + 1 menção em comentário de cabeçalho)
- `python -c "from sysdoc_dvi.normas import carregar_vigencia;t=carregar_vigencia('normas/vigencia.yaml');print('nllc' in ' '.join(t))"` → `True`, exit 0
- `grep -c "requests\|urllib\|http" sysdoc_dvi/normas.py` → 0
- `grep -rn "vigencia" sysdoc.py` → **não vazio**, mas os dois resultados (`sysdoc.py:1000-1001`) são um campo de projeto pré-existente e não relacionado (`projeto.get("vigência")`, usado em `_detect_procurement_category` para detectar "dedicação exclusiva" em serviços) — não importa nem referencia `sysdoc_dvi.normas`. A CLI determinística continua sem qualquer dependência do motor; o critério do plano é uma verificação textual imprecisa para um termo de negócio genérico já existente no código antes desta fase. Nenhuma ação necessária (fora do escopo desta task — Rule scope boundary).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `sysdoc_dvi/normas.py` está pronto para ser consumido pelo orquestrador (plano futuro) no despacho de itens `tipo: vigencia`
- `normas/vigencia.yaml` precisa de revisão humana do dono do produto antes de qualquer análise real: 5 das 6 entradas estão com `status: pendente_de_conferencia` — item pendente no roadmap, não bloqueio de código
- Nenhum bloqueio para os planos seguintes da fase (verificações `calculo`/`mecanica`, grounding check, orquestrador)

---
*Phase: 05-motor-analise-checklist*
*Completed: 2026-08-26*

## Self-Check: PASSED

- FOUND: normas/vigencia.yaml
- FOUND: sysdoc_dvi/normas.py
- FOUND: tests/test_dvi_normas.py
- FOUND: commit e51e6a8 (test)
- FOUND: commit 47386f0 (feat)
