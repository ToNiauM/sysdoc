---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 07
status: executing
stopped_at: Plano 07-02 concluído (2/8 planos da Phase 7, wave 1/6) — pronto para 07-03
last_updated: "2026-08-27T06:28:42Z"
progress:
  total_phases: 7
  completed_phases: 3
  total_plans: 32
  completed_plans: 25
  percent: 43
---

# STATE — SysDoc

**Project:** SysDoc - Sistema de Análise de Documentação de Licitação
**Current Phase:** 07
**Mode:** standard

## Project Reference

See: .planning/PROJECT.md

**Core value:** CLI offline para análise de documentos de licitação via agentes de IA.

## Progress

| Phase | Status | Plans | Progress |
|-------|--------|-------|----------|
| 1 | complete | 1/1 | 100% |
| 2 | complete | 1/1 | 100% |
| 3 | pending | 0/1 | 0% |
| 4 | pending | 0/1 | 0% |
| 5 | pending | 0/0 | 0% |
| 6 | complete | 7/7 | 100% |
| 7 | in_progress | 2/8 | 25% |

## Recent Changes

- 2026-05-07: Projeto inicializado no GSD.
- 2026-05-07: Codebase mapeado.
- 2026-05-07: Phase 1 concluída — `sysdoc analyze`, `.sysdoc/config.yaml`, AGENTS.md, wrappers Claude Code/OpenCode e testes CLI.
- 2026-05-08: Phase 2 planejada — `02-RESEARCH.md`, `02-PATTERNS.md` e `02-01-PLAN.md`.
- 2026-05-12: Phase 2 concluída — `sysdoc create` gera DOCX determinístico a partir de JSON + templates em `referencias/`, com revisão ETP para `tipo=tr`; 67 testes passando.
- 2026-05-12: Phase adicionada — Templates TR a partir dos 4 modelos Lei 14.133 em `Referencias/`, com placeholders SysDoc anotados.
- 2026-08-26: Merge de branches — "Templates TR (Lei 14.133)" renumerada de Phase 5 para Phase 6; Phase 5 permanece "Motor de análise por checklist" (concluída, release 1.5.0).
- 2026-08-27: Phase 6 planejada (rodada 1: Despacho de Verificação Inicial) — 7 planos em 4 waves, cobrindo SYSD-16/17/18 e D-01 a D-14. Canal raw-XML separado (`render_docx_template(..., raw_xml=)`) adotado em vez de allowlist sobre `values`, eliminando por construção a injeção via chave homônima no `dados_consolidados.json`.
- 2026-08-27: Plano 06-01 concluído — gerador determinístico `templates/build_despacho_templates.py` cria `templates/dvi/despacho_geral.docx` e `templates/dvi/despacho_tic.docx`, moldura fiel a `processo-teste/referencias/dvi.md` com seis estilos nomeados e placeholder raw único `{{corpo_apontamentos_xml}}`; 11 testes novos, suíte completa (480) verde.
- 2026-08-27: Plano 06-02 concluído — `sysdoc_docx/corpo_dvi.py` filtra classificação (D-03), agrupa por peça em ordem canônica (D-05), isola pendências em seção própria ao final (D-04), resolve referência cruzada entre apontamentos equivalentes (D-07) e emite `<w:p>` com estilos nomeados prontos para injeção raw (D-08), sempre com o texto vindo do JSON escapado; 26 testes novos, suíte completa (506) verde.
- 2026-08-27: Plano 06-03 concluído — sigla DVI corrigida de "Documento de Verificação Inicial" para **Despacho de Verificação Inicial** (D-01) em `CLAUDE.md`, `AGENTS.md`, `README.md` (2 ocorrências), `checklists/dvi.yaml`, os três `SKILL.md`, `templates/build_dvi_base.py` (com `templates/dvi_base.docx` regerado) e 2 fixtures de teste; `tests/test_sigla_dvi.py` (4 testes) trava permanentemente a regressão via varredura de `git ls-files`; CHANGELOG registra a correção referenciando a entrada `[1.5.x]` anterior; suíte completa (510) verde.
- 2026-08-27: Plano 06-04 concluído — `render_docx_template(template, output, values, raw_xml=None)` abre canal de XML cru estruturalmente separado de `values` (D-09): `values` é sempre escapado, sem exceção por nome de chave; `RAW_XML_KEYS` permanece como allowlist fechada, mas só é consultada em `_validar_chave_raw`, nunca no corpo da função (travado por teste de introspecção). Campos institucionais do despacho (`vocativo`, `unidade`, `destinatario`, `signatario`, `cargo_signatario`, `autoridade`, `cargo_autoridade`) resolvidos por `valores_despacho()` a partir do novo bloco `despacho:` em `.sysdoc/config.yaml` (semeado por `init_config`), com marcador `[PREENCHER: <campo>]` quando ausente — nunca inventado. 17 testes novos em `tests/test_dvi_render_raw.py` provam a separação de canal isoladamente; suíte completa (532) verde.
- 2026-08-27: Plano 06-05 concluído — `sysdoc create <pasta> dvi` resolve `despacho_geral.docx`/`despacho_tic.docx` pelo `tipo` do `.sysdoc/config.yaml` (D-13), respeitando template customizado do órgão (D-14) via comparação SHA-256 contra as sementes do repo; injeta o corpo real montado por `sysdoc_docx.corpo_dvi` pelo canal `raw_xml`, nunca em `values`; `seed_dvi_template`/`init_command` semeiam a variante correspondente ao `tipo`. 22 testes novos em `tests/test_dvi_create_variante.py` provam precedência, variante, conteúdo filtrado e não-injeção ponta a ponta via `create()`; suíte completa (554) verde.
- 2026-08-27: Plano 06-06 concluído (Rodada 1 fechada) — `tests/test_dvi_despacho_e2e.py` (13 testes) prova sobre o processo real de 49 itens (`processo-teste/`) que `sysdoc create <pasta> dvi` produz o despacho nas duas variantes, com override de template do projeto e sem nenhum `{{` remanescente, isolado por `shutil.copytree` em `tmp_path`. Bug real encontrado e corrigido no caminho: a seção de pendências não era numerada no XML renderizado (`sysdoc_docx/corpo_dvi.py`, nova `_titulo_numerado`). `processo-teste/.sysdoc/config.yaml` recebeu `tipo: geral` e o bloco `despacho:` (só `unidade`/`destinatario` preenchidos) diretamente em disco, sem ser versionado. CHANGELOG, README, `skills/sysdoc/SKILL.md` e `AGENTS.md` documentam a Rodada 1 como entregue; suíte completa (567) verde.
- 2026-08-27: Plano 06-07 concluído (Phase 6 fechada — Rodada 1, 7/7 planos) — checkpoint bloqueante da Task 1 apresentou ao usuário as três opções para o destino de `templates/dvi_base.docx` (formato relatório) com o conjunto real de placeholders inspecionado; **decisão do usuário: `aposentar`**. Task 2 removeu `templates/dvi_base.docx` e `templates/build_dvi_base.py`, trimou `tests/test_dvi_template_base.py` (removidas `TestTemplateBaseValido`/`TestCreateAposInit`, preservada `TestSeedDviTemplate`), confirmou que `tests/test_sigla_dvi.py::test_docx_base_usa_a_expansao_correta` passa a `skipped` pelo `skipif` já existente, e registrou a decisão em `CHANGELOG.md` (recuperável via `git show d180b24^:templates/dvi_base.docx`). Suíte completa: 561 passed, 1 skipped (era 567; -5 testes do arquivo removido, +1 skip esperado). SYSD-18 completo.

- 2026-08-27: Phase 7 planejada — 8 planos em 6 waves, requisitos SYSD-19 a SYSD-29, cobrindo D-01 a D-21 do `07-CONTEXT.md`. Interface web em **Django** (não FastAPI — correção explícita do usuário), rodando em Docker de um serviço, importando `sysdoc`/`sysdoc_dvi` como biblioteca. Plan-checker aprovou na iteração 2; o blocker da iteração 1 era um `ValueError` em import time (`ClearableFileInput(attrs={"multiple": True})` deixou de ser aceito no Django 5.0), reproduzido contra instalação real e corrigido para o par `MultipleFileInput`/`MultipleFileField`.
- 2026-08-27: Plano 07-01 concluído (wave 1/6) — `sysdoc.criar_documento()` (dataclass `ResultadoCreate`) e `sysdoc.localizar_html_analise()`/`localizar_docx_despacho()` tornam `create()`/`deploy()` chamáveis como biblioteca sem imprimir nem `subprocess`; `sysdoc_dvi/progresso.py` (`EventoProgresso`/`ETAPAS`/`SinkProgresso`, sem dependência de Django) e `_emitir()` em `pipeline.py` dão a `executar_run(..., progresso=callback)` um canal de eventos por etapa, blindado contra callback que lança exceção (RF9). Nenhuma string impressa pela CLI mudou; 11 testes novos em `tests/test_biblioteca_chamavel.py`; suíte completa (568 passed, 1 skipped) verde. SYSD-19 completo.
- 2026-08-27: Plano 07-02 concluído (wave 1/6) — pacote Django `sysdoc_web` criado como extra opcional (`pip install -e ".[web]"`, `django>=5.0,<6.0`/`gunicorn>=22.0`), sem tocar em `dependencies` base; `sysdoc_web/settings.py` endurecido (`SECRET_KEY` obrigatória fora de `DEBUG`, `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` por env, cookies `HttpOnly`/`SameSite`, `SECURE_CONTENT_TYPE_NOSNIFF`/`X_FRAME_OPTIONS=DENY`, limites de upload já parametrizados, SQLite com `timeout=20` — primeira metade da defesa de D-14 — e nenhuma menção a chave de LLM). Login obrigatório em `/entrar/`, `/sair/` só por POST, sem nenhuma rota de auto-cadastro (`django.contrib.auth.urls` deliberadamente fora). `tests/conftest.py` traz o fixture `django_web` (bootstrap condicional via `DiscoverRunner`, Django só importado dentro do fixture); suíte completa: 574 passed/1 skipped com Django, 570 passed/2 skipped sem Django (nunca erro). SYSD-20/SYSD-21 completos.

## Recent Decisions

- `ResultadoCreate` (dataclass congelada com 4 campos) fica em `sysdoc.py`, perto de `create`/`criar_documento`, em vez de um módulo próprio — evita um arquivo novo para uma estrutura de dados usada só ali.
- `localizar_docx_despacho()` busca só em `paths.root` (sem `rglob`) e usa nome ancorado por regex (`^\d{2}_.*_dvi_\d{4}-\d{2}-\d{2}\.docx$`) — um `.docx` de `referencias/` nunca pode ser confundido com um despacho já gerado.
- `sysdoc_dvi.cli.run()` não recebe o parâmetro `progresso` — só chamadores de biblioteca (a view Django que os planos seguintes vão escrever) o usam; a CLI continua sem esse parâmetro no dispatch do argparse.
- Interface web da Phase 7 é **Django**, decisão explícita do usuário em 2026-08-27 que revoga a sugestão anterior de FastAPI registrada na conversa de requisitos. Não reabrir.
- Concorrência da web: **uma análise por vez**, com `UniqueConstraint` condicional no banco (não um `if` na view, que uma segunda thread do gunicorn driblaria) mais worker single-slot em processo separado. Sem Redis, sem Celery — trava o custo de API e mantém o compose com um serviço só.
- A web **importa** `sysdoc`/`sysdoc_dvi` como biblioteca, nunca via `subprocess` da CLI; onde uma função não for reutilizável, a correção é torná-la chamável preservando o comportamento da CLI.
- Revisão humana bloqueante antes do DOCX também na web (D-11 da Phase 7, preserva a D-03 da Phase 6): o fim da análise não gera o despacho — só `views.gerar_despacho` chama `create`, nunca o worker.
- Django entra como extra opcional (`[project.optional-dependencies]`); `pip install sysdoc` não passa a exigir Django e a CLI continua funcionando sem a web instalada.
- "Interface GUI" sai do Out of Scope de `PROJECT.md` e `REQUIREMENTS.md` como parte da própria Phase 7 — a CLI permanece o caminho canônico para agentes de IA.
- Templates de geração DOCX ficam em `referencias/`, não em um template fixo do repositório.
- `sysdoc create` permanece offline e determinístico, usando substituição ZIP/XML de placeholders em DOCX.
- `tipo=tr` é o padrão quando omitido; `--tipo` existe para scripts.
- Para TR, o ETP preparado é lido de `.sysdoc/cache/textos/documentos/ETP.txt`, com fallback legado para `.sysdoc/cache/textos/ETP.txt`.
- `templates/dvi/` é a pasta própria para templates institucionais do despacho, um DOCX por variante de verificação (`despacho_geral.docx`, `despacho_tic.docx`), no molde do gerador determinístico já usado por `templates/build_dvi_base.py`.
- Chave de equivalência de D-07 (referência cruzada) usa apenas `parecer` normalizado, não `parecer+fundamento` — medição contra `processo-teste/dados_consolidados.json` mostrou que o par `ETP-016`/`TR-002` tem `fundamento` que varia pelo nome da peça, mesmo apontando o mesmo achado.
- DVI = Despacho de Verificação Inicial (D-01), confirmado por `processo-teste/referencias/dvi.md` linha 1 e pelo dono do produto; `tests/test_sigla_dvi.py` trava permanentemente contra as duas expansões erradas já vistas no repositório.
- Canal de XML cru é um parâmetro dedicado (`raw_xml`), não uma allowlist sobre nome de chave em `values` — fecha por construção o vetor de chave homônima vinda de `dados_consolidados.json` (revisão do checker sobre D-09).
- Campos institucionais do despacho (vocativo, unidade, destinatário, signatário, autoridade) vêm de `.sysdoc/config.yaml` bloco `despacho:`, nunca do JSON da análise nem inferidos — campo ausente vira `[PREENCHER: <campo>]` visível no Word.
- Precedência de template DVI resolvida por SHA-256 contra as sementes do repo: um `.docx` em `referencias/` byte-idêntico a `templates/dvi/despacho_*.docx` conta como "semente intocada" e cede lugar à variante do `tipo`; só um `.docx` realmente diferente (customizado pelo órgão) vence sem precisar de `tipo`.
- Numeração de seção (`"N) "`) só é aplicada no ponto de renderização do XML (`_titulo_numerado`), não no campo `titulo` devolvido por `montar_apontamentos()` — mantém os testes unitários que comparam esse campo sem número intactos, corrigindo só o defeito visível no DOCX final.
- `processo-teste/` permanece intencionalmente fora do controle de versão; a suíte E2E que roda sobre ele (`tests/test_dvi_despacho_e2e.py`) sempre copia para `tmp_path` antes de qualquer escrita e nunca é responsável por versionar nada desse projeto.
- `templates/dvi_base.docx` e `templates/build_dvi_base.py` (formato relatório do DVI) aposentados por decisão explícita do usuário no checkpoint bloqueante do Plano 06-07 — recuperáveis via git history (`git show d180b24^:<caminho>`); o conteúdo que expunham continua disponível via `templates/render_analise.py`/HTML e `dados_consolidados.json`.
- `sysdoc_web/urls.py` não inclui `django.contrib.auth.urls` (evitaria rotas de reset de senha por e-mail que não há como servir); só `LoginView`/`LogoutView` explícitos e nenhuma rota de cadastro — confirmado por teste (`test_nao_existe_rota_de_cadastro`).
- `pytest.importorskip("django")` no nível de módulo aborta a coleta inteira do arquivo (confirmado experimentalmente), inclusive testes definidos antes da linha — por isso os dois testes de leitura de arquivo que precisam rodar sem Django (`tests/test_web_settings_sem_django.py`) foram para um módulo próprio, sem esse guard, em vez de ficarem acima do `importorskip` em `tests/test_web_base.py`.

## Accumulated Context

### Roadmap Evolution

- Phase 5 added: Motor de análise por checklist com agentes plugáveis (PRD completo em `.planning/phases/05-motor-analise-checklist/PRD.md`)
- Phase 7 added (2026-08-26): Interface web para pregoeiros — fluxo visual de upload → extração → análise → output HTML/DOCX, abstraindo a CLI e o motor DVI

## Pending Todos

- Revisar a pasta não rastreada `Referencias/` antes de qualquer publicação ampla; ela parece conter modelos reais do usuário.

## Blockers/Concerns

- Nenhum bloqueio ativo para continuar o roadmap.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260826-o2d | Melhorias DX motor DVI: autocorreção de acentuação pós-validação (P2), progresso por item no run (P4), template DVI base semeado pelo init (P6) | 2026-08-26 | b376b5f | [260826-o2d-melhorias-dx-motor-dvi-autocorre-o-p-s-v](./quick/260826-o2d-melhorias-dx-motor-dvi-autocorre-o-p-s-v/) |
| 260826-p65 | Motor DVI: fatiador determinístico de peças no prepare (P1), re-ancoragem determinística do campo `de` antes de degradar (P3), preços de modelos configuráveis por alvo (P5) | 2026-08-26 | 8af987b | [260826-p65-motor-dvi-fatiador-deterministico-de-pec](./quick/260826-p65-motor-dvi-fatiador-deterministico-de-pec/) |

## Session Continuity

Last session: 2026-08-27T06:28:42Z
Stopped at: Plano 07-02 concluído (2/8 planos da Phase 7, wave 1/6) — pronto para 07-03
Resume file: None

## Current Focus

Phase 7: Interface web para pregoeiros — em execução (2/8 planos). Próximo passo recomendado: executar `07-03-PLAN.md` (modelos Processo/AnaliseJob, fila single-slot e worker do pipeline DVI).

Phases 3 e 4 seguem pendentes e não bloqueiam a 7.

---

*Last updated: 2026-08-27 — Completed 07-02-PLAN.md: esqueleto Django `sysdoc_web` como extra opcional, settings endurecidas, autenticação obrigatória sem auto-cadastro e bootstrap condicional do Django na suíte pytest; Phase 7 wave 1 fechada (07-01 + 07-02)*
