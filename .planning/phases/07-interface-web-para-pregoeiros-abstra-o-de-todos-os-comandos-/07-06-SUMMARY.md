---
phase: 07-interface-web-para-pregoeiros
plan: 06
subsystem: web
tags: [django, polling, javascript-vanilla, seguranca, fila]

requires:
  - phase: 07-interface-web-para-pregoeiros (plan 03)
    provides: "Modelos Processo/AnaliseJob, fila.enfileirar()/FilaOcupada, progresso.texto_da_etapa gravado pelo worker"
  - phase: 07-interface-web-para-pregoeiros (plan 05)
    provides: "views.novo_processo/verificacao (telas 1/2), TODO(07-06) em verificacao apontando para a rota processos:analise"
provides:
  - "views.analise/iniciar_analise/situacao_analise — tela 3 do fluxo do pregoeiro (D-09)"
  - "sysdoc_web/static/progresso.js — polling puro sem WebSocket/SSE (D-16), escrita no DOM só por textContent"
  - "Endpoint JSON /processos/<slug>/analise/situacao/ com chave fechada de 8 campos, Cache-Control: no-store"
affects: [07-07]

tech-stack:
  added: []
  patterns:
    - "url_resultado do JSON aponta para a própria rota processos:analise (reverse() no servidor) até o plano 07-07 criar processos:resultado — o JS navega para lá, e a view detecta status=concluida e redireciona de novo para processos:inicio; nenhum link morto nem URL hardcoded no front"
    - "Elemento raiz com data-url-situacao sempre presente na tela de análise (mesmo sem job ainda criado); situacao_analise devolve um estado neutro (status=sem_analise) em vez de erro quando não há job — o polling nunca quebra por corrida entre o primeiro carregamento da página e o clique em Iniciar análise"
    - "iniciarCiclo()/consultar() em progresso.js implementam pausa real (não apenas silêncio de fetch): a aba oculta não agenda novo setTimeout; visibilitychange dispara consulta imediata ao voltar"

key-files:
  created:
    - sysdoc_web/templates/processos/analise.html
    - sysdoc_web/static/progresso.js
    - tests/test_web_progresso.py
  modified:
    - sysdoc_web/processos/views.py
    - sysdoc_web/processos/urls.py
    - sysdoc_web/templates/processos/inicio.html
    - sysdoc_web/static/sysdoc.css

key-decisions:
  - "situacao_analise trata job is None devolvendo um JSON com status=sem_analise/percentual=0 em vez de 404 — o atributo data-url-situacao é sempre renderizado no elemento raiz da tela (mesmo antes de qualquer disparo), então o endpoint precisa responder de forma honesta a esse estado transitório sem nunca 500"
  - "url_resultado usa reverse('processos:analise', args=[slug]) enquanto processos:resultado (07-07) não existe — satisfaz o requisito de começar por '/processos/' e evita link morto; a própria view analise() já sabe redirecionar de um job concluído para processos:inicio com aviso, então a navegação do JS cai nesse mesmo caminho"
  - "progresso.js evita reproduzir os literais 'innerHTML'/'WebSocket'/'EventSource' até em comentários — os gates de grep do acceptance criteria (Task 2) inspecionam o arquivo inteiro, não só o código executável, então a primeira versão do comentário de topo falhava por citar exatamente esses termos como o que NÃO fazer"

requirements-completed: [SYSD-26]

duration: ~35min
completed: 2026-08-27
---

# Phase 7 Plan 06: Tela 3 — disparo da análise e progresso em tempo real por polling Summary

**`views.analise`/`iniciar_analise`/`situacao_analise` entregam a tela onde o pregoeiro acompanha a análise em português, por polling puro (`progresso.js`, sem WebSocket/SSE), com fila cheia e falha do pipeline sempre traduzidas em mensagem honesta e nunca em erro 500.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 3/3
- **Files created:** 3
- **Files modified:** 4

## Accomplishments

- `views.analise` substitui o `TODO(07-06)` deixado em `verificacao` (07-05): a tela 3 mostra o nome do processo, o tipo de contratação em rótulo (nunca `geral`/`tic` cru) e, dependendo do estado do último `AnaliseJob`, o botão de iniciar ou a região de progresso — sem nenhum recarregamento de página.
- `views.iniciar_analise` (`@require_POST`) recusa disparo sem `tipo_verificacao` definido e converte `FilaOcupada` em `messages.warning` com redirecionamento de volta — uma segunda análise concorrente nunca produz 500 (D-14), confirmado por `test_segunda_analise_mostra_aviso_e_nao_500`.
- `views.situacao_analise` (`@require_GET`) devolve um JSON de chave fechada (`status`, `situacao`, `etapa`, `percentual`, `concluida`, `sucesso`, `mensagem`, `url_resultado`) com `Cache-Control: no-store` e autorização por objeto (`get_object_or_404(..., criado_por=request.user)`) — nenhum nome de provedor, modelo, caminho de arquivo ou traceback pode vazar, porque o endpoint só ecoa `AnaliseJob.etapa`/`mensagem_erro`, campos já traduzidos pelo worker do plano 07-03 (D-17).
- `sysdoc_web/static/progresso.js` é JavaScript puro: lê `data-url-situacao`, faz `fetch` a cada 2 s, escreve `situacao`/`etapa`/`percentual` só por `textContent`/`style.width`, pausa de verdade quando a aba fica oculta (sem agendar novo ciclo) e retoma no `visibilitychange`, para após 3 falhas de rede consecutivas, e só navega para `url_resultado` depois de confirmar que a string começa por `/` — sem redirecionamento aberto (T-07-06-03).
- `processos/analise.html` e `processos/inicio.html` mostram a situação do processo em linguagem de gente; nenhum template do app contém `LLM`, `modelo`, `provedor`, `prompt`, `checklist`, `JSON`, `YAML`, `cache`, `token`, `grounding` ou `schema` — confirmado por grep de acceptance criteria.
- 10 testes novos em `tests/test_web_progresso.py` travam a recusa sem tipo, a criação do job na fila, a fila cheia sem 500, o JSON em português com o conjunto exato de chaves, a ausência de dado técnico numa falha, a URL de resultado, a interrupção honesta pós-reinício (D-15), a autorização por objeto (404 para outro usuário), a ausência de cache e a recusa de `GET` no disparo (405).

## Task Commits

Each task was committed atomically:

1. **Task 1: Disparo da análise e tela de progresso** - `4e80731` (feat)
2. **Task 2: Polling no navegador** - `b132a49` (feat)
3. **Task 3: Suíte de progresso, fila cheia e falha traduzida** - `cf99dcf` (test)

## Files Created/Modified

- `sysdoc_web/processos/views.py` — `analise`, `iniciar_analise`, `situacao_analise`; `verificacao` agora redireciona para `processos:analise`
- `sysdoc_web/processos/urls.py` — rotas `processos:analise`, `processos:iniciar_analise`, `processos:situacao_analise`
- `sysdoc_web/templates/processos/analise.html` — tela 3 (novo), com `data-url-situacao` e `<script src="{% static 'progresso.js' %}" defer>`
- `sysdoc_web/templates/processos/inicio.html` — mostra a situação do último job por processo e link para a tela de análise
- `sysdoc_web/static/progresso.js` — polling puro (novo)
- `sysdoc_web/static/sysdoc.css` — barra de progresso, bloco de erro, estado de espera
- `tests/test_web_progresso.py` — 10 testes (novo)

## Decisions Made

Ver `key-decisions` no frontmatter. Destaque: como `processos:resultado` (07-07) ainda não existe, `url_resultado` no JSON aponta para a própria `processos:analise` — a view já sabe redirecionar um job concluído para `processos:inicio` com aviso, então a navegação do JS não produz link morto nem exige um placeholder próprio.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `{% load static %}` antes de `{% extends %}` quebra a renderização do template**
- **Found during:** Task 3 (ao rodar a suíte nova, dois testes que exercitam `views.analise`/`views.iniciar_analise` via `follow=True` derrubaram a página com `TemplateSyntaxError`)
- **Issue:** `analise.html` foi escrito na Task 1 com `{% load static %}` na primeira linha e `{% extends "base.html" %}` na segunda — o Django exige que `{% extends %}` seja a primeira tag do template quando presente.
- **Fix:** Invertida a ordem: `{% extends "base.html" %}` primeiro, `{% load static %}` depois (mesmo padrão de `base.html`, que só usa `load` porque não estende nada).
- **Files modified:** `sysdoc_web/templates/processos/analise.html`
- **Verification:** `python3 -m pytest tests/test_web_progresso.py -q` → 10 passed (antes: 2 failed, 8 passed); suíte completa 619 passed, 1 skipped.
- **Committed in:** `cf99dcf` (Task 3, junto com o teste que expôs o bug — o próprio acceptance criteria de Task 1, que só rodava `manage.py check` e greps estáticos, não exercitava a renderização real do template)

**2. [Rule 3 - Blocking] Comentários de `progresso.js` citando os literais proibidos pelo próprio gate de grep da Task 2**
- **Found during:** Task 2
- **Issue:** O acceptance criteria exige `grep -c "innerHTML"` == 0 e `grep -ciE "websocket|eventsource|https://"` == 0 no arquivo inteiro, mas a primeira versão do comentário de topo explicava a decisão de design citando literalmente `innerHTML`, `WebSocket` e `EventSource` como o que **não** fazer — o texto explicativo colidia com a própria verificação automatizada.
- **Fix:** Reescrito o comentário sem reproduzir os termos proibidos (ex.: "sem canal push do navegador" em vez de nomear as APIs), preservando a explicação do porquê.
- **Files modified:** `sysdoc_web/static/progresso.js`
- **Verification:** greps de acceptance criteria da Task 2, todos em `0`/`>=1` conforme esperado.
- **Committed in:** `b132a49` (Task 2)

---

**Total deviations:** 2 auto-fixed (1 Rule 1 - bug real de renderização de template, corrigido e travado pela suíte nova; 1 Rule 3 - blocking, sem mudança de comportamento, só reescrita de comentário)
**Impact on plan:** Nenhum impacto de escopo. A primeira correção é um bug genuíno que só a suíte pytest (não os greps estáticos do próprio plano) conseguia expor — reforça por que a Task 3 roda a suíte completa antes de fechar o plano.

## Issues Encountered

- O `<verify>` da Task 1 (`pytest ... -k "iniciar or situacao or fila"`) e da Task 2 (checagem de sintaxe/greps) não exercitam a renderização real de `analise.html` — só a Task 3, ao rodar os testes de ponta a ponta via `Client.post(..., follow=True)`, expôs o `TemplateSyntaxError` de ordem de tags. Mesma classe de lacuna já registrada nos summaries de 07-02/07-03/07-05 sobre verificação incompleta de tasks anteriores à criação do arquivo de teste.

## User Setup Required

None - nenhuma configuração de serviço externo é necessária.

## Next Phase Readiness

- `views.analise`/`iniciar_analise`/`situacao_analise`, `progresso.js` e o padrão `data-url-situacao` estão prontos para o plano 07-07 (tela 4 — resultado e despacho): quando `processos:resultado` existir, basta trocar o `reverse("processos:analise", ...)` de `url_resultado` para a nova rota; a view `analise()` já tem o `TODO(07-07)` explícito no ponto exato onde o redirecionamento de job concluído deve mudar.
- `AnaliseJob.mensagem_erro` e `etapa` continuam sendo os únicos campos técnicos que chegam ao JSON — qualquer tela futura que precise de mais detalhe (ex.: relatório de execução do DVI) precisa de um campo novo e deliberado, não de reaproveitar esses dois.
- Suíte completa: 619 passed, 1 skipped (era 609 passed, 1 skipped; +10 testes novos). Nenhum bloqueio para o plano 07-07.

---
*Phase: 07-interface-web-para-pregoeiros*
*Completed: 2026-08-27*

## Self-Check: PASSED

Todos os 8 arquivos citados neste SUMMARY (3 criados, 4 modificados, o próprio SUMMARY) foram confirmados em disco e os três hashes de commit de task (`4e80731`, `b132a49`, `cf99dcf`) foram confirmados em `git log --oneline --all`.
