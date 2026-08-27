---
phase: 07-interface-web-para-pregoeiros
plan: 07
subsystem: web
tags: [django, xss-defense, path-traversal, revisao-humana, downloads]

requires:
  - phase: 07-interface-web-para-pregoeiros (plan 01)
    provides: "sysdoc.criar_documento()/localizar_html_analise()/localizar_docx_despacho() chamáveis como biblioteca"
  - phase: 07-interface-web-para-pregoeiros (plan 03)
    provides: "servicos.caminhos()/dados_consolidados()/gravar_campos_despacho(), caminho_do_processo() com contenção"
  - phase: 07-interface-web-para-pregoeiros (plan 06)
    provides: "views.analise/situacao_analise com TODO(07-07) apontando para a rota de resultado"
provides:
  - "views.resultado — tela 4 do fluxo: apontamentos em português, painel de contagens, downloads"
  - "views.gerar_despacho — única porta de entrada de sysdoc.criar_documento na aplicação web, sob POST com aceite explícito (D-11)"
  - "views.baixar_analise/baixar_despacho + downloads.entregar() — os dois downloads endurecidos (D-13)"
  - "sysdoc_web.processos.apontamentos — leitura segura e tradução do dados_consolidados.json"
affects: []

tech-stack:
  added: []
  patterns:
    - "apontamentos.py nunca devolve HTML — só dict/list/str que o template Django auto-escapa; rótulos em português substituem por completo o enum cru do schema"
    - "_contexto_resultado() é o único ponto que monta o contexto da tela de resultado, reusado por resultado (GET) e gerar_despacho (POST inválido) — evita duas fontes de verdade para o mesmo template"
    - "downloads.entregar() é o único ponto que serve arquivo do disco para o navegador nesta app: contenção via Path.is_relative_to antes de qualquer outra checagem, sempre attachment, nunca renderização na origem autenticada"

key-files:
  created:
    - sysdoc_web/processos/apontamentos.py
    - sysdoc_web/processos/downloads.py
    - sysdoc_web/templates/processos/resultado.html
    - tests/test_web_resultado.py
  modified:
    - sysdoc_web/processos/views.py
    - sysdoc_web/processos/urls.py
    - sysdoc_web/processos/forms.py
    - sysdoc_web/static/sysdoc.css

key-decisions:
  - "RevisaoDespachoForm constrói os campos de dispatch iterando sysdoc.CAMPOS_DESPACHO dentro de __init__ e substituindo self.fields por um dict novo, em vez de declarar os sete CharField como atributos de classe — se a tupla da CLI mudar, o formulário acompanha sem edição nesta tela"
  - "gerar_despacho encapsula SystemExit e Exception na mesma cláusula except (tupla, não herança comum) — criar_documento pode levantar qualquer um dos dois conforme a falha (template ausente vs. erro de runtime), e ambos precisam virar a mesma mensagem genérica em português (D-17)"
  - "downloads.entregar() checa contenção de caminho (Path.is_relative_to) antes de checar existência do arquivo — um caminho fora da raiz nunca chega a tocar o disco para saber se existe"
  - "Comentários/docstrings evitam os literais 'modelo_ia' e 'inline' mesmo em prosa explicativa — os próprios gates de grep do acceptance criteria inspecionam o arquivo inteiro, mesma armadilha já documentada no summary do plano 07-06"
  - "Task 1/2/3 foram commitadas em ordem, mas como o template e a view de Task 1 já precisavam do RevisaoDespachoForm (Task 2) para renderizar a seção de despacho, o commit de Task 1 foi construído numa versão intermediária sem essa seção — reaplicada no commit de Task 2 — para manter cada commit funcionalmente coerente (mesmo padrão de duas passadas documentado no summary do plano 07-01)"

requirements-completed: [SYSD-27, SYSD-28]

duration: ~50min
completed: 2026-08-27
---

# Phase 7 Plan 07: Tela 4 — apontamentos, revisão humana bloqueante e downloads Summary

**`views.resultado`/`gerar_despacho`/`baixar_analise`/`baixar_despacho` fecham o fluxo do pregoeiro: apontamentos traduzidos para português sem expor JSON ou modelo, `sysdoc.criar_documento` só é chamado por um POST explícito com aceite do pregoeiro, e os dois downloads são servidos como anexo com cabeçalhos endurecidos e contenção de caminho.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 3/3
- **Files created:** 4
- **Files modified:** 4

## Accomplishments

- `sysdoc_web/processos/apontamentos.py` traduz o `dados_consolidados.json` para a tela sem nunca devolver HTML: `resumo_para_tela()` monta contagens por classificação e identifica o processo (campo ausente vira `"não identificado"`, nunca `KeyError`); `itens_para_tela()` devolve os apontamentos ordenados por documento e id, sem `modelo_ia` nem qualquer metadado de execução (D-06).
- `views.analise` deixou de ter o `TODO(07-07)`: job concluído redireciona direto para `processos:resultado`, e `situacao_analise` aponta `url_resultado` para a mesma rota — a tela 3 (plano 06) e a tela 4 agora estão de fato conectadas.
- `views.resultado` mostra os apontamentos, o painel de contagens e os downloads disponíveis; quando a análise ainda não produziu `dados_consolidados.json`, mostra a mensagem honesta em vez de tentar montar contagem sobre nada.
- `forms.RevisaoDespachoForm` constrói os sete campos institucionais iterando `sysdoc.CAMPOS_DESPACHO` (nunca redigitando a tupla) e exige `confirmo=True` — campo em branco continua virando `[PREENCHER: <campo>]` no Word (D-12), e a ausência do aceite é o próprio bloqueio de D-11.
- `views.gerar_despacho` é a **única** porta de entrada de `sysdoc.criar_documento` na aplicação web: recusa sem análise concluída, recusa (sem gerar nada) quando `confirmo` não está marcado ou o formulário é inválido, grava os campos institucionais no bloco `despacho:` do `.sysdoc/config.yaml` via `servicos.gravar_campos_despacho`, e só então chama `criar_documento(..., "dvi")` — falha vira mensagem genérica em português, traceback só no log do servidor (D-17). O worker (`manage.py runworker`) continua sem nenhuma referência a `criar_documento`.
- `sysdoc_web/processos/downloads.py` serve os dois downloads sempre como anexo: `Path.is_relative_to` contra a pasta do processo antes de qualquer outra checagem (`SuspiciousOperation` se fora), `Http404` se ausente, cabeçalhos `X-Content-Type-Options: nosniff`, `Content-Security-Policy: sandbox`, `Referrer-Policy: no-referrer` e `Cache-Control: private, no-store`; nome do arquivo passa por `sysdoc.sanitize_filename`. Não existe rota para `dados_consolidados.json` (D-13).
- `tests/test_web_resultado.py` (13 testes) prova, contra o caminho de produção real (sem mock de `criar_documento`): rótulos em português sem o enum cru, ausência de JSON/modelo no HTML, escape do `parecer` contra XSS injetado, que a análise concluída **não** gera DOCX sozinha, que POST sem `confirmo` não gera nada, que POST com `confirmo` gera o DOCX real casando o padrão de nome ancorado e grava `unidade` no `config.yaml`, que campo em branco vira o marcador, os dois downloads (attachment, tipo de conteúdo correto, 404 por ausência/outro usuário), ausência de rota para o JSON, e a recusa de `downloads.entregar()` para caminho fora da raiz.

## Task Commits

Each task was committed atomically:

1. **Task 1: Leitura dos apontamentos e tela de resultado** - `aa7b8c9` (feat)
2. **Task 2: Revisão humana bloqueante e geração do despacho** - `e526443` (feat)
3. **Task 3: Downloads endurecidos e suíte da tela de resultado** - `5fec893` (test)

## Files Created/Modified

- `sysdoc_web/processos/apontamentos.py` — `ROTULO_CLASSIFICACAO`/`ROTULO_RISCO`, `resumo_para_tela()`, `itens_para_tela()` (novo)
- `sysdoc_web/processos/downloads.py` — `entregar()` com contenção de caminho e cabeçalhos endurecidos (novo)
- `sysdoc_web/templates/processos/resultado.html` — tela 4: resumo, painel de contagens, apontamentos, formulário de revisão, downloads (novo)
- `tests/test_web_resultado.py` — 13 testes (novo)
- `sysdoc_web/processos/views.py` — `resultado`, `_contexto_resultado`, `gerar_despacho`, `baixar_analise`, `baixar_despacho`; `analise`/`situacao_analise` atualizados para apontar para `processos:resultado`
- `sysdoc_web/processos/urls.py` — rotas `processos:resultado`, `processos:gerar_despacho`, `processos:baixar_analise`, `processos:baixar_despacho`
- `sysdoc_web/processos/forms.py` — `RevisaoDespachoForm`, `ROTULOS_CAMPOS_DESPACHO`
- `sysdoc_web/static/sysdoc.css` — painel de contagens, cartões de apontamento, lista de downloads

## Decisions Made

Ver `key-decisions` no frontmatter. Destaques:

- A revisão humana bloqueante foi exercitada de ponta a ponta contra o template DVI real do repositório (`templates/dvi/despacho_geral.docx`), não um substituto — a suíte prova que o DOCX gerado pelo POST confirmado é byte-real, casando o padrão de nome ancorado `^\d{2}_.*_dvi_\d{4}-\d{2}-\d{2}\.docx$` usado por `sysdoc.localizar_docx_despacho`.
- `_contexto_resultado()` é reusado tanto pelo GET de `resultado` quanto pelo POST inválido de `gerar_despacho` — evita duas fontes de verdade para o mesmo template quando o formulário volta com erro.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Docstring de `apontamentos.py` citando o literal `modelo_ia` proibido pelo próprio gate de grep da Task 1**
- **Found during:** Task 1 (verificação de acceptance criteria)
- **Issue:** O acceptance criteria exige `grep -c "modelo_ia" sysdoc_web/processos/apontamentos.py sysdoc_web/templates/processos/resultado.html` == 0 (contagem somada), mas a docstring de `itens_para_tela()` explicava a exclusão citando literalmente `modelo_ia` como o que **não** incluir — o texto explicativo colidia com a própria verificação automatizada.
- **Fix:** Reescrito para "o identificador do provedor de IA usado" em vez do nome literal do campo, preservando a explicação do porquê (D-06).
- **Files modified:** `sysdoc_web/processos/apontamentos.py`
- **Verification:** `grep -c "modelo_ia" sysdoc_web/processos/apontamentos.py sysdoc_web/templates/processos/resultado.html` → `0` em ambos.
- **Committed in:** `aa7b8c9` (Task 1)

**2. [Rule 3 - Blocking] Docstring de `downloads.py` citando o literal `inline` proibido pelo próprio gate de grep da Task 3**
- **Found during:** Task 3
- **Issue:** O acceptance criteria exige `grep -c "inline" sysdoc_web/processos/downloads.py` == 0, mas a primeira versão do docstring explicava a decisão de segurança citando "nunca `inline`" — mesma classe de armadilha já documentada no summary do plano 07-06 para `progresso.js`.
- **Fix:** Reescrito sem o literal proibido, preservando a explicação (o HTML da análise nunca é servido "para renderização dentro da origem autenticada").
- **Files modified:** `sysdoc_web/processos/downloads.py`
- **Verification:** `grep -c "inline" sysdoc_web/processos/downloads.py` → `0`; `grep -c "attachment"` → `1`.
- **Committed in:** `5fec893` (Task 3)

---

**Total deviations:** 2 auto-fixed (ambas Rule 3 - blocking, sem mudança de comportamento, só reescrita de comentário/docstring para não colidir com o próprio gate de grep do acceptance criteria da task).
**Impact on plan:** Nenhum impacto de escopo ou comportamento.

## Issues Encountered

- A Task 1 do plano já previa, na própria ação descrita, que a tela de resultado deveria renderizar "o formulário de revisão (Task 2)" — ou seja, o template e a view de Task 1 dependem estruturalmente de `RevisaoDespachoForm`, que só é criado na Task 2. Para manter os três commits atômicos e cada um funcionalmente coerente (sem `ImportError` em `manage.py check`), o commit de Task 1 foi construído numa versão intermediária do template/view sem a seção de despacho, reaplicada com a seção completa no commit de Task 2 — mesmo padrão de "duas passadas" já documentado no summary do plano 07-01 para preservar atomicidade quando duas tasks tocam o mesmo arquivo com dependência real entre si.

## User Setup Required

None - nenhuma configuração de serviço externo é necessária.

## Next Phase Readiness

- O fluxo do pregoeiro está fechado ponta a ponta: upload (07-05) → tipo de verificação (07-05) → análise com progresso (07-06) → resultado, revisão bloqueante e downloads (07-07). Falta só o plano 07-08 (documentação/fechamento da fase, conforme ROADMAP).
- `views.gerar_despacho` é o único ponto de chamada de `sysdoc.criar_documento` em toda a aplicação web — confirmado por grep (`== 1` em `views.py`, `== 0` em `runworker.py`) e por teste (`test_analise_concluida_nao_gera_docx_sozinha`).
- Suíte completa: 632 passed, 1 skipped (era 619; +13 testes novos). Nenhum bloqueio para o plano 07-08.

---
*Phase: 07-interface-web-para-pregoeiros*
*Completed: 2026-08-27*

## Self-Check: PASSED

Todos os 8 arquivos citados neste SUMMARY (4 criados, 4 modificados) foram confirmados em disco e os três hashes de commit de task (`aa7b8c9`, `e526443`, `5fec893`) foram confirmados em `git log --oneline --all`.
