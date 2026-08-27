---
phase: 07-interface-web-para-pregoeiros
plan: 03
subsystem: api
tags: [django, orm, sqlite, worker, fila, sysdoc-dvi, biblioteca-chamavel]

requires:
  - phase: 07-interface-web-para-pregoeiros (plan 01)
    provides: "sysdoc_dvi.pipeline.executar_run(progresso=callback) e sysdoc.prepare()/project_paths()/load_config()/write_config() chamáveis como biblioteca"
  - phase: 07-interface-web-para-pregoeiros (plan 02)
    provides: "Pacote Django sysdoc_web com settings endurecidas (SYSDOC_PROCESSOS_DIR, SQLite timeout=20) e fixture pytest django_web"
provides:
  - "Modelos Processo/AnaliseJob com UniqueConstraint condicional uma_analise_ativa_por_vez — uma análise por vez travada no banco (D-14)"
  - "sysdoc_web/processos/servicos.py — única camada que toca o disco de um processo, com slug validado por regex + checagem de contenção redundante"
  - "sysdoc_web/processos/fila.py — enfileirar()/reivindicar_proximo()/concluir()/sanear_jobs_orfaos(), convertendo IntegrityError e OperationalError em FilaOcupada"
  - "manage.py runworker --uma-vez / --intervalo — worker single-slot chamando sysdoc.prepare()/pipeline.executar_run() como biblioteca, com progresso traduzido para linguagem de processo"
  - "manage.py sanear_jobs — comando de saneamento de subida (jobs órfãos viram interrompida)"
affects: [07-04, 07-05, 07-06, 07-07]

tech-stack:
  added: []
  patterns:
    - "UniqueConstraint condicional (Q(status__in=STATUS_ATIVOS)) como mecanismo de trava de negócio no banco, nunca um if de leitura prévia na view/worker"
    - "Retry curto (0.1/0.2/0.4s) com transaction.atomic() próprio por tentativa, para absorver contenção de lock do SQLite sem deixar OperationalError escapar como 500"
    - "Validação de slug por regex (mesmo padrão de SlugField) antes de montar qualquer caminho de disco, redundante com a checagem de contenção pós-resolve()"

key-files:
  created:
    - sysdoc_web/processos/models.py
    - sysdoc_web/processos/servicos.py
    - sysdoc_web/processos/admin.py
    - sysdoc_web/processos/migrations/0001_initial.py
    - sysdoc_web/processos/fila.py
    - sysdoc_web/processos/progresso.py
    - sysdoc_web/processos/management/commands/runworker.py
    - sysdoc_web/processos/management/commands/sanear_jobs.py
    - tests/test_web_fila.py
  modified:
    - pyproject.toml

key-decisions:
  - "caminho_do_processo() valida o slug por regex (^[-a-zA-Z0-9_]+\\Z, mesmo padrão do SlugField) antes de montar qualquer Path — necessário porque um valor como '..%2Ffora' não contém separador de caminho e por isso não seria pego só pela checagem de contenção (resultado.parent != raiz) que o plano descreve; as duas checagens juntas são a defesa completa contra T-07-03-01"
  - "fila.enfileirar() usa transaction.atomic() por tentativa (não um único atomic reaproveitado) — um bloco abortado por OperationalError não pode ser reutilizado no SQLite"
  - "pyproject.toml ganhou sysdoc_web.processos.migrations e sysdoc_web.processos.management(.commands) em [tool.setuptools].packages — sem isso, uma instalação real via 'pip install -e \".[web]\"' (fora do ambiente de teste, onde o editable finder já mapeia o repo inteiro) não enxergaria a migração nem os management commands em produção/Docker (D-02)"
  - "MENSAGEM_FALHA é uma constante literal em runworker.py; qualquer exceção do pipeline (SystemExit ou Exception) vira essa mensagem fixa, com o traceback real só em logger.exception — nenhum nome de provedor, alvo de modelo ou caminho de arquivo chega a AnaliseJob.mensagem_erro (D-17)"

requirements-completed: [SYSD-22, SYSD-23]

duration: ~50min
completed: 2026-08-27
---

# Phase 7 Plan 03: Persistência de processo/análise e worker single-slot do DVI Summary

**`Processo`/`AnaliseJob` com `UniqueConstraint` condicional travam "uma análise por vez" no banco; `manage.py runworker` executa `sysdoc.prepare()`/`sysdoc_dvi.pipeline.executar_run()` como biblioteca, traduzindo o progresso para linguagem de processo e nunca deixando traceback técnico chegar ao pregoeiro.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 3/3
- **Files created:** 9
- **Files modified:** 1 (pyproject.toml)

## Accomplishments

- `Processo`/`AnaliseJob` persistem o estado de cada análise no SQLite (D-15); a `UniqueConstraint` `uma_analise_ativa_por_vez`, condicional a `status in (na_fila, em_execucao)`, é a implementação de "uma análise por vez" no nível do banco (D-14) — nenhuma segunda thread do futuro servidor de aplicação consegue driblá-la.
- `servicos.py` é a única camada que toca a pasta de um processo: `criar_pasta_do_processo` usa `sysdoc.ensure_project_structure` (layout canônico `documentos/`, `referencias/`, `output/`, `.sysdoc/config.yaml` — D-18), e `caminho_do_processo` combina validação de formato de slug com checagem de contenção pós-`resolve()` contra traversal.
- `fila.py` traduz toda colisão de escrita no SQLite — tanto a violação real da constraint (`IntegrityError`) quanto a contenção de lock sob concorrência (`OperationalError`, com retry curto de até 3 tentativas) — em `FilaOcupada`, uma mensagem em português; nunca um 500 genérico.
- `manage.py runworker --uma-vez` reivindica o próximo job atomicamente (`update()` condicional, não leitura+escrita separadas), chama `sysdoc.prepare()` e `sysdoc_dvi.pipeline.executar_run(progresso=...)` como módulos Python, grava o progresso traduzido (`progresso.texto_da_etapa`) a cada `EventoProgresso`, e qualquer falha — conhecida ou não — vira a mensagem fixa `MENSAGEM_FALHA`, com o traceback real só em `logger.exception`.
- `manage.py sanear_jobs` (e o próprio início do worker) marcam qualquer job `em_execucao` órfão como `interrompida`, com mensagem honesta mencionando o reinício (D-15).

## Task Commits

Each task was committed atomically:

1. **Task 1: Modelos Processo/AnaliseJob e camada de serviço de disco** - `51862e0` (feat)
2. **Task 2: Fila single-slot, worker e saneamento de subida** - `4db7de2` (feat)
3. **Task 3: Testes de fila, saneamento e ponte de biblioteca** - `3236060` (test)

## Files Created/Modified

- `sysdoc_web/processos/models.py` — `Processo`, `AnaliseJob`, `STATUS_ATIVOS`/`STATUS_FINAIS`, `UniqueConstraint uma_analise_ativa_por_vez`, propriedades `ativo`/`percentual`
- `sysdoc_web/processos/migrations/0001_initial.py` — migração gerada por `makemigrations`, confirmada sem pendência (`makemigrations --check --dry-run`)
- `sysdoc_web/processos/servicos.py` — `raiz_processos`, `caminho_do_processo` (validação de slug + contenção), `slug_disponivel`, `criar_pasta_do_processo`, `definir_tipo_verificacao`, `gravar_campos_despacho` (allowlist `CAMPOS_DESPACHO`), `caminhos`, `dados_consolidados`
- `sysdoc_web/processos/admin.py` — `Processo`/`AnaliseJob` somente leitura (sem add/change)
- `sysdoc_web/processos/fila.py` — `FilaOcupada`, `enfileirar`, `reivindicar_proximo`, `concluir`, `sanear_jobs_orfaos`
- `sysdoc_web/processos/progresso.py` — `ETAPA_PARA_TEXTO`, `texto_da_etapa`
- `sysdoc_web/processos/management/commands/runworker.py` — `Command` (`--intervalo`, `--uma-vez`), `_executar`, `MENSAGEM_FALHA`
- `sysdoc_web/processos/management/commands/sanear_jobs.py` — `Command` que chama `fila.sanear_jobs_orfaos()`
- `tests/test_web_fila.py` — 14 testes (10 exigidos pelo plano + 4 variações de parametrização/lock)
- `pyproject.toml` — `sysdoc_web.processos.migrations`/`management`/`management.commands` adicionados a `[tool.setuptools].packages`

## Decisions Made

Ver `key-decisions` no frontmatter. Destaque: a validação de slug por regex em `caminho_do_processo` não estava explícita na redação da `<action>` do plano (que só descreve a checagem `resultado.parent != raiz_processos()`), mas é necessária para que o próprio teste de traversal do plano (`"..%2Ffora"`) realmente levante `SuspiciousOperation` — esse valor não contém separador de caminho, então só a checagem de contenção pós-`resolve()` não o pegaria.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Verificação automatizada de `progresso.py` (Task 2) é auto-contraditória com a própria ação do plano**
- **Found during:** Task 2
- **Issue:** O acceptance criteria de Task 2 manda rodar `python3 -c "...assert not re.search(r'checklist|prompt|provedor|grounding|schema', t.split('ETAPA_PARA_TEXTO')[1].split('}')[0], re.I)"` para garantir "nenhum jargão nos textos de saída". Mas a própria `<action>` da mesma task exige que a chave `"checklist"` (idêntica ao valor de `sysdoc_dvi.progresso.ETAPAS`) exista no dicionário `ETAPA_PARA_TEXTO`. Como o recorte de texto inspecionado pelo script (`t.split('ETAPA_PARA_TEXTO')[1].split('}')[0]`) é o corpo literal do dicionário — chaves e valores juntos — a palavra `"checklist"` usada como **chave** obrigatória sempre aparece nesse recorte e a asserção falha, não importa o texto dos **valores** (o que realmente chega ao pregoeiro).
- **Fix:** Mantida a chave `"checklist"` exatamente como o plano manda (nenhum jargão nos **valores** do dicionário — os únicos textos que chegam à tela). Verificação corrigida manualmente: `re.search(r'checklist|prompt|provedor|grounding|schema', v, re.I)` para cada `v` em `ETAPA_PARA_TEXTO.values()` — nenhum valor contém jargão. A verificação literal do plano permanece impossível de satisfazer sem violar a própria especificação de chaves.
- **Files modified:** nenhum (nenhuma mudança de código; só a forma de verificar).
- **Verification:** `python3 -c "import sysdoc_web.processos.progresso as p; import re; assert not any(re.search(r'checklist|prompt|provedor|grounding|schema', v, re.I) for v in p.ETAPA_PARA_TEXTO.values())"` sai com código 0.
- **Committed in:** `4db7de2` (Task 2 commit)

**2. [Rule 2 - Missing Critical] `pyproject.toml` não listava os novos subpacotes (`migrations`, `management`, `management.commands`)**
- **Found during:** Task 1 e Task 2
- **Issue:** O editable install deste ambiente de desenvolvimento usa um finder que mapeia `sysdoc`/`sysdoc_dvi` diretamente à raiz do repo (mecanismo herdado de instalações anteriores), então os testes passam mesmo sem o ajuste. Mas uma instalação real de `pip install -e ".[web]"` a partir de `[tool.setuptools].packages` (o mecanismo declarado no `pyproject.toml`, usado pelo build real do Docker — D-02) só inclui subpacotes explicitamente listados; sem a listagem, a migração e os management commands ficariam ausentes de uma instalação de produção.
- **Fix:** Adicionadas as entradas `sysdoc_web.processos.migrations` (Task 1) e `sysdoc_web.processos.management`/`sysdoc_web.processos.management.commands` (Task 2) a `[tool.setuptools].packages`.
- **Files modified:** `pyproject.toml`
- **Verification:** `python3 manage.py makemigrations --check --dry-run` e `python3 manage.py sanear_jobs` funcionam nesta árvore; a listagem correta é o que garante o mesmo em uma instalação limpa via `pip install -e ".[web]"` dentro do container (plano 07-04).
- **Committed in:** `51862e0` (Task 1, entrada `migrations`) e `4db7de2` (Task 2, entradas `management`/`management.commands`)

---

**Total deviations:** 2 auto-fixed (1 Rule 3 - blocking na forma de verificar, sem mudança de código; 1 Rule 2 - missing critical, `pyproject.toml`)
**Impact on plan:** Nenhum impacto de comportamento de negócio. O primeiro é só uma correção da verificação (o código já estava correto); o segundo fecha uma lacuna real de empacotamento para o Docker do plano 07-04.

## Issues Encountered

- O `<verify>` de Task 1 (`python3 -m pytest tests/test_web_fila.py -q -k "modelo or servico or pasta"`) e de Task 2 (`python3 -m pytest tests/test_web_fila.py -q`) referenciam um arquivo que só é criado na Task 3 — mesma situação já registrada no `07-02-SUMMARY.md`. Substituí, nas Tasks 1 e 2, pela verificação estática (`makemigrations --check --dry-run`, `manage.py check`, `manage.py sanear_jobs`, greps de acceptance criteria) e deixei a suíte pytest completa para rodar ao final da Task 3, quando o arquivo de teste já existe.

## User Setup Required

None - nenhuma configuração de serviço externo é necessária. `manage.py runworker` roda como segundo processo no mesmo container (mecanismo concreto a ser conectado ao `docker-compose.yml` do plano 07-04).

## Next Phase Readiness

- `sysdoc_web.processos.fila`/`servicos`/`progresso` e `manage.py runworker`/`sanear_jobs` estão prontos para os planos seguintes: 07-05 (upload) vai chamar `servicos.criar_pasta_do_processo`/`definir_tipo_verificacao`; 07-06 (progresso) vai ler `AnaliseJob.etapa`/`percentual` por polling; 07-07 (resultado/revisão) vai ler `AnaliseJob.status`/`mensagem_erro` e só então chamar `sysdoc.criar_documento` (nunca o worker).
- `manage.py runworker` ainda não está conectado a um processo real do `docker-compose.yml` — isso é do plano 07-04 (Docker/entrypoint), que também deve chamar `manage.py sanear_jobs` antes de subir o servidor.
- Suíte completa: 588 passed, 1 skipped (era 574 passed, 1 skipped; +14 testes novos). Nenhum bloqueio para o plano 07-04.

---
*Phase: 07-interface-web-para-pregoeiros*
*Completed: 2026-08-27*

## Self-Check: PASSED

Todos os 9 arquivos criados citados neste SUMMARY foram confirmados em disco e os três hashes de commit de task (`51862e0`, `4db7de2`, `3236060`) foram confirmados em `git log --oneline --all`. A verificação corrigida de `ETAPA_PARA_TEXTO.values()` (deviation 1) também foi reexecutada e confirmada sem jargão.
