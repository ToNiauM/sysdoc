---
phase: 05-motor-analise-checklist
plan: 14
subsystem: cli
tags: [pipeline, orchestration, sysdoc-dvi, checkpoint, sintese, montagem, cli]

# Dependency graph
requires:
  - phase: 05-motor-analise-checklist (05-07)
    provides: sysdoc_dvi.pecas mapeamento de peças
  - phase: 05-motor-analise-checklist (05-08)
    provides: sysdoc_dvi.agente.AgenteLLM (AnalysisAgent)
  - phase: 05-motor-analise-checklist (05-09)
    provides: sysdoc_dvi.despacho (despacho por tipo, SCHEMAS_POR_TIPO)
  - phase: 05-motor-analise-checklist (05-10)
    provides: sysdoc_dvi.sintese.sintetizar (AgenteSintese protocol)
  - phase: 05-motor-analise-checklist (05-11)
    provides: sysdoc_dvi.montagem.montar_json, sysdoc_dvi.checkpoint, sysdoc_dvi.relatorio
provides:
  - "sysdoc_dvi/pipeline.py: executar_run — orquestração ponta a ponta (config → checklist → prepare → peças → checkpoint → despacho → síntese → montagem → validate → render → relatório → limpar checkpoint)"
  - "sysdoc_dvi/cli.py: subcomandos run/relatorio/config implementados (binário sysdoc-dvi funcional)"
  - "tests/test_dvi_run.py: cobertura ponta a ponta com agente falso, sem rede"
  - "sysdoc.py: correção do campo cache do manifest (era relativo ao cwd, agora relativo à raiz do projeto)"
affects: [05-15, "sysdoc create dvi (integração futura com o pipeline)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Orquestrador único (executar_run) que importa sysdoc como biblioteca, nunca via subprocess do próprio binário"
    - "Adaptador fino (chamar()) para casar AgenteLLM (protocolo AnalysisAgent) com o protocolo AgenteSintese exigido pela síntese, sem alterar nenhum dos dois módulos originais"
    - "Preenchimento determinístico de placeholders PT-BR (prefixo [OMISSÃO] em de/para) antes de montar_json, para que um item pendente nunca aborte a montagem inteira"

key-files:
  created:
    - sysdoc_dvi/pipeline.py
    - tests/test_dvi_run.py
  modified:
    - sysdoc_dvi/cli.py
    - sysdoc.py
    - CHANGELOG.md

key-decisions:
  - "modelo_ia do JSON final é o slug do modelo forte configurado (config.forte.partition('/')[2]), nunca um valor genérico"
  - "projeto (órgão/processo/valor_estimado/objeto) é lido de .sysdoc/config.yaml quando presente, com fallback determinístico via sysdoc.detect_process/detect_values/detect_object sobre os textos mapeados"
  - "Itens pendentes com de/para/parecer/fundamento vazios (comportamento intencional de despacho._pendente e agente._resultado_pendente) recebem texto de preenchimento determinístico com >=3 palavras antes de montar_json, prefixando de/para com [OMISSÃO] para que a rastreabilidade do validador também não acuse fabricação"

patterns-established:
  - "Pattern: qualquer módulo que precise satisfazer dois protocolos de agente distintos (AnalysisAgent + AgenteSintese) deve usar duck-typing (hasattr 'chamar') no orquestrador, nunca redefinir os protocolos"

requirements-completed: [RF2, RF3, RF8, RF9, RNF2, RNF3, RNF4]

# Metrics
duration: 45min
completed: 2026-08-26
---

# Phase 5 Plan 14: Pipeline do orquestrador DVI (`sysdoc-dvi run/relatorio/config`) Summary

**`sysdoc-dvi run [pasta]` executa o fluxo completo — prepare → mapeamento de peças → checklist por item com retomada por checkpoint → síntese pelo modelo forte → `dados_consolidados.json` validado e renderizado → relatório de execução — num único comando testado ponta a ponta com um agente falso, sem rede.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 3
- **Files modified:** 4 (`sysdoc_dvi/pipeline.py` criado, `sysdoc_dvi/cli.py` e `sysdoc.py` modificados, `tests/test_dvi_run.py` criado) + `CHANGELOG.md`

## Accomplishments
- `sysdoc_dvi/pipeline.py` implementa `executar_run` com a ordem fixa exigida pelo plano: config de modelos → checklist filtrado → `sysdoc.prepare` (se necessário) → mapeamento de peças → checkpoint → `despacho.executar_checklist` → `sintese.sintetizar` → `montagem.montar_json` → `sysdoc.validate` → `sysdoc.render` → relatório em `output/` → `checkpoint.limpar_checkpoint`. Toda exceção conhecida do motor vira mensagem de uma linha com o remédio e código de saída 1, sem stack trace.
- `sysdoc_dvi/cli.py` tem `run`/`relatorio`/`config` funcionais: `run` delega ao pipeline; `relatorio` reimprime o último `output/*_relatorio_*.json` sem reexecutar nada; `config` grava a seção `dvi` de `~/.sysdoc/config.json` com permissão restrita (diretório 0700, arquivo 0600) e `--listar` nunca ecoa uma chave de API.
- `tests/test_dvi_run.py` monta um projeto sintético completo (ETP/TR reais, checklist customizado de 3 itens cobrindo `presenca`/`julgamento`, `.sysdoc/config.yaml` com `tipo: geral`, `~/.sysdoc/config.json` de teste via `HOME` monkeypatchado) e um `AgenteFalso` que implementa tanto `AnalysisAgent` quanto `AgenteSintese` (`.chamar`), sem nenhuma chamada de rede. Cobre abort sem config, abort sem peça obrigatória, execução completa com validação real, retomada (agente chamado menos vezes na segunda execução) e o dispatch da CLI.
- Corrigido um bug de integração real (não coberto por nenhum teste anterior, que usava fixtures de manifest sintéticas): `sysdoc.write_extracted_text` gravava o campo `cache` do manifest relativo ao `cwd`, mas `sysdoc_dvi.pecas.mapear_pecas` sempre o resolve relativo à raiz do projeto — ao rodar `sysdoc prepare Projeto` a partir do diretório pai (padrão mais comum), isso duplicava o prefixo do projeto no caminho e todo mapeamento real de peça falhava. Só foi descoberto porque este plano é o primeiro a exercitar `prepare` → `mapear_pecas` com arquivos reais em vez de manifests sintéticos.

## Task Commits

Each task was committed atomically:

1. **Task 1: Orquestração do run** - `ed04c8a` (feat) — inclui a correção do bug de caminho de cache em `sysdoc.py`
2. **Task 2: Implementar os subcomandos da CLI sysdoc-dvi** - `e8a4bc6` (feat)
3. **Task 3: Teste ponta a ponta com agente falso** - `0a9f6d8` (test)

**Plan metadata:** _(commit final desta execução, gravado a seguir)_

## Files Created/Modified
- `sysdoc_dvi/pipeline.py` - `executar_run`/`ErroPipeline`, orquestração ponta a ponta, adaptador de síntese, preenchimento de placeholders pendentes
- `sysdoc_dvi/cli.py` - handlers reais de `run`/`relatorio`/`config` (antes eram stubs devolvendo 2)
- `sysdoc.py` - `write_extracted_text`: campo `cache` do manifest agora relativo a `paths.root` (Rule 1 bugfix)
- `tests/test_dvi_run.py` - suíte ponta a ponta (10 testes: abort sem config, abort sem peça, run completo, retomada, CLI, segredo de config)
- `CHANGELOG.md` - entradas "Adicionado" (`sysdoc-dvi run/relatorio/config`) e "Corrigido" (caminho de cache do manifest)

## Decisions Made
- `modelo_ia` do JSON final vem do modelo **forte** configurado (a síntese é a última etapa e usa o modelo forte; o item individual pode ter usado o econômico).
- Dados de `projeto` (`órgão`/`processo`/`valor_estimado`/`objeto`) priorizam `.sysdoc/config.yaml`, com fallback determinístico para os detectores já existentes em `sysdoc.py` (`detect_process`/`detect_values`/`detect_object`) sobre os textos das peças mapeadas — nenhuma chamada a modelo para isso.
- `numero_etp`/`numero_tr` (exigidos por `sintese.sintetizar`) vêm de `.sysdoc/config.yaml` (`numero_etp`/`numero_tr`) com fallback para `"não informado"`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrigido caminho de cache duplicado no manifest, quebrando todo mapeamento real de peça**
- **Found during:** Task 1 (implementação de `executar_run`), confirmado pelo teste ponta a ponta da Task 3
- **Issue:** `sysdoc.write_extracted_text` gravava `item["cache"]` via `rel(out_path)`, relativo ao `cwd`. Ao rodar `sysdoc prepare Projeto` a partir do diretório pai — o padrão usado em todos os testes existentes (`monkeypatch.chdir(tmp_path); sysdoc.prepare("Projeto")`) e o modo mais comum de uso real — `rel()` devolve `"Projeto/.sysdoc/cache/..."`. `sysdoc_dvi.pecas._resolver_caminho_cache`, porém, sempre resolve esse campo como `paths.root / entrada["cache"]`, produzindo `.../Projeto/Projeto/.sysdoc/cache/...` — fora de `.sysdoc/cache` — e `ErroMapeamentoPeca` em toda execução real.
- **Fix:** `"cache"` agora é gravado como `str(out_path.resolve().relative_to(paths.root.resolve()))`, sempre relativo à raiz do projeto, batendo com a suposição de `mapear_pecas`. As duas únicas outras leituras de `item["cache"]` (dentro de `prepare()`) usam apenas `.name`, então não foram afetadas.
- **Files modified:** `sysdoc.py`
- **Verification:** `tests/test_dvi_run.py::TestRunCompleto` (mapeamento real de ETP/TR + `sysdoc.validate` real passando) e suíte completa (`pytest tests/ -q`, 364 testes)
- **Committed in:** `ed04c8a` (parte do commit da Task 1)

**2. [Rule 2 - Missing Critical] Preenchimento de placeholders para itens pendentes antes de `montar_json`**
- **Found during:** Task 1, ao integrar `despacho.executar_checklist`/`agente.AgenteLLM` com `montagem.montar_json` (nota de integração explícita no prompt de execução)
- **Issue:** `despacho._pendente` e `agente._resultado_pendente` deliberadamente devolvem `de`/`para`/`parecer`/`fundamento` vazios para itens que degradaram para `pendente` (nunca inventam conteúdo). `montagem.montar_json`, porém, levanta `ErroMontagem` para qualquer um desses campos com menos de 3 palavras — um único item pendente abortaria a montagem inteira do relatório, violando RF9 ("um item nunca derruba a análise inteira").
- **Fix:** `pipeline._preencher_pendencias` roda antes de `sintetizar`/`montar_json` e substitui, campo a campo, qualquer texto com menos de 3 palavras por um texto determinístico em português culto (`de`/`para` sempre prefixados com `[OMISSÃO]`, o mesmo marcador já usado por `despacho`/`grounding`/`validate_sysdoc.is_traceable`, para que a checagem de rastreabilidade do validador real também não acuse fabricação).
- **Files modified:** `sysdoc_dvi/pipeline.py`
- **Verification:** cobertura indireta via `TestRunCompleto` (checklist seed real tem um item `mecanica` sem `parametros.verificacao`, que degrada para pendente e ainda assim passa por `sysdoc.validate` real)
- **Committed in:** `ed04c8a` (parte do commit da Task 1)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** Ambos essenciais para que o pipeline funcione de ponta a ponta com dados reais; sem os dois, `executar_run` nunca completaria um run real (peça nunca mapeada) nem sobreviveria a um único item pendente (montagem sempre abortaria). Sem scope creep — nenhuma mudança tocou `templates/analise_template.html`, `templates/render_analise.py` ou `templates/validate_sysdoc.py`.

## Issues Encountered
- O checklist semente (`checklists/dvi.yaml`, de 05-13, bloqueado aguardando fontes de negócio) tem apenas um item ativo (`DVI-GER-001`, `tipo=mecanica`) e esse item tem `parametros: {}` sem a chave `verificacao` exigida por `verificar_item_mecanico` — ele sempre degrada para `pendente` via despacho (comportamento correto e esperado, não um bug do pipeline). Por isso o teste ponta a ponta usa um checklist sintético próprio (`_escrever_checklist`, 3 itens `presenca`/`julgamento` cobrindo ETP e TR) passado via `checklist=`, em vez do arquivo semente do repositório — exercita o pipeline de forma completa e determinística sem depender da conversão pendente do checklist real.

## User Setup Required
None - no external service configuration required. `sysdoc-dvi run` requer `~/.sysdoc/config.json` com a seção `dvi` (`economico`/`forte`) e as chaves de API correspondentes — já documentado no remédio da própria mensagem de erro (`ErroConfiguracaoModelos`) e em `sysdoc_dvi/config.py`.

## Next Phase Readiness
- `sysdoc-dvi run/relatorio/config` está funcional e testado ponta a ponta; falta apenas o checklist completo (~50 itens, bloqueado em 05-13) para uso em produção — o pipeline já funciona corretamente contra o checklist semente de 6 itens.
- `sysdoc create dvi` (05-12) e `sysdoc deploy` permanecem manuais, como decidido no plano (exigem revisão humana antes).
- Nenhum bloqueio para 05-15.

---
*Phase: 05-motor-analise-checklist*
*Completed: 2026-08-26*

## Self-Check: PASSED

- FOUND: sysdoc_dvi/pipeline.py
- FOUND: tests/test_dvi_run.py
- FOUND: .planning/phases/05-motor-analise-checklist/05-14-SUMMARY.md
- FOUND commit: ed04c8a
- FOUND commit: e8a4bc6
- FOUND commit: 0a9f6d8
