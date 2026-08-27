---
phase: 07-interface-web-para-pregoeiros
plan: 01
subsystem: api
tags: [python, dataclasses, refactor, biblioteca-chamavel, dvi-pipeline]

requires: []
provides:
  - "sysdoc.criar_documento() — cria o DOCX e devolve ResultadoCreate (saida/template/origem_template/substituicoes_pendentes) sem imprimir nada"
  - "sysdoc.localizar_html_analise() — devolve o Path do HTML mais recente ou None, sem parsear stdout de deploy"
  - "sysdoc.localizar_docx_despacho() — devolve o Path do despacho DOCX mais recente por nome ancorado, ou None"
  - "sysdoc_dvi.progresso.EventoProgresso / ETAPAS / SinkProgresso — contrato neutro de progresso, sem dependência de Django ou sysdoc"
  - "sysdoc_dvi.pipeline.executar_run(..., progresso=callback) — emite um EventoProgresso por linha relevante das nove etapas do pipeline"
affects: [07-03, 07-06, 07-07]

tech-stack:
  added: []
  patterns:
    - "Wrapper fino: função pública que só imprime + função 'lib' com o mesmo nome sem sufixo _cli que devolve dados (criar_documento/create)"
    - "_emitir(progresso, etapa, mensagem, atual=None, total=None) sempre faz print() e opcionalmente chama o callback dentro de try/except, isolando falha de terceiro do pipeline principal"

key-files:
  created:
    - sysdoc_dvi/progresso.py
    - tests/test_biblioteca_chamavel.py
  modified:
    - sysdoc.py
    - sysdoc_dvi/pipeline.py

key-decisions:
  - "ResultadoCreate é uma dataclass congelada com só 4 campos (saida/template/origem_template/substituicoes_pendentes) — nada de expor values/raw_xml internos ao chamador"
  - "localizar_docx_despacho() usa regex ancorada `^\\d{2}_.*_dvi_\\d{4}-\\d{2}-\\d{2}\\.docx$` e busca só em paths.root (sem rglob), para nunca servir um .docx de referencias/ como despacho gerado"
  - "sysdoc_dvi.cli.run() continua sem o parâmetro progresso — só chamadores de biblioteca (a futura view Django) o usam"

requirements-completed: [SYSD-19]

duration: 35min
completed: 2026-08-27
---

# Phase 7 Plan 01: Biblioteca chamável para sysdoc/sysdoc_dvi Summary

**`criar_documento()`, `localizar_html_analise()`, `localizar_docx_despacho()` e `executar_run(progresso=...)` tornam `sysdoc`/`sysdoc_dvi` chamáveis por um processo web sem `subprocess` e sem tocar em stdout, preservando byte a byte a saída da CLI existente.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 3/3
- **Files modified:** 3 (sysdoc.py, sysdoc_dvi/pipeline.py, tests/test_biblioteca_chamavel.py)
- **Files created:** 1 (sysdoc_dvi/progresso.py)

## Accomplishments

- `sysdoc.create()` deixou de ser a única forma de obter o DOCX gerado: `criar_documento()` devolve os caminhos como dados, e `create()` virou um wrapper que só imprime e delega.
- `deploy()` deixou de ser a única forma de descobrir qual HTML é o "ativo": `localizar_html_analise()` expõe a mesma lógica de quatro globs + mtime como função de biblioteca; `localizar_docx_despacho()` faz o mesmo para o despacho DOCX, com nome ancorado por regex para não confundir modelo de referência com artefato gerado.
- `sysdoc_dvi.pipeline.executar_run()` ganhou um canal de progresso estruturado (`EventoProgresso`) coerente com as nove etapas já impressas hoje, blindado contra callback que lança exceção (RF9 — um item/callback nunca derruba a análise).

## Task Commits

Each task was committed atomically:

1. **Task 1: Extrair criar_documento() de create()** - `fab209d` (feat)
2. **Task 2: localizar_html_analise() e refatoração de deploy()** - `55b79e5` (feat)
3. **Task 3: Callback de progresso estruturado no pipeline DVI** - `d56cfab` (feat)

_Nenhuma task foi TDD; todos os testes novos foram escritos junto com a implementação no mesmo commit de cada task._

## Files Created/Modified

- `sysdoc.py` — `ResultadoCreate` (dataclass), `criar_documento()`, `create()` (agora wrapper fino), `localizar_html_analise()`, `localizar_docx_despacho()`, `deploy()` (agora usa `localizar_html_analise`)
- `sysdoc_dvi/progresso.py` — `EventoProgresso`, `ETAPAS`, `SinkProgresso` (novo módulo, sem dependência de Django/sysdoc)
- `sysdoc_dvi/pipeline.py` — `_emitir()`, parâmetro `progresso=None` em `executar_run`/`_executar_run`, nove passos numerados + linhas de retomada/autocorreção/JSON gravado emitindo eventos tipados
- `tests/test_biblioteca_chamavel.py` — 11 testes novos cobrindo as três frentes (393 linhas)

## Decisions Made

- `ResultadoCreate` fica no mesmo módulo `sysdoc.py`, perto de `create`, em vez de um módulo `resultados.py` separado — evita um novo arquivo para uma dataclass de 4 campos usada só por `create`/`criar_documento`.
- O mapeamento de etapa por linha impressa seguiu exatamente a tabela do plano (`config`/`checklist`/`prepare`/`pecas`/`itens`/`sintese`/`montagem`/`validacao`/`render`) — nenhuma linha fora dessa lista (ex.: "Validação falhou...", "Relatório salvo em...") foi tocada, por não constar do mapeamento explícito do plano.
- `sysdoc_dvi.cli.run()` permanece sem o parâmetro `progresso` — confirmado por `grep -c "progresso" sysdoc_dvi/cli.py == 0`, condição que a Task 3 exige para não vazar o parâmetro novo para o dispatch do argparse.

## Deviations from Plan

None - plan executado exatamente como escrito.

## Issues Encountered

Nenhum problema bloqueante. Ao commitar por task, `sysdoc.py` tinha dois hunks independentes (Task 1 em `create`/`criar_documento`, Task 2 em `deploy`/`localizar_html_analise`) que precisaram ser aplicados em duas passadas — primeiro só a mudança de Task 1 sobre o arquivo original (`git checkout HEAD --`), depois a mudança de Task 2 — para preservar a atomicidade de commit por task exigida pelo protocolo de execução.

## User Setup Required

None - nenhuma configuração de serviço externo é necessária. Este plano não instala nenhum pacote novo (`pyproject.toml` intocado).

## Next Phase Readiness

Os três pontos de entrada que a camada Django dos planos 07-03/07-06/07-07 precisam já existem e são testados:

- `sysdoc.criar_documento(project, "dvi")` para gerar o despacho a partir de uma view (D-11: só chamado por uma ação deliberada do usuário, nunca automaticamente).
- `sysdoc.localizar_html_analise(paths)` / `sysdoc.localizar_docx_despacho(paths)` para a tela de resultado oferecer os dois downloads (D-13) sem regravar nada.
- `sysdoc_dvi.pipeline.executar_run(..., progresso=callback)` para o worker single-slot (D-14/D-16) gravar progresso no banco a cada `EventoProgresso`, sem WebSocket/SSE — só polling do lado do navegador.

Nenhum bloqueio para os próximos planos da fase.

---
*Phase: 07-interface-web-para-pregoeiros*
*Completed: 2026-08-27*

## Self-Check: PASSED

Todos os arquivos criados/modificados citados neste SUMMARY foram confirmados em disco e os três hashes de commit de task (`fab209d`, `55b79e5`, `d56cfab`) foram confirmados em `git log`.
