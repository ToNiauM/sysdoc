---
phase: 07-interface-web-para-pregoeiros
plan: 04
subsystem: infra
tags: [docker, docker-compose, gunicorn, entrypoint, single-service]

requires:
  - phase: 07-interface-web-para-pregoeiros (plan 02)
    provides: "sysdoc_web/settings.py lendo DJANGO_SECRET_KEY, SYSDOC_WEB_DEBUG, SYSDOC_WEB_ALLOWED_HOSTS, SYSDOC_WEB_DATA_DIR etc.; extra opcional 'web' em pyproject.toml"
  - phase: 07-interface-web-para-pregoeiros (plan 03)
    provides: "manage.py sanear_jobs e manage.py runworker --intervalo N, worker single-slot chamando sysdoc/sysdoc_dvi como biblioteca"
provides:
  - "Dockerfile de estágio único (python:3.12-slim), usuário não-root sysdoc (UID/GID 10001), sem nenhuma chave de API embutida"
  - "docker/entrypoint.sh: segredo persistido no volume + migrate + collectstatic + sanear_jobs + um único laço de runworker + exec gunicorn --workers 1 --threads 4"
  - "docker-compose.yml com um único serviço 'web', volume nomeado sysdoc-dados e montagem :ro de ~/.sysdoc"
  - ".env.exemplo documentando variáveis sem segredo real, incluindo nota operacional sobre permissão de leitura de ~/.sysdoc"
  - "tests/test_web_docker.py — 8 testes estáticos travando D-02/D-05/D-14 sem depender de Docker nem de Django"
affects: [07-05, 07-06, 07-07, 07-08]

tech-stack:
  added: []
  patterns:
    - "Segredo Django gerado uma única vez e persistido em ${SYSDOC_WEB_DATA_DIR}/secret_key (permissão 600) — não regenerado a cada subida"
    - "Worker single-slot como laço de shell em segundo plano dentro do mesmo container (`while true; do runworker; sleep 5; done &`), nunca um segundo serviço no compose"
    - "gunicorn --workers 1 --threads 4 documentado inline como a amarração a D-14: threads servem só polling/upload, nunca a análise"

key-files:
  created:
    - Dockerfile
    - .dockerignore
    - docker/entrypoint.sh
    - docker-compose.yml
    - .env.exemplo
    - tests/test_web_docker.py
  modified:
    - .gitignore

key-decisions:
  - "Base python:3.12-slim, estágio único (sem multi-stage) — pip install -e '.[web]' é a única instalação de pacote, sem curl|sh nem pacote fora do índice padrão (T-07-04-SC)"
  - "Volume de dados deve ser nomeado (Docker named volume), não bind mount de diretório do host: testado manualmente que um named volume vazio herda a ownership sysdoc:sysdoc do diretório /dados criado no build (cópia do conteúdo inicial da imagem para o volume na primeira montagem), enquanto um bind mount de diretório do host preserva o UID do host e quebra a escrita do UID 10001 do container"
  - "Nota operacional adicionada a .env.exemplo: a montagem :ro de ~/.sysdoc só funciona se o diretório tiver permissão de leitura para 'outros' (chmod o+rx) — testado manualmente que uma pasta 700 (padrão comum) fica ilegível para o UID 10001 do container mesmo com a montagem :ro correta"
  - "env_file com 'required: false' no docker-compose.yml — docker compose up funciona sem nenhum .env presente, conforme D-02"

requirements-completed: [SYSD-24]

duration: ~25min
completed: 2026-08-27
---

# Phase 7 Plan 04: Empacotamento Docker — `docker compose up` como único comando de subida Summary

**`Dockerfile` (estágio único, usuário não-root) + `docker/entrypoint.sh` (segredo persistido, migrate, collectstatic, saneamento de jobs órfãos e um único worker antes do `exec gunicorn --workers 1 --threads 4`) + `docker-compose.yml` de um serviço só — build, subida via `docker run` equivalente e reinício com dados persistidos verificados manualmente ponta a ponta.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2/2
- **Files created:** 6
- **Files modified:** 1 (`.gitignore`)

## Accomplishments

- `Dockerfile` constrói a imagem em estágio único sobre `python:3.12-slim`, cria o usuário não-root `sysdoc` (UID/GID 10001), instala apenas `ca-certificates` como pacote de sistema, roda `pip install -e ".[web]"` e não contém `ENV`/`ARG` com nome ou valor de chave de API em nenhuma linha (T-07-04-01, verificado por grep e por leitura).
- `.dockerignore` garante que `processo-teste/`, `Referencias/`, `.sysdoc/`, `.git/` e demais material real do usuário nunca entram no contexto de build (T-07-04-02).
- `docker/entrypoint.sh` executa, nesta ordem obrigatória, segredo → `django --version` → `migrate` → `collectstatic` → `sanear_jobs` (D-15) → um único laço de `runworker` em segundo plano → `exec gunicorn --workers 1 --threads 4` (D-14). O comentário inline no `--threads 4` documenta explicitamente por que ele é seguro (defesas dos planos 07-02/07-03 contra `OperationalError` do SQLite).
- `docker-compose.yml` declara um único serviço `web`, sem `redis`/`celery`/`rabbit`/`broker`, com volume nomeado `sysdoc-dados:/dados` e montagem somente-leitura `${HOME}/.sysdoc:/home/sysdoc/.sysdoc:ro`; nenhum valor de ambiente contém segredo literal — as quatro chaves de provedor são interpolação pura (`${VAR:-}`).
- `.env.exemplo` documenta as variáveis relevantes em português, sem valor real, incluindo a observação operacional sobre `~/.sysdoc/config.json` como caminho preferido para as chaves de API.
- `tests/test_web_docker.py` trava as 8 invariantes estáticas do plano (serviço único, ausência de broker, ausência de segredo literal, volume de dados, montagem `:ro` da config, ordem migrate/sanear_jobs/runworker antes do gunicorn, `--workers 1`/`--threads 4`, `.dockerignore` exclui material do usuário).

## Task Commits

Each task was committed atomically:

1. **Task 1: Dockerfile, .dockerignore e entrypoint de subida** - `1bc85ee` (feat)
2. **Task 2: docker-compose.yml, .env.exemplo e testes de configuração** - `f0617fe` (feat)
3. **Deviation (Rule 2 - missing critical) — nota operacional de permissão em ~/.sysdoc** - `60fc0fd` (docs)

## Files Created/Modified

- `Dockerfile` — imagem única, usuário `sysdoc` (UID/GID 10001), `pip install -e ".[web]"`, `EXPOSE 8000`, `ENTRYPOINT ["/app/docker/entrypoint.sh"]`
- `.dockerignore` — exclui `.git`, `.planning`, `__pycache__`, `dados_web`, `processo-teste`, `processo-01`, `output`, `documentos`, `Referencias`, `referencias`, `.sysdoc`, `*.sqlite3`, `.env`, `.pytest_cache`, `.ruff_cache`, `.opencode`, `.claude`
- `docker/entrypoint.sh` — segredo persistido (`600`), `django --version`, `migrate --noinput`, `collectstatic --noinput`, `sanear_jobs`, laço único de `runworker`, `exec gunicorn ... --workers 1 --threads 4`
- `docker-compose.yml` — serviço `web` único, `build: .`, `ports: ["8000:8000"]`, `restart: unless-stopped`, `env_file` opcional, `environment` interpolado, `volumes: sysdoc-dados:/dados` + `${HOME}/.sysdoc:/home/sysdoc/.sysdoc:ro`
- `.env.exemplo` — variáveis documentadas sem valor real + nota de permissão de `~/.sysdoc`
- `tests/test_web_docker.py` — 8 testes estáticos de leitura de arquivo (compose + entrypoint + dockerignore)
- `.gitignore` — `.env` adicionado

## Decisions Made

Ver `key-decisions` no frontmatter. Destaque: a validação manual com `docker run` mostrou uma diferença de comportamento relevante para operação real — **volume nomeado** funciona de imediato (herda a ownership `sysdoc:sysdoc` do `/dados` criado no build, por cópia de conteúdo inicial na primeira montagem), enquanto um **bind mount de diretório do host** preserva a ownership do host e falha com `Permission denied` para o UID 10001 do container. O plano já pedia volume nomeado (`sysdoc-dados`) para os dados e bind mount só para `~/.sysdoc` (que é somente-leitura e não precisa de escrita pelo container), então o `docker-compose.yml` entregue já está correto — a observação foi útil para confirmar a escolha, não para mudá-la.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Montagem `:ro` de `~/.sysdoc` pode ficar ilegível pelo UID do container**
- **Found during:** Verificação manual de Task 2 (`docker run` com bind mount real de `~/.sysdoc:ro`)
- **Issue:** O diretório real `~/.sysdoc` do ambiente de teste tem permissão `700` (só o dono do host pode ler/listar). Montado como `:ro` no container, o UID 10001 (`sysdoc`) recebe `Permission denied` até para `ls`, mesmo com a montagem tecnicamente correta — o `carregar_config_dvi()`/`chave_do_provedor()` do motor DVI (que leem `~/.sysdoc/config.json` dentro do container) falhariam silenciosamente com "arquivo ausente" em vez de indicar o problema real de permissão.
- **Fix:** Nenhuma mudança de código (não é algo que o `Dockerfile`/`docker-compose.yml` possam corrigir — é permissão do lado do host, sob controle do administrador). Adicionada nota operacional a `.env.exemplo` orientando `chmod o+rx ~/.sysdoc && chmod o+r ~/.sysdoc/config.json` antes de subir.
- **Files modified:** `.env.exemplo`
- **Verification:** Reexecutado o mesmo `docker run` com bind mount real; a nota documenta o comportamento observado e o comando de correção.
- **Committed in:** `60fc0fd`

---

**Total deviations:** 1 auto-fixed (Rule 2 - missing critical, documentação apenas — nenhuma mudança de comportamento de código)
**Impact on plan:** Nenhum. A arquitetura do compose já estava correta (volume nomeado para dados, bind mount somente-leitura para config do administrador); a lacuna era só a ausência de aviso sobre um pré-requisito de permissão no host.

## Issues Encountered

- **Ambiente de execução não permitiu validar `docker compose up -d` ao vivo até o fim.** Duas limitações do host compartilhado, não do `docker-compose.yml` entregue:
  1. `docker network create` para a rede padrão do projeto (`sysdoc_default`) falhou com "all predefined address pools have been fully subnetted" — há ~25 redes Docker de outros projetos já ativas neste host compartilhado, esgotando os pools automáticos do daemon.
  2. Contornando isso com uma rede externa de subnet explícita, a publicação da porta `8000:8000` falhou com "port is already allocated" — outro serviço no mesmo host já ocupa a porta 8000.
  - **O que foi verificado como substituto equivalente, com sucesso:**
    - `docker build -t sysdoc-web:teste .` → código 0 (imagem construída, ~13s de instalação).
    - `docker compose config` → código 0, YAML resolvido corretamente (um serviço, volume nomeado, montagem `:ro`, envs interpoladas sem segredo).
    - `docker run` direto da imagem construída (mesmo `ENTRYPOINT`, mesmas variáveis de ambiente, volume nomeado no lugar do volume do compose, porta livre `18000`/`18001` no lugar de `8000`) → log completo mostrando `migrate` (19 migrações aplicadas), `collectstatic` (128 arquivos), `sanear_jobs` (0 órfãos), início do worker e `gunicorn` com `--workers 1`, `curl` retornando `302` em `/`.
    - `docker restart` do mesmo container → segredo (`secret_key`) e banco (`db.sqlite3`) preservados no volume nomeado; segunda subida não reaplicou migrações (`No migrations to apply`) e reconfirmou `302` em `/`.
    - Bind mount real de `~/.sysdoc:ro` testado (ver Deviation 1 acima) — montagem correta, permissão do host insuficiente no ambiente de teste (esperado, não é defeito do compose).
  - **O que não foi possível confirmar ao vivo:** o comando exato `docker compose up -d` criando a rede/serviço nomeados pelo compose, e `docker compose exec web python manage.py createsuperuser`. Ambos dependem apenas de infraestrutura de rede/porta do host, já provada equivalente via `docker run` direto com a mesma imagem e o mesmo entrypoint — não há motivo para crer que o comportamento mudaria sob `docker compose up` num host com recursos de rede/porta disponíveis.

## User Setup Required

- Antes de rodar `docker compose up` em produção real, o administrador deve garantir que `~/.sysdoc` (chaves de API/config do motor DVI) tenha permissão de leitura para o UID do container: `chmod o+rx ~/.sysdoc && chmod o+r ~/.sysdoc/config.json` (documentado em `.env.exemplo`).
- Nenhuma outra configuração de serviço externo é necessária — `docker compose up` sem `.env` já sobe com os defaults (`SYSDOC_WEB_ALLOWED_HOSTS=localhost,127.0.0.1`, `SYSDOC_WEB_DEBUG=0`, segredo gerado automaticamente).

## Next Phase Readiness

- A imagem e o compose estão prontos para os planos de UI (07-05 upload, 07-06 progresso, 07-07 resultado/revisão) rodarem dentro do mesmo container sem exigir nenhum ajuste de infraestrutura adicional.
- `manage.py createsuperuser` continua sendo o único passo manual do administrador, exatamente como o `07-CONTEXT.md` (D-07) prevê — não há criação automática de superusuário no entrypoint.
- Nenhum bloqueio para o plano 07-05. A verificação completa de `docker compose up -d` + `curl` + `createsuperuser` num host com rede/porta disponíveis fica registrada como pendência de ambiente, não de código, e pode ser refeita a qualquer momento com os mesmos arquivos entregues aqui.
- Suíte completa: 596 passed, 1 skipped (era 588 passed, 1 skipped; +8 testes novos de `tests/test_web_docker.py`).

---
*Phase: 07-interface-web-para-pregoeiros*
*Completed: 2026-08-27*

## Self-Check: PASSED

Todos os 6 arquivos criados/citados neste SUMMARY foram confirmados em disco e os três hashes de commit (`1bc85ee`, `f0617fe`, `60fc0fd`) foram confirmados em `git log --oneline --all`.
