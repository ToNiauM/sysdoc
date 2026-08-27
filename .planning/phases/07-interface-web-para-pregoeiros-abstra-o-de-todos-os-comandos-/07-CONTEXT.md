# Phase 7: Interface web para pregoeiros - Context

**Gathered:** 2026-08-27
**Status:** Ready for planning
**Source:** Requisitos conversados em sessões anteriores (registrados na memória do projeto) + decisões tomadas na abertura do `/gsd-plan-phase 7`

<domain>
## Phase Boundary

**Esta fase entrega:** uma aplicação web em Django, rodando em Docker, que abstrai o fluxo completo do SysDoc para pregoeiros que **não** conhecem — e não devem precisar conhecer — a CLI, o motor de IA, os checklists, o YAML ou o JSON.

O fluxo visual cobre as quatro etapas do goal do ROADMAP:

1. **Upload** dos documentos do processo (PDF único do processo inteiro, ou peças separadas).
2. **Extração e carregamento** — `sysdoc prepare` + fatiador determinístico de peças, sem o usuário ver cache, manifest ou `contexto_sysdoc.md`.
3. **Análise** — motor `sysdoc-dvi` com progresso em tempo real na tela.
4. **Output** — a análise em HTML e o Despacho de Verificação Inicial em DOCX, para download.

**Fora do escopo desta fase:**
- Reescrever ou duplicar qualquer lógica de `sysdoc.py`, `sysdoc_dvi/` ou `sysdoc_docx/` — a web é camada de abstração, não uma segunda implementação.
- Deploy para VPS/produção real, TLS, domínio, backup. A entrega é a aplicação containerizada rodando localmente via `docker compose up`.
- Multi-tenancy, cobrança, painéis de custo por usuário.
- Substituir a CLI. `sysdoc` e `sysdoc-dvi` continuam funcionando exatamente como hoje, sem a web instalada.
- Templates de TR/ETP (rodada 2 da Phase 6).

### Regra que governa toda a UI

O usuário-alvo é um pregoeiro, não um operador de ferramenta. **Nenhum jargão da máquina aparece na interface:** nada de "LLM", "modelo", "provedor", "prompt", "checklist", "JSON", "YAML", "cache", "token", "grounding", "schema". A tela fala a língua do processo: *processo*, *documentos*, *análise*, *apontamentos*, *despacho*.

</domain>

<decisions>
## Implementation Decisions

### Stack e empacotamento

- **D-01:** **Django** é o framework web. Decisão explícita do usuário em 2026-08-27, que **revoga** a sugestão anterior de FastAPI registrada na memória do projeto. Toda a camada web — rotas, views, templates, ORM, admin, auth — é Django.
- **D-02:** Tudo roda em **Docker**, com `Dockerfile` + `docker-compose.yml` na raiz do repo. Um serviço web. `docker compose up` é o único comando que o administrador precisa dar para subir a aplicação.
- **D-03:** O backend **importa `sysdoc` e `sysdoc_dvi` como biblioteca Python** — nunca via `subprocess` da CLI, nunca reimplementando o pipeline. As funções já existentes são os pontos de entrada: `sysdoc.prepare()`, `sysdoc.create()`, `sysdoc_dvi.pipeline.executar_run()`. Se alguma delas não for chamável como biblioteca (por exemplo porque imprime em stdout, chama `sys.exit`, ou só aceita caminho relativo), **o ajuste correto é tornar a função reutilizável**, não contorná-la com shell.
- **D-04:** A aplicação web é um **pacote Django novo** no repo (ex.: `webapp/` ou `sysdoc_web/`), com suas próprias dependências declaradas em `[project.optional-dependencies]` (extra `web`). A instalação base do SysDoc (`pip install sysdoc`) **não** passa a exigir Django.

### Segurança e credenciais

- **D-05:** **Chaves de API de LLM ficam exclusivamente no servidor** — em `~/.sysdoc/config.json` dentro do container ou em variáveis de ambiente do compose. Nunca são exibidas, nunca trafegam para o navegador, nunca aparecem em página de configuração acessível ao pregoeiro.
- **D-06:** O usuário **não escolhe e não vê** provedor, modelo, alvo econômico/forte, prompt ou custo da análise. Essa configuração é do administrador, feita fora da web (via `sysdoc-dvi config`, que já existe).
- **D-07:** **Autenticação obrigatória** com o `django.contrib.auth` nativo: login exigido em todas as views do fluxo, **sem auto-cadastro** — contas são criadas pelo administrador (`createsuperuser` / Django admin). Motivo: cada análise gasta crédito real de API; uma aplicação aberta é uma torneira de custo. *(Assunção do planejamento — não foi discutida explicitamente com o usuário, mas é o default conservador; se o usuário quiser acesso aberto na rede interna, é uma remoção trivial de decorator.)*
- **D-08:** Upload aceita **apenas** as extensões que o `sysdoc` já extrai (`.pdf`, `.docx`, `.txt`, `.md`), com validação de tipo no servidor e teto de tamanho configurável. O nome do arquivo enviado passa pela sanitização já existente antes de tocar o disco.

### Fluxo do usuário

- **D-09:** A UI tem **quatro telas**, na ordem do fluxo: (1) novo processo + upload, (2) escolha do tipo de verificação — apresentada em português de gente, *"Contratação em geral"* / *"Solução de TIC"*, nunca `geral`/`tic` cru, (3) tela de progresso da análise, (4) resultado com os apontamentos e os downloads.
- **D-10:** **O caminho principal de upload é um PDF único do processo inteiro.** Decisão de produto já tomada (memória `dvi-arquivo-unico`, 2026-08-26) e já viabilizada pelo fatiador determinístico de peças no `prepare` (`detectar_fronteiras_pecas` / `fatiar_texto_por_pecas` em `sysdoc.py`). Upload de peças separadas continua suportado como caminho alternativo, mas não é o que a tela pede primeiro.
- **D-11:** **Revisão humana é passo explícito e bloqueante antes do DOCX.** A análise terminar **não** gera o despacho automaticamente: a tela de resultado mostra os apontamentos e exige uma ação deliberada do pregoeiro — botão *"Revisar e gerar Despacho"* — para chamar `sysdoc create <pasta> dvi`. Isso preserva na web a garantia que a D-03 da Phase 6 estabeleceu na CLI (o despacho é ato de servidor, não saída automática de máquina).
- **D-12:** Os campos institucionais do despacho (unidade, destinatário, signatário, cargo, autoridade) são preenchidos **na tela de revisão**, com formulário, e gravados no bloco `despacho:` do `.sysdoc/config.yaml` do projeto — a mesma fonte que `valores_despacho()` já lê. O pregoeiro nunca edita YAML; o marcador `[PREENCHER: <campo>]` continua sendo o comportamento para campo deixado em branco.
- **D-13:** A tela de resultado oferece **dois downloads**: o HTML da análise (`analise_[modelo]_[data].html`, produzido pelo renderer determinístico existente) e o DOCX do despacho (`xx_nome_dvi_data.docx`). O `dados_consolidados.json` **não** é oferecido ao pregoeiro na UI comum.

### Execução da análise

- **D-14:** **Uma análise por vez.** Fila simples, single-worker, sem Redis, sem Celery, sem broker externo. Decisão do usuário na abertura desta fase — trava o custo de API e mantém o compose com um serviço só. Coerente com o out-of-scope já registrado no `PROJECT.md` ("análise em tempo real com múltiplas LLMs — uma por vez").
- **D-15:** O estado de cada análise é **persistido no banco Django** (SQLite por padrão, num volume), não só em memória: um modelo de job com status, timestamps, projeto associado e progresso. Motivo: se o container reiniciar no meio, a tela precisa poder dizer o que aconteceu em vez de mentir "em andamento" para sempre. Jobs encontrados em execução na subida são marcados como interrompidos.
- **D-16:** **Progresso em tempo real via polling** de um endpoint de status pelo próprio navegador — não WebSocket, não SSE. O pipeline DVI já emite progresso por item (quick task `260826-o2d`); o worker grava esse progresso no job e o endpoint devolve. Polling é o que cabe num `docker compose` de um serviço só, sem ASGI/Channels.
- **D-17:** Falha da análise (chave ausente, provedor fora do ar, PDF ilegível) vira **mensagem em português para o pregoeiro** na tela — "não foi possível concluir a análise", com o caminho de contato/administrador — e o traceback técnico fica no log do servidor. Stack trace nunca chega ao navegador.

### Dados em disco

- **D-18:** Cada processo criado pela web é **uma pasta de projeto SysDoc normal**, no layout que a CLI já usa (`documentos/`, `referencias/`, `output/`, `.sysdoc/`), dentro de um volume Docker. Um projeto criado pela web pode ser aberto pela CLI e vice-versa — não existe formato paralelo.

### Documentação e escopo do produto

- **D-19:** **"Interface GUI" sai do Out of Scope.** `PROJECT.md` (§ Out of Scope: "Interface GUI — CLI only") e `REQUIREMENTS.md` (tabela Out of Scope: "Interface GUI | Agentes não usam GUI") contradizem esta fase e devem ser atualizados como parte dela — a GUI passa a ser requisito ativo, com a ressalva de que a CLI continua sendo o caminho canônico para agentes de IA. Decisão do usuário na abertura desta fase.
- **D-20:** Os requisitos novos desta fase são numerados a partir de **SYSD-19** (SYSD-01 a SYSD-18 já estão tomados). O `REQUIREMENTS.md` está dessincronizado do `ROADMAP.md` — para em SYSD-10, enquanto SYSD-11 a SYSD-18 só existem no roadmap (ver nota de sincronia ao final do `ROADMAP.md`). Sincronizar essa lacuna é oportuno aqui, mas é trabalho de documentação, não deve virar plano próprio às custas da entrega da fase.
- **D-21:** `README.md` e `CHANGELOG.md` registram a web. `AGENTS.md`, `skills/sysdoc/SKILL.md` e os wrappers de skill **não** mudam de contrato — a web não é um caminho para agentes de IA, e o fluxo canônico da skill continua sendo o da CLI.

### Claude's Discretion

- **Nome do pacote Django** (`webapp/`, `sysdoc_web/`, `web/`) e organização em apps — critério do planner, desde que não colida com os módulos existentes (`sysdoc.py`, `sysdoc_dvi/`, `sysdoc_docx/`).
- **Mecanismo concreto do worker single-slot**: thread de background no processo Django, management command dedicado (`manage.py runworker`) rodando como segundo processo no mesmo container, ou equivalente. Requisito é o comportamento (uma por vez, estado no banco, sobrevive a reinício com estado honesto), não a técnica.
- **Camada de interatividade do front**: HTMX, JS mínimo com `fetch`, ou template puro com meta-refresh na tela de progresso. Sem framework SPA — não há justificativa de complexidade aqui.
- **Aparência**: CSS próprio enxuto ou um framework CSS leve. O `templates/analise_template.html` existente é referência de tom visual, mas **não** é para ser importado nem alterado — permanece imutável.
- **Servidor de aplicação** no container (gunicorn, uvicorn+WSGI, `runserver` para uso interno) — critério do planner, com a ressalva de que a decisão precisa ser coerente com D-14 (concorrência de workers do servidor não pode driblar o "uma análise por vez").

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Fluxo operacional canônico (fonte única de verdade)
- `skills/sysdoc/SKILL.md` — o fluxo canônico IA-agnóstico. A web precisa reproduzir a **sequência** que ele define, não inventar uma nova.
- `CLAUDE.md` — regras do projeto: templates imutáveis, `modelo_ia` com slug real, português culto, campo `de` literal, checklist como fonte única.

### CLI que a web vai chamar como biblioteca
- `sysdoc.py` — `prepare()` (linha ~882), `create()` (~1654), `project_paths()` (~290), `init_config()` (~343), `valores_despacho()` (~361), `resolver_tipo_verificacao()` (~383), `render_docx_template()` (~1487). **Ler antes de planejar qualquer chamada** — várias dessas funções retornam `int` de exit code e imprimem em stdout; a web precisa saber o que é reaproveitável e o que precisa de refatoração mínima.
- `sysdoc.detectar_fronteiras_pecas()` / `fatiar_texto_por_pecas()` / `escrever_fatias_virtuais()` (linhas 141–200) — o fatiador determinístico que viabiliza o upload de PDF único (D-10).
- `sysdoc_dvi/pipeline.py` — `executar_run()` (linha 240) é o ponto de entrada da análise. Ler a assinatura e o que ela emite de progresso.
- `sysdoc_dvi/cli.py` — `run()` (linha 132) mostra como o pipeline é orquestrado hoje pela CLI; a web faz o equivalente sem passar pelo argparse.
- `sysdoc_dvi/config.py` — `carregar_config_dvi()`, `chave_do_provedor()`. Define de onde vêm as chaves de API (D-05).
- `sysdoc_dvi/relatorio.py` — `montar_relatorio()` / `renderizar_relatorio()`: o que o motor já sabe reportar sobre uma execução.
- `sysdoc_docx/corpo_dvi.py` — montagem do corpo do despacho, já entregue na Phase 6.

### Contratos de dados
- `templates/schema_sysdoc.json` — contrato do `dados_consolidados.json`. A tela de resultado lê daqui, não de um formato próprio.
- `checklists/dvi.yaml` — fonte canônica dos itens de análise. **Nunca duplicar itens, perguntas ou base legal na web.**
- `normas/vigencia.yaml` — fonte única de vigência normativa.
- `templates/render_analise.py` e `templates/analise_template.html` — **imutáveis**. A web chama o renderer, nunca escreve HTML de análise à mão.

### Estado do projeto e decisões anteriores
- `.planning/STATE.md` — § Recent Decisions concentra as decisões da Phase 6 que a web precisa respeitar (revisão humana, campos institucionais vindos do `config.yaml`, precedência de template por SHA-256).
- `.planning/phases/06-templates-tr-a-partir-dos-modelos-lei-14-133/06-CONTEXT.md` — decisões D-01 a D-14 da Phase 6, em especial a natureza do despacho como documento de correção.
- `.planning/PROJECT.md` e `.planning/REQUIREMENTS.md` — os dois arquivos que a D-19 manda atualizar.

</canonical_refs>

<specifics>
## Specific Ideas

- O comando `docker compose up` sobe a aplicação inteira; nenhum passo manual de migração ou seed deve ficar a cargo do administrador além de criar o primeiro usuário.
- A tela de progresso deve dizer em que etapa está em linguagem de processo — "lendo os documentos", "analisando", "montando o resultado" — não "prepare", "run", "render".
- O `processo-teste/` já existente no disco (49 itens, fora do controle de versão) é o material real disponível para validar o fluxo ponta a ponta.
- A suíte de testes atual está em 561 passed / 1 skipped. Qualquer plano desta fase mantém a suíte verde e adiciona os seus próprios testes.

</specifics>

<deferred>
## Deferred Ideas

- **Deploy real** (VPS, TLS, domínio, backup do volume) — a fase entrega o container funcionando, não a operação em produção.
- **Painel de custo/consumo de API** por usuário ou por análise — o dado existe no relatório do motor, mas expor isso é outra fase.
- **Múltiplas análises simultâneas** com pool configurável — descartado nesta fase por D-14; volta ao debate se o gargalo aparecer no uso real.
- **Auto-cadastro de usuários / SSO institucional** — fora do escopo por D-07.
- **Edição dos apontamentos pela web** antes de gerar o despacho — a revisão desta fase é aprovar e preencher os campos institucionais, não reescrever o parecer.
- **Sincronizar integralmente `REQUIREMENTS.md` com `ROADMAP.md`** (SYSD-11 a SYSD-18) — encostar no que a fase precisa, sem virar projeto de documentação.

</deferred>

---

*Phase: 07-interface-web-para-pregoeiros*
*Context gathered: 2026-08-27 a partir de requisitos conversados + decisões da abertura do plan-phase*
