# SysDoc

Ferramenta IA-agnóstica para preparar, analisar e gerar saídas determinísticas a partir de documentos. O caso comum continua sendo TR e ETP em contratações públicas, mas a estrutura agora aceita qualquer conjunto de documentos suportados.

A análise é executada em duas camadas complementares:

1. **CLI determinística** (`sysdoc`) — extrai PDFs e DOCX, prepara um contexto canônico, valida o JSON consolidado contra schema, versiona o JSON por modelo de IA + data, renderiza HTML imutável e faz o deploy via SSH. Não realiza chamadas a modelos de linguagem.
2. **Agente de IA** (Claude Code, OpenCode, Codex, Antigravity, Cline, Gemini CLI, Cursor, ou qualquer outro harness) — lê os artefatos da CLI, aplica as lentes de análise definidas em `skills/sysdoc/SKILL.md` e produz `dados_consolidados.json`.

A separação garante reprodutibilidade: o mesmo JSON, validado pelo mesmo validador, gera sempre o mesmo HTML. A análise pode ser repetida com modelos distintos sem retrabalho de extração ou renderização.

---

## Sumário

1. [Requisitos](#requisitos)
2. [Instalação](#instalação)
3. [Arquitetura e pipeline](#arquitetura-e-pipeline)
4. [Fluxo padrão rápido](#fluxo-padrão-rápido)
5. [Comandos da CLI](#comandos-da-cli)
6. [Configuração por projeto (`.sysdoc/config.yaml`)](#configuração-por-projeto-sysdocconfigyaml)
7. [Suporte multi-harness](#suporte-multi-harness)
8. [Estrutura de um projeto](#estrutura-de-um-projeto)
9. [Schema canônico e regras de validação](#schema-canônico-e-regras-de-validação)
10. [Restrições do projeto](#restrições-do-projeto)
11. [Motor de análise DVI (`sysdoc-dvi`)](#motor-de-análise-dvi-sysdoc-dvi)
12. [Documentação adicional](#documentação-adicional)
13. [Exemplo didático: do zero ao deploy nos dois fluxos](#exemplo-didático-do-zero-ao-deploy-nos-dois-fluxos)

---

## Requisitos

- Python 3.10 ou superior
- `pip` para instalação local
- `ssh` e `scp` no PATH para o deploy (opcional, somente se for usar `sysdoc deploy`)
- Acesso SSH a um servidor com diretório de publicação (opcional, somente para deploy)

Dependências de runtime: `pypdf>=4.0.0`, `pyyaml>=6.0`. Instaladas automaticamente pelo `pip install -e .`.

---

## Instalação

```bash
git clone <url-do-repo> sysdoc
cd sysdoc
pip install -e .
```

Após a instalação o entry point `sysdoc` fica disponível em qualquer diretório. Para validar:

```bash
sysdoc --version
sysdoc --help
```

---

## Arquitetura e pipeline

O fluxo padrão de uma análise tem cinco estágios. Cada estágio produz artefatos consumidos pelo seguinte; a CLI nunca consulta um modelo de linguagem.

```
                    [1] sysdoc init
                            |
                            v
                    +-----------------------+
                    | MeuProjeto/           |  <-- usuario copia documentos
                    | +-- documentos/       |      e referencias
                    | +-- referencias/      |
                    | +-- output/           |
                    | +-- .sysdoc/          |
                    |     +-- config.yaml   |
                    +-----------+-----------+
                                |
                    [2] sysdoc analyze (ou prepare)
                                |
                                v
                    +-----------------------+
                    | .sysdoc/cache/        |  <-- extracao deterministica
                    | +-- textos/documentos/|      (pypdf + ElementTree)
                    | +-- textos/referencias|
                    | +-- contexto_sysdoc.md|
                    | +-- manifest.json     |
                    +-----------+-----------+
                                |
                    [3] Agente de IA
                                |       le contexto + textos extraidos
                                |       aplica lentes (tecnica, juridica,
                                |       Delic, consistencia ETP x TR)
                                v
                    +-----------------------+
                    |dados_consolidados.json|  <-- produzido pela IA conforme
                    +-----------+-----------+      templates/schema_sysdoc.json
                                |
                    [4] sysdoc publish
                                |       valida + versiona JSON +
                                |       renderiza HTML imutavel
                                v
                    +-----------------------+
                    | output/dados_...json  |
                    | output/analise_...html|
                    | output/*.docx         |
                    +-----------+-----------+
                                |
                    [5] sysdoc deploy
                                |       le vps_host/vps_path do
                                |       config.yaml, descobre proximo
                                v       index{N}.html livre via SSH
                    +-----------------------+
                    | VPS: index{N}.html    |
                    +-----------------------+
```

### Responsabilidades

| Estágio | Responsável | Entradas | Saídas |
|---------|-------------|----------|--------|
| 1. Init | CLI | nome do projeto | estrutura de pastas, `config.yaml` |
| 2. Prepare/Analyze | CLI | `documentos/*`, `referencias/*` | textos extraídos, `contexto_sysdoc.md`, `manifest.json` |
| 3. Análise | Agente de IA | `contexto_sysdoc.md`, textos extraídos, `SKILL.md`, `schema_sysdoc.json` | `dados_consolidados.json` |
| 4. Publish | CLI | `dados_consolidados.json` | JSON versionado + HTML versionado |
| 5. Deploy | CLI | HTML mais recente, `config.yaml` | `index{N}.html` na VPS |

---

## Fluxo padrão rápido

Use `.` quando já estiver dentro da pasta do projeto; use `[pasta]` quando estiver na raiz do SysDoc.

### Passo 1 — Inicializar

```bash
sysdoc init .
```

Cria `documentos/`, `referencias/`, `output/`, `.sysdoc/config.yaml` e arquivos mínimos sem sobrescrever o que já existir.

### Passo 2 — Adicionar documentos

Coloque os documentos a analisar em `documentos/`. Use `referencias/` para normas, modelos institucionais, exemplos aprovados, pareceres ou materiais de apoio.

```bash
sysdoc status
```

Confirma quantos documentos, referências, JSONs, HTMLs e caches foram encontrados.

### Passo 3 — Configurar deploy

```bash
sysdoc config --vps usuario@servidor --path /caminho/publico/html .
```

Grava a VPS e a pasta remota em `.sysdoc/config.yaml`.

### Passo 4 — Preparar para IA

```bash
sysdoc all .
```

Inicializa se faltar algo, extrai os textos e gera `.sysdoc/cache/contexto_sysdoc.md` para o agente de IA.

Alternativa direta, quando a estrutura já existe:

```bash
sysdoc prepare .
```

### Passo 5 — Gerar o JSON com o agente de IA

```
/sysdoc analyze . foco em garantia contratual e sanções administrativas
```

O agente lê o cache, segue `skills/sysdoc/SKILL.md` e entrega `dados_consolidados.json`.

### Passo 6 — Validar e renderizar

```bash
sysdoc render .
```

Renderiza o HTML em `output/` usando `dados_consolidados.json` ou o JSON mais recente.

Para validar, versionar JSON e renderizar em uma única etapa:

```bash
sysdoc publish .
```

Para gerar um `.docx` a partir de um template Word em `referencias/`:

```bash
sysdoc create tr
```

Quando `tipo` for omitido, `create` assume `tr`. A flag `--tipo` também pode ser usada para scripts.

### Passo 7 — Enviar para produção

```bash
sysdoc deploy .
```

Envia o HTML mais recente para a VPS configurada.

### Com pasta explícita

```bash
sysdoc init Aquisicao-Combustivel-2026
sysdoc config --vps usuario@servidor --path /caminho/publico/html Aquisicao-Combustivel-2026
sysdoc all Aquisicao-Combustivel-2026
sysdoc publish Aquisicao-Combustivel-2026
sysdoc deploy Aquisicao-Combustivel-2026
```

Para comparar análises feitas por modelos diferentes:

```bash
sysdoc compare Aquisicao-Combustivel-2026
```

---

## Comandos da CLI

| Comando | O que faz |
|---------|-----------|
| `sysdoc status` | Lista projetos no diretório atual e exibe contagens de documentos, referências, JSON, HTML e cache preparado. |
| `sysdoc init [pasta]` | Cria estrutura base (`documentos/`, `referencias/`, `output/`, `.sysdoc/config.yaml`). Não sobrescreve `config.yaml` se já existir. |
| `sysdoc config --vps <usuario@host> --path <caminho> [pasta]` | Atualiza a VPS e a pasta remota em `.sysdoc/config.yaml`. Sem flags, mostra a configuração atual. |
| `sysdoc prepare [pasta]` | Extrai texto de todos os arquivos suportados em `documentos/` e `referencias/` para `.sysdoc/cache/textos/`. Gera `contexto_sysdoc.md` e `manifest.json`. |
| `sysdoc all [pasta]` | Inicializa a estrutura e prepara o cache para o agente de IA. |
| `sysdoc analyze [pasta] [-i "instrução"] [--dry-run]` | Prepara o cache (se ausente) e exibe um handoff visual com o slash command exato (`/sysdoc analyze <pasta>`) para colar no harness de IA. Aceita `--instruction`/`-i` para foco temático e `--dry-run` para reimprimir o handoff sem reextrair PDFs. |
| `sysdoc guia [pasta]` | Wizard interativo de onboarding: verifica entradas obrigatórias, oferece configurar a VPS, pergunta qual harness será usado e gera `.sysdoc/cache/roteiro.txt` com os comandos exatos para o projeto. Requer terminal interativo. |
| `sysdoc validate [pasta]` | Valida `dados_consolidados.json` contra o schema, regras de coerência, acentuação PT-BR e rastreabilidade do campo `de`. |
| `sysdoc render [pasta] [--json arquivo]` | Renderiza HTML em `output/` a partir de `dados_consolidados.json`, do JSON mais recente ou de um JSON explícito. |
| `sysdoc publish [pasta] [--json arquivo]` | Executa `validate` + versionamento de JSON por modelo+data em `output/` + `render`. |
| `sysdoc create [pasta] [tipo] [--template arquivo.docx] [--json arquivo]` | Gera DOCX a partir de um template Word e dados do JSON. Para `tipo=tr`: aplica revisão ETP (substituição `de`→`para`), seleciona template por categoria de contratação em `referencias/` e grava na raiz como `tr_[modelo]_[data].docx`. |
| `sysdoc deploy [pasta]` | Envia o HTML mais recente para a VPS via SSH/SCP, descobrindo o próximo `index{N}.html` livre. Lê `vps_host`/`vps_path` de `.sysdoc/config.yaml`. |
| `sysdoc compare [pasta]` | Lista todos os JSONs versionados do projeto com modelo, data, contagem de itens, bloqueantes e relevantes. |
| `sysdoc --version` | Exibe a versão instalada (1.4.0). |

Todos os comandos retornam código de saída convencional: 0 para sucesso, não-zero para falha. Nenhum comando faz chamadas a modelos de linguagem.

---

## Configuração por projeto (`.sysdoc/config.yaml`)

Criado automaticamente por `sysdoc init`. Configure deploy com:

```bash
sysdoc config --vps usuario@servidor --path /caminho/publico/html .
```

O arquivo fica assim:

```yaml
projeto: <nome-da-pasta>
vps_host: "<usuario>@<host>"      # ex.: "usuario@servidor"
vps_path: "<caminho-absoluto>"    # ex.: "/caminho/publico/html"
modelo_ia_padrao: "<slug>"        # ex.: "claude-sonnet-4-6"
```

Comportamento:

- `vps_host` e `vps_path` em branco ⇒ `sysdoc deploy` usa o fallback hardcoded.
- `sysdoc config [pasta]` sem `--vps`/`--path` mostra os valores atuais.
- `modelo_ia_padrao` é metadado informativo; o JSON final ainda deve trazer o slug real do modelo que fez a análise.

---

## Suporte multi-harness

| Harness | Wrapper | Como acionar |
|---------|---------|--------------|
| Claude Code | `.claude/skills/sysdoc-analise/SKILL.md` | `/sysdoc`, `sysdoc analyze`, ou frase contendo "análise de licitação" |
| OpenCode | `.opencode/skills/sysdoc-analise/SKILL.md` | `/sysdoc`, `sysdoc analyze`, ou frase contendo "análise de licitação" |
| Codex, Antigravity, Cline, Gemini CLI, Cursor | `AGENTS.md` na raiz | Ler `AGENTS.md` e `skills/sysdoc/SKILL.md`, depois invocar `sysdoc analyze` no shell |

A fonte única de verdade operacional é `skills/sysdoc/SKILL.md`. Os wrappers só adicionam ajustes específicos do harness, como o uso do MCP `PDF_Tools` no Claude Code ou a preferência por Bash no OpenCode. Em caso de divergência entre wrapper e canônico, prevalece o canônico.

---

## Estrutura de um projeto

```
MeuProjeto/
├── documentos/                               # documentos a analisar
│   └── ...                                   # PDF, DOCX, TXT ou MD
├── referencias/                              # normas, modelos, exemplos e templates
│   └── ...                                   # PDF, DOCX, TXT ou MD
├── output/                                   # HTML, JSON versionado e DOCX gerados
├── .sysdoc/
│   ├── config.yaml                           # projeto, vps_host, vps_path, modelo_ia_padrao
│   └── cache/
│       ├── manifest.json                     # SHA256, contagens e mapeamentos por arquivo
│       ├── contexto_sysdoc.md                # mapa determinístico para a IA
│       └── textos/
│           ├── documentos/
│           └── referencias/
└── dados_consolidados.json                   # produzido pela IA, base para render/publish/create
```

Diretórios reservados, nunca tratados como projeto pelo `sysdoc status`: `.git`, `.claude`, `.opencode`, `backup`, `skills`, `templates`.

---

## Schema canônico e regras de validação

`dados_consolidados.json` deve respeitar `templates/schema_sysdoc.json`. Campos de topo obrigatórios:

`titulo`, `subtitulo`, `modelo_ia`, `data_análise`, `projeto`, `metadados`, `documentos_analisados`, `parecer_executivo`, `secao_etp`, `secao_tr`, `itens`, `nota_integridade`.

Cada item de `itens[]` exige: `id`, `número`, `item`, `documento`, `seção`, `de`, `para`, `parecer`, `fundamento`, `classificação`, `severidade`, `risco_jurídico`, `status_delic`, `alterado_pelo_jurídico`.

### Enums

- `documento`: `ETP` ou `TR`
- `classificação`: `conforme`, `ajuste_necessário`, `risco`, `pendente`
- `severidade`: `crítica`, `alta`, `média`, `baixa`, `informativa`
- `risco_jurídico`: `bloqueante`, `relevante`, `menor`, `informativo`
- `status_delic`: `confirmado`, `novo`, `divergente`, `null`
- `classificação_documento`: `aprovado`, `aprovado_com_ressalvas`, `reprovado`, `pendente_de_complementação`

### Regras de coerência (o validador rejeita se violar)

- `classificação=risco` exige `risco_jurídico ∈ {relevante, bloqueante}`
- `classificação=conforme` exige `risco_jurídico=informativo`
- `risco_jurídico=bloqueante` exige `severidade ∈ {crítica, alta}`
- `alterado_pelo_jurídico=true` exige `de ≠ para`
- `modelo_ia` deve ser slug real (`claude-sonnet-4-6`, `gpt-5`, etc.) — valores genéricos como `ia`, `modelo` ou `default` reprovam
- `parecer_executivo` exige no mínimo 450 palavras
- `parecer_documento` (em `secao_etp` e `secao_tr`) exige no mínimo 120 palavras
- Quando o cache estiver presente, o campo `de` de cada item deve ser rastreável no texto extraído do documento indicado

### Rastreabilidade e campo `de`

O campo `de` deve preservar literalmente o trecho do documento original — inclusive erros de digitação, falta de acento ou quebras estranhas de extração. É o único campo isento da norma culta.

Para documentar a ausência de uma cláusula esperada, use o marcador `[OMISSÃO] seção onde deveria constar`.

---

## Restrições do projeto

- `templates/analise_template.html`, `templates/render_analise.py` e `templates/validate_sysdoc.py` são imutáveis durante uma análise. Qualquer modificação compromete a reprodutibilidade.
- HTML nunca é escrito manualmente. Apenas o renderizador determinístico produz arquivos `analise_*.html`.
- Todo campo gerado pela IA usa norma culta do português brasileiro com acentuação correta. Exceção exclusiva: o campo `de`.
- Não invente artigos de lei, números de acórdão, números SEI, valores monetários, datas ou cláusulas. Quando a base for insuficiente, classifique o item como `pendente`.
- Hierarquia normativa para fundamentação: lei ou norma aplicável > regulamento vinculante > modelo oficial > referência técnica confiável > texto atual do documento.

---

## Motor de análise DVI (`sysdoc-dvi`)

O motor de análise DVI (Despacho de Verificação Inicial) é um **binário separado**, `sysdoc-dvi`, distinto da CLI `sysdoc` — ele é o único componente do projeto que chama modelo de linguagem. A CLI `sysdoc` continua 100% determinística.

### Pré-requisito: configurar os modelos

Antes do primeiro `sysdoc-dvi run`, configure o par de modelos econômico/forte:

```bash
sysdoc-dvi config --economico openrouter/deepseek-chat --forte anthropic/claude-opus-5
sysdoc-dvi config --listar
```

O mapeamento fica em `~/.sysdoc/config.json` (nunca versionado). Alternativa: editar o arquivo à mão, ou usar as variáveis de ambiente `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`.

Opcionalmente, registre o preço de cada alvo (USD por 1 milhão de tokens de entrada/saída) para que o relatório de execução calcule o custo real em vez de custo zero:

```bash
sysdoc-dvi config --preco openrouter/deepseek-chat 0.28 0.42
sysdoc-dvi config --preco anthropic/claude-opus-5 15 75
sysdoc-dvi config --listar
```

O preço configurado tem precedência sobre a tabela embutida (vazia por padrão — nenhum preço é assumido) e pode ser repetido para registrar vários alvos numa só chamada de `config`. Alvo sem preço registrado mantém custo zerado no relatório, com um aviso que já traz o comando `sysdoc-dvi config --preco <alvo> <entrada> <saida>` pronto para copiar.

### Rodando a análise

```bash
sysdoc-dvi run [pasta] --tipo geral|tic
```

`--tipo geral` roda a aplicabilidade padrão de qualquer contratação; `--tipo tic` inclui também os itens específicos de contratação de TIC. O pipeline: lê o mapeamento de modelos → filtra `checklists/dvi.yaml` por `aplicabilidade`/`ativo` → roda `sysdoc prepare` se o cache não existir → mapeia as peças do projeto (ETP, TR, MCP, Mapa de Riscos) → executa cada item do checklist com retomada por checkpoint → roda a síntese final (`parecer_executivo`, `parecer_documento`) no modelo forte → grava `dados_consolidados.json` → `sysdoc validate` → `sysdoc render` → grava um relatório de execução em `output/`. `sysdoc-dvi relatorio [pasta]` reimprime o último relatório sem reexecutar.

### Mapeamento de peças (ETP, TR, MCP, Mapa de Riscos)

O caminho canônico é um **único PDF do processo inteiro** em `documentos/`. Nesse caso, `sysdoc prepare` tenta fatiar deterministicamente as peças por cabeçalho em linha própria (ex.: "ESTUDO TÉCNICO PRELIMINAR", "TERMO DE REFERÊNCIA", "MAPA DE RISCOS"), gravando cada fatia em `.sysdoc/cache/textos/documentos/{PECA}.txt`. Peça sem cabeçalho inequívoco (ambíguo ou ausente) usa o arquivo inteiro do processo em vez de abortar. O bloco `pecas:` de `.sysdoc/config.yaml` deixou de ser obrigatório nesse fluxo; continua disponível como override manual de precedência absoluta (sempre sobre o arquivo inteiro, nunca sobre uma fatia). `sysdoc-dvi run` imprime a origem de cada peça mapeada (`fatiamento`, `arquivo-inteiro`, `override`, `ancora` ou `nome`) no passo 4 e no relatório de execução.

### O que cada tipo de verificação faz

| Tipo | O que faz |
|------|-----------|
| `presenca` | Chamada a LLM (contexto restrito à peça, temperatura 0) verificando se um elemento obrigatório está presente no documento. |
| `julgamento` | Chamada a LLM fundamentada exclusivamente em `base_legal_texto` do item — citar norma fora dessa base reclassifica o item como `pendente`. |
| `calculo` | LLM extrai a tabela de dados (valores, quantidades) em schema fechado; funções Python puras recalculam média, mediana e unitário × quantidade e comparam com o valor declarado, com tolerância configurável. |
| `vigencia` | Lookup determinístico em `normas/vigencia.yaml` — o modelo nunca responde sobre vigência de memória. Norma ausente da tabela vira item `pendente`. |
| `mecanica` | Funções Python puras sobre o texto extraído (numeração sequencial, presença de CATMAT/CATSER, menção × presença de cronograma físico-financeiro). |

### Onde ficam checklist e tabela de vigência

- `checklists/dvi.yaml` — itens de análise DVI, fonte canônica (ver `skills/sysdoc/SKILL.md`).
- `normas/vigencia.yaml` — tabela de vigência de normativos, com override por projeto em `referencias/`.

### Editar ou desativar um item sem tocar em código

Cada item do checklist é uma entrada YAML com `id`, `aplicabilidade`, `peca`, `tipo`, `pergunta`, `base_legal_texto`, `referencia`, `severidade_default`, `modelo_alvo` e `ativo`. Para desativar um item, defina `ativo: false` — nenhuma alteração de código é necessária. Editar pergunta, base legal ou severidade também é só editar o YAML.

### Passo manual seguinte

Depois de revisar o JSON/HTML gerado:

```bash
sysdoc create dvi [pasta]
sysdoc deploy [pasta]
```

`sysdoc create dvi` gera o DVI em DOCX (minuta para assinatura, nunca documento final automático). Os artefatos gerados a partir da 1.5.0 seguem o padrão de nomes `xx_nome_tipo_data.extensao`, onde `xx` é o contador de produção daquele tipo de artefato no projeto (nunca reutilizado) — exemplo canônico: `01_processo-042_dvi_2026-08-26.docx`.

### Template do despacho e configuração institucional

`sysdoc create <pasta> dvi` produz o **Despacho de Verificação Inicial** propriamente dito: um documento que aponta, para a Unidade Demandante, apenas o que precisa de ajuste — itens `conforme` nunca aparecem, itens `pendente` (documento ausente/ilegível) viram uma seção própria ao final, e apontamentos equivalentes entre ETP e TR são resolvidos automaticamente como referência cruzada.

Duas chaves novas em `.sysdoc/config.yaml` (semeadas vazias por `sysdoc init`) controlam a geração:

- **`tipo: geral|tic`** — mesma aplicabilidade usada por `sysdoc-dvi run --tipo`. Sem template customizado do órgão em `referencias/`, `create` usa essa chave para escolher entre `templates/dvi/despacho_geral.docx` e `templates/dvi/despacho_tic.docx`.
- **`despacho:`** — bloco com os sete campos institucionais que não existem no `dados_consolidados.json` (são dado de órgão, não de análise): `vocativo`, `unidade`, `destinatario`, `signatario`, `cargo_signatario`, `autoridade`, `cargo_autoridade`. Campo vazio vira o marcador `[PREENCHER: <campo>]` visível no Word — nunca é inventado.

Um `referencias/dvi.docx` (ou `modelo_dvi.docx`/`template_dvi.docx`) próprio do projeto sempre tem precedência sobre a variante do repositório, preservando a customização por órgão sem exigir mudança no SysDoc.

---

## Documentação adicional

| Arquivo | Conteúdo |
|---------|----------|
| `skills/sysdoc/SKILL.md` | Fluxo canônico IA-agnóstico: lentes, schema, exemplos comentados, checklist final, hierarquia normativa. |
| `AGENTS.md` | Instruções genéricas para qualquer harness de IA (Codex, Antigravity, Cline, Gemini CLI, Cursor). |
| `CLAUDE.md` | Notas específicas do Claude Code, incluindo prioridade de ferramentas de extração de PDF. |
| `templates/schema_sysdoc.json` | Schema JSON canônico do `dados_consolidados.json`. |
| `templates/validate_sysdoc.py` | Validador determinístico (schema, coerência, PT-BR, rastreabilidade). Imutável. |
| `templates/render_analise.py` | Renderizador HTML determinístico. Imutável. |
| `tests/test_validate.py`, `tests/test_cli.py` | Testes automatizados. Rode `python -m pytest tests/ -v` antes e depois de qualquer mudança. |
| `CHANGELOG.md` | Histórico de versões. |
| `.planning/` | Artefatos do workflow GSD: PROJECT.md, ROADMAP.md, STATE.md, fases (`phases/NN-*/`). |

---

## Exemplo didático: do zero ao deploy nos dois fluxos

Cenário fictício: análise da contratação **"Aquisição de Notebooks 2026"** (contratação de TIC). Os dois fluxos partem da mesma estrutura de projeto e terminam no mesmo lugar — JSON validado, HTML renderizado, DOCX para assinatura e deploy. O que muda é **quem faz a análise**:

| | Fluxo A — original (agente de IA) | Fluxo B — motor DVI (`sysdoc-dvi`) |
|---|---|---|
| Quem analisa | o harness de IA (Claude Code, OpenCode, etc.) lendo `skills/sysdoc/SKILL.md` | o binário `sysdoc-dvi`, via API, dirigido por `checklists/dvi.yaml` |
| Produto típico | análise comparativa ETP × TR com foco temático livre | DVI (Despacho de Verificação Inicial) por checklist |
| Chamada de modelo | dentro do chat do agente | `sysdoc-dvi run` (único componente que chama modelo) |
| Reprodutibilidade | depende do prompt e do modelo usados na sessão | itens tipados, checklist com hash, checkpoint de retomada |
| Quando usar | exploração, dúvida específica, segunda opinião | diligência padronizada de rotina, comparável entre processos |

### Preparação comum aos dois fluxos

```bash
# 1. Criar o projeto (estrutura de pastas + .sysdoc/config.yaml)
sysdoc init Aquisicao-Notebooks-2026

# 2. Copiar os documentos do processo
cp ~/Downloads/ETP.pdf ~/Downloads/TR.pdf Aquisicao-Notebooks-2026/documentos/
cp ~/Downloads/MCP.pdf ~/Downloads/Mapa-de-Riscos.pdf Aquisicao-Notebooks-2026/documentos/   # peças extras usadas pelo DVI
cp ~/modelos/dvi.docx Aquisicao-Notebooks-2026/referencias/                                  # template institucional p/ create dvi

# 3. Conferir o que foi encontrado
sysdoc status

# 4. (Opcional) Configurar o deploy uma única vez
sysdoc config --vps usuario@servidor --path /caminho/publico/html Aquisicao-Notebooks-2026
```

### Fluxo A — original: o agente de IA analisa

```bash
# 5A. Extrair textos e gerar o handoff para o agente
sysdoc analyze Aquisicao-Notebooks-2026 -i "foco em garantia contratual e sanções"
```

O comando roda o `prepare` (cache determinístico em `.sysdoc/cache/`) e imprime o slash command exato para colar no harness:

```
/sysdoc analyze Aquisicao-Notebooks-2026 foco em garantia contratual e sanções
```

O agente lê `contexto_sysdoc.md` + textos extraídos, aplica as lentes do `SKILL.md` e grava `dados_consolidados.json` na raiz do projeto.

```bash
# 6A. Validar, versionar o JSON e renderizar o HTML em uma etapa
sysdoc publish Aquisicao-Notebooks-2026
# → output/01_aquisicao-notebooks-2026_dados_2026-08-26.json
# → output/01_aquisicao-notebooks-2026_analise_2026-08-26.html

# 7A. (Opcional) Gerar o TR revisado em DOCX a partir do template em referencias/
sysdoc create Aquisicao-Notebooks-2026 tr

# 8A. Publicar o HTML na VPS
sysdoc deploy Aquisicao-Notebooks-2026
```

### Fluxo B — novo: o motor DVI analisa

```bash
# 5B. (Uma única vez por máquina) Mapear os modelos econômico/forte
sysdoc-dvi config --economico openrouter/deepseek-chat --forte anthropic/claude-opus-5
sysdoc-dvi config --listar    # confere sem ecoar chaves

# 6B. Rodar o pipeline completo — TIC inclui os itens específicos de tecnologia
sysdoc-dvi run Aquisicao-Notebooks-2026 --tipo tic
```

Um único comando encadeia tudo: filtra o checklist por aplicabilidade → roda `sysdoc prepare` se o cache não existir → mapeia as peças (ETP, TR, MCP, Mapa de Riscos) pelas âncoras do manifest → executa cada item do checklist (LLM para `presenca`/`julgamento`; Python puro para `calculo`/`vigencia`/`mecanica`) → grounding check do campo `de` → síntese dos pareceres no modelo forte → grava e valida `dados_consolidados.json` → renderiza o HTML → grava o relatório de execução em `output/`. Se a execução cair no meio, rodar de novo retoma do checkpoint, pulando itens já resolvidos.

```bash
# 7B. Revisar: reimprimir o relatório (status por item, falhas de grounding, custo)
sysdoc-dvi relatorio Aquisicao-Notebooks-2026

# 8B. Após revisão humana do JSON/HTML, gerar a minuta do DVI em DOCX
sysdoc create Aquisicao-Notebooks-2026 dvi
# → output/01_aquisicao-notebooks-2026_dvi_2026-08-26.docx

# 9B. Publicar o HTML na VPS
sysdoc deploy Aquisicao-Notebooks-2026
```

### Os dois fluxos convivem

O mesmo projeto aceita os dois: rode o Fluxo B para a diligência padronizada e, em seguida, o Fluxo A para aprofundar um ponto específico com outro modelo. Cada `publish`/`run` versiona seus artefatos com contador próprio (`01_`, `02_`, ...), e `sysdoc compare` lista todas as análises lado a lado:

```bash
sysdoc compare Aquisicao-Notebooks-2026
```

Regra de ouro em ambos: `create dvi`/`create tr` e `deploy` são sempre passos manuais — a minuta exige revisão humana antes de assinar ou publicar.
