---
phase: 07-interface-web-para-pregoeiros
plan: 02
subsystem: infra
tags: [django, auth, settings, pytest, extra-opcional, sqlite]

requires:
  - phase: 07-interface-web-para-pregoeiros (plan 01)
    provides: "sysdoc.criar_documento()/localizar_html_analise()/localizar_docx_despacho() e sysdoc_dvi.pipeline.executar_run(progresso=...) chamáveis como biblioteca"
provides:
  - "Pacote Django `sysdoc_web` instalável via `pip install -e \".[web]\"`, com `manage.py`, settings endurecidas e app `processos`"
  - "Login obrigatório em `/entrar/`, logout só por POST em `/sair/`, sem nenhuma rota de auto-cadastro"
  - "Layout base (`base.html`) e folha de estilo própria (`sysdoc.css`) sem jargão de máquina e sem CDN externo"
  - "Bootstrap condicional do Django na suíte pytest (`tests/conftest.py`, fixture `django_web`) — suíte verde com e sem Django instalado"
affects: [07-03, 07-04, 07-05, 07-06, 07-07, 07-08]

tech-stack:
  added: ["django>=5.0,<6.0 (extra opcional 'web')", "gunicorn>=22.0 (extra opcional 'web')"]
  patterns:
    - "Extra opcional em pyproject.toml: dependencies base intocado, Django só entra via [project.optional-dependencies].web"
    - "Fixture pytest session-scoped que só importa Django dentro do próprio corpo da função (nunca no nível de módulo de conftest.py), com pytest.importorskip como guarda"
    - "Módulo de teste dedicado (tests/test_web_settings_sem_django.py) para os dois testes de leitura de arquivo que precisam rodar mesmo sem Django — pytest.importorskip no topo de um módulo aborta a coleta inteira dele, então testes que devem sobreviver sem a dependência não podem compartilhar módulo com esse guard"

key-files:
  created:
    - manage.py
    - sysdoc_web/settings.py
    - sysdoc_web/urls.py
    - sysdoc_web/wsgi.py
    - sysdoc_web/processos/apps.py
    - sysdoc_web/processos/urls.py
    - sysdoc_web/processos/views.py
    - sysdoc_web/templates/base.html
    - sysdoc_web/templates/registration/login.html
    - sysdoc_web/templates/processos/inicio.html
    - sysdoc_web/static/sysdoc.css
    - tests/conftest.py
    - tests/test_web_base.py
    - tests/test_web_settings_sem_django.py
  modified:
    - pyproject.toml

key-decisions:
  - "SECRET_KEY obrigatória via DJANGO_SECRET_KEY fora de DEBUG (ImproperlyConfigured em português); efêmera via secrets.token_urlsafe(50) só quando SYSDOC_WEB_DEBUG=1"
  - "SQLite com OPTIONS={'timeout': 20} — primeira metade da defesa de D-14 contra 'database is locked' sob concorrência de escrita"
  - "settings.py nunca contém OPENROUTER/OPENAI_API_KEY/GEMINI_API_KEY/ANTHROPIC_API_KEY/economico/forte — configuração de modelo é só de ~/.sysdoc/config.json, lida dentro do container (D-05/D-06)"
  - "urls.py raiz não inclui django.contrib.auth.urls (evita rotas de reset de senha por e-mail que não há como servir) — só LoginView/LogoutView explícitos, sem nenhuma rota de cadastro"
  - "Testes 4 e 5 da Task 3 (leitura de pyproject.toml/settings.py sem precisar de Django em runtime) foram para um módulo próprio (tests/test_web_settings_sem_django.py) sem importorskip, em vez de tests/test_web_base.py — confirmado experimentalmente que pytest.importorskip no nível de módulo aborta a coleta inteira do arquivo, então não é possível colocá-los 'acima do importorskip' no mesmo módulo e ainda assim rodarem sem Django"

requirements-completed: [SYSD-20, SYSD-21]

duration: ~30min
completed: 2026-08-27
---

# Phase 7 Plan 02: Esqueleto Django `sysdoc_web` Summary

**Pacote Django `sysdoc_web` como extra opcional (`pip install -e ".[web]"`), com settings endurecidas, autenticação obrigatória sem auto-cadastro e bootstrap condicional do Django na suíte pytest — suíte fica verde com e sem Django instalado.**

## Performance

- **Duration:** ~30 min
- **Completed:** 2026-08-27T06:28:42Z
- **Tasks:** 3/3
- **Files modified:** 1 (pyproject.toml)
- **Files created:** 14

## Accomplishments

- `pyproject.toml` ganhou o extra `web = ["django>=5.0,<6.0", "gunicorn>=22.0"]` sem tocar em `dependencies`; `sysdoc`/`sysdoc-dvi` continuam importáveis e funcionais com Django desinstalado (`pip3 uninstall django` + suíte completa verde comprovado durante a execução).
- `sysdoc_web/settings.py` endurecido: `SECRET_KEY` obrigatória fora de `DEBUG`, `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` explícitos por variável de ambiente, cookies `HttpOnly`/`SameSite=Lax`, `SECURE_CONTENT_TYPE_NOSNIFF`/`X_FRAME_OPTIONS=DENY`, limites de upload já parametrizados antes de existir qualquer view de upload, e nenhuma menção a chave de LLM.
- Login obrigatório: `/` redireciona 302 para `/entrar/` quando anônimo; `/sair/` só aceita POST; nenhuma rota de cadastro existe (`/cadastro/`, `/registro/`, `/accounts/signup/` → 404); `django.contrib.auth.urls` deliberadamente não incluído.
- `tests/conftest.py` traz o fixture `django_web` que faz o bootstrap completo (setup/teardown de banco de teste via `DiscoverRunner`) só quando um teste realmente pede — Django nunca é importado no nível de módulo do conftest.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extra opcional `web` e esqueleto do projeto Django** - `b615f1c` (feat)
2. **Task 2: Autenticação obrigatória sem auto-cadastro e layout base** - `4771f9c` (feat)
3. **Task 3: Bootstrap condicional do Django na suíte pytest** - `7843f2f` (test)

## Files Created/Modified

- `pyproject.toml` — extra `web`, `packages` estendido com `sysdoc_web`/`sysdoc_web.processos`
- `manage.py` — entrypoint administrativo do Django
- `sysdoc_web/settings.py` — configuração endurecida completa (ver Decisions)
- `sysdoc_web/urls.py` — rotas raiz: admin, entrar, sair (POST), include do app `processos`, estáticos em `DEBUG`
- `sysdoc_web/wsgi.py` — WSGI padrão
- `sysdoc_web/processos/apps.py`, `urls.py`, `views.py` — app inicial com a view `inicio` protegida por `@login_required`
- `sysdoc_web/templates/base.html`, `registration/login.html`, `processos/inicio.html` — layout em português, sem jargão de máquina, sem CDN externo
- `sysdoc_web/static/sysdoc.css` — folha de estilo própria e enxuta
- `tests/conftest.py` — fixture `django_web` (bootstrap condicional)
- `tests/test_web_base.py` — 4 testes: raiz exige login, login válido dá acesso, ausência de rota de cadastro, cabeçalhos de segurança
- `tests/test_web_settings_sem_django.py` — 2 testes de leitura de arquivo que rodam sem Django instalado

## Decisions Made

Ver `key-decisions` no frontmatter. Destaque: os testes 4/5 da Task 3 foram para um módulo próprio sem `importorskip` — confirmado por experimento isolado (`pytest.importorskip` numa linha do meio de um módulo faz a coleta inteira do arquivo ser pulada, inclusive testes definidos *antes* dessa linha), então a alternativa "acima do importorskip no mesmo arquivo" oferecida pelo plano não é tecnicamente viável com o guard no nível de módulo pedido para os demais testes. Isso adiciona um arquivo (`tests/test_web_settings_sem_django.py`) além dos dois listados no `files_modified` da Task 3 do plano — mudança pontual, dentro da liberdade que o próprio texto do plano concedeu ("em um módulo próprio sem importorskip, à sua escolha").

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Verificação da Task 2 adiada para depois da Task 3**
- **Found during:** Task 2
- **Issue:** O bloco `<verify>` da Task 2 manda rodar `python3 -m pytest tests/test_web_base.py -q`, mas esse arquivo só é criado na Task 3 — rodar naquele ponto falharia por arquivo inexistente, não por defeito de código.
- **Fix:** `python3 manage.py check` foi executado (e passou) ao final da Task 2; a suspensão de `pytest tests/test_web_base.py -q` para depois da Task 3 é a única ordem executável, já que o teste depende de `tests/conftest.py` que a própria Task 3 entrega.
- **Files modified:** nenhum — só reordenação de verificação, sem tocar em código.
- **Verificação:** `python3 -m pytest tests/test_web_base.py -q` rodou com sucesso (4 passed) assim que a Task 3 terminou.
- **Committed in:** não aplicável (não gerou mudança de arquivo, só de sequência de verificação).

**2. [Rule 3 - Blocking] Arquivo extra em tests/ além do `files_modified` da Task 3**
- **Found during:** Task 3
- **Issue:** Os testes 4 e 5 (leitura de `pyproject.toml`/`settings.py`) precisam rodar sem Django instalado, mas `pytest.importorskip("django")` no topo de `tests/test_web_base.py` aborta a coleta do módulo inteiro quando Django está ausente — inclusive testes definidos antes da linha do skip, verificado experimentalmente.
- **Fix:** Criado `tests/test_web_settings_sem_django.py`, sem nenhum `import django` nem `importorskip`, contendo só os dois testes de leitura de arquivo.
- **Files modified:** `tests/test_web_settings_sem_django.py` (novo)
- **Verificação:** `pip3 uninstall django` + `python3 -m pytest tests/ -q` → 570 passed, 2 skipped, código de saída 0 (nenhum erro); os dois testes de leitura de arquivo aparecem como `passed`, não `skipped`.
- **Committed in:** `7843f2f` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (ambas Rule 3 - blocking, nenhuma mudança de comportamento de negócio)
**Impact on plan:** Nenhum impacto de escopo; ambas resolvem sequenciamento/estrutura de teste dentro da liberdade textual do próprio plano. Nenhuma linha de produção (`sysdoc_web/`) foi alterada por causa delas.

## Issues Encountered

- O ambiente não tinha Django instalado e é "externally managed" (PEP 668); a instalação exigiu `pip3 install --break-system-packages` (mesmo padrão já em uso pelo `pytest`/`pypdf`/etc. globais do ambiente, que também não estão em venv). Resolvido sem impacto em `pyproject.toml` além do extra `web` já previsto pelo plano.

## User Setup Required

None - nenhuma configuração de serviço externo é necessária. `DJANGO_SECRET_KEY`, `SYSDOC_WEB_DATA_DIR` e demais variáveis de ambiente só são exigidas para rodar o servidor de verdade (planos seguintes/Docker), não para esta entrega.

## Next Phase Readiness

- `sysdoc_web` existe, `manage.py check` passa, login é obrigatório, não há rota de cadastro, e a suíte pytest tem o fixture `django_web` pronto para os planos 07-03 (fila/worker), 07-05 (upload) e 07-06/07-07 (progresso e resultado) escreverem seus próprios testes sobre a mesma base.
- Nenhum modelo Django foi criado neste plano (nenhuma migração pendente) — o primeiro `models.py` real (fila/job de análise) é do plano 07-03, conforme D-14/D-15 do `07-CONTEXT.md`.
- Nenhum bloqueio para o plano 07-03.

---
*Phase: 07-interface-web-para-pregoeiros*
*Completed: 2026-08-27*

## Self-Check: PASSED

Todos os 14 arquivos criados e a modificação em `pyproject.toml` foram confirmados em disco; os três hashes de commit de task (`b615f1c`, `4771f9c`, `7843f2f`) foram confirmados em `git log --oneline`.
