# SysDoc

Ferramenta de análise comparativa técnica e jurídica entre o Estudo Técnico Preliminar (ETP) e o Termo de Referência (TR) de processos de contratação pública brasileira regidos pela Lei 14.133/2021.

A análise é executada em duas camadas complementares:

1. **CLI determinística** (`sysdoc`) — extrai PDFs e DOCX, prepara um contexto canônico, valida o JSON consolidado contra schema, versiona o JSON por modelo de IA + data, renderiza HTML imutável e faz o deploy via SSH. Não realiza chamadas a modelos de linguagem.
2. **Agente de IA** (Claude Code, OpenCode, Codex, Antigravity, Cline, Gemini CLI, Cursor, ou qualquer outro harness) — lê os artefatos da CLI, aplica as lentes de análise definidas em `skills/sysdoc/SKILL.md` e produz `dados_consolidados.json`.

A separação garante reprodutibilidade: o mesmo JSON, validado pelo mesmo validador, gera sempre o mesmo HTML. A análise pode ser repetida com modelos distintos sem retrabalho de extração ou renderização.

---

## Sumário

1. [Requisitos](#requisitos)
2. [Instalação](#instalação)
3. [Arquitetura e pipeline](#arquitetura-e-pipeline)
4. [Exemplo completo: do init ao deploy](#exemplo-completo-do-init-ao-deploy)
5. [Comandos da CLI](#comandos-da-cli)
6. [Configuração por projeto (`.sysdoc/config.yaml`)](#configuração-por-projeto-sysdocconfigyaml)
7. [Suporte multi-harness](#suporte-multi-harness)
8. [Estrutura de um projeto](#estrutura-de-um-projeto)
9. [Schema canônico e regras de validação](#schema-canônico-e-regras-de-validação)
10. [Restrições do projeto](#restrições-do-projeto)
11. [Documentação adicional](#documentação-adicional)

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
                    | MeuProjeto/           |  <-- usuario copia ETP.pdf,
                    | +-- modelos/          |      TR.pdf e referencias
                    | +-- .sysdoc/          |
                    |     +-- config.yaml   |
                    +-----------+-----------+
                                |
                    [2] sysdoc analyze (ou prepare)
                                |
                                v
                    +-----------------------+
                    | .sysdoc/cache/        |  <-- extracao deterministica
                    | +-- textos/ETP.txt    |      (pypdf + ElementTree)
                    | +-- textos/TR.txt     |
                    | +-- textos/REF-*.txt  |
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
                    | dados_consolidados_   |
                    | [modelo]_[data].json  |
                    | analise_[modelo]_     |
                    | [data].html           |
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
| 2. Prepare/Analyze | CLI | `ETP.pdf`, `TR.pdf`, `modelos/*` | textos extraídos, `contexto_sysdoc.md`, `manifest.json` |
| 3. Análise | Agente de IA | `contexto_sysdoc.md`, textos extraídos, `SKILL.md`, `schema_sysdoc.json` | `dados_consolidados.json` |
| 4. Publish | CLI | `dados_consolidados.json` | JSON versionado + HTML versionado |
| 5. Deploy | CLI | HTML mais recente, `config.yaml` | `index{N}.html` na VPS |

---

## Exemplo completo: do init ao deploy

Cenário hipotético: aquisição de combustível tipo gasolina comum para a frota administrativa, processo SEI 12345.000123/2026-01.

### Passo 1 — Criar o projeto

```bash
sysdoc init Aquisicao-Combustivel-2026
```

Saída esperada:

```
Estrutura básica criada em: J:\COLOG\SEPAT\Diversos\SysDoc\Aquisicao-Combustivel-2026
  Configuração: Aquisicao-Combustivel-2026\.sysdoc\config.yaml
  Próximo passo: copie ETP.pdf e TR.pdf para Aquisicao-Combustivel-2026
```

A pasta criada contém:

```
Aquisicao-Combustivel-2026/
├── modelos/
├── .sysdoc/
│   └── config.yaml
└── README.md
```

`config.yaml` é gerado com valores padrão:

```yaml
projeto: Aquisicao-Combustivel-2026
vps_host: ""
vps_path: ""
modelo_ia_padrao: ""
```

### Passo 2 — Configurar o deploy (opcional)

Edite `Aquisicao-Combustivel-2026/.sysdoc/config.yaml` antes do deploy:

```yaml
projeto: Aquisicao-Combustivel-2026
vps_host: "root@76.13.170.15"
vps_path: "/opt/web/cfc-analise/html"
modelo_ia_padrao: "claude-sonnet-4-6"
```

Se os campos `vps_host` e `vps_path` ficarem em branco, o `sysdoc deploy` cai num fallback hardcoded definido em `sysdoc.py`.

### Passo 3 — Copiar os documentos de entrada

Coloque na pasta:

- `Aquisicao-Combustivel-2026/ETP.pdf` — Estudo Técnico Preliminar
- `Aquisicao-Combustivel-2026/TR.pdf` — Termo de Referência
- `Aquisicao-Combustivel-2026/modelos/` — pelo menos um arquivo de referência (modelo Delic, jurisprudência, parecer paradigma) em PDF, DOCX, TXT ou MD

Validar que os inputs estão corretos:

```bash
sysdoc status
```

Saída esperada:

```
PROJETO                          ETP    TR  MODELOS  JSON  HTML  PREP
-----------------------------------------------------------------------------
Aquisicao-Combustivel-2026        ok    ok       ok   ---   ---   ---

1 projeto(s) encontrado(s).
```

### Passo 4 — Preparar o contexto

```bash
sysdoc analyze Aquisicao-Combustivel-2026 -i "foco em garantia contratual e sanções administrativas"
```

A CLI roda `prepare` automaticamente (porque o cache ainda não existe), extrai o texto dos PDFs e DOCX, gera o mapa determinístico e imprime os caminhos:

```
Contexto preparado: Aquisicao-Combustivel-2026\.sysdoc\cache\contexto_sysdoc.md
Textos extraídos: Aquisicao-Combustivel-2026\.sysdoc\cache\textos
Contexto: Aquisicao-Combustivel-2026\.sysdoc\cache\contexto_sysdoc.md
Textos extraídos: Aquisicao-Combustivel-2026\.sysdoc\cache\textos
Manifest: Aquisicao-Combustivel-2026\.sysdoc\cache\manifest.json
Instrução adicional: foco em garantia contratual e sanções administrativas

Próximo passo: o Agente de IA deve ler os arquivos acima,
gerar dados_consolidados.json e rodar 'sysdoc publish'.
```

A pasta `.sysdoc/cache/` agora contém:

```
.sysdoc/cache/
├── manifest.json
├── contexto_sysdoc.md
└── textos/
    ├── ETP.txt
    ├── TR.txt
    └── REF-01_modelo-tr-servicos-continuados.txt
```

`contexto_sysdoc.md` é o mapa determinístico que o agente lê em vez de tokenizar os PDFs inteiros: traz briefing detectado (processo, objeto, valores), mapa de seções do ETP e TR, e snippets orientadores agrupados por tema (garantia, sanções, recebimento, pagamento, etc.).

### Passo 5 — Executar a análise pelo agente de IA

Abra o agente de IA na raiz do repositório do SysDoc (não dentro da pasta do projeto). O agente já reconhece o slash `/sysdoc` se a skill correspondente estiver instalada (`.claude/skills/` ou `.opencode/skills/`):

```
/sysdoc analyze Aquisicao-Combustivel-2026 foco em garantia contratual e sanções administrativas
```

Para harnesses sem wrapper de skill (Codex, Antigravity, Cline, Gemini CLI, Cursor), o agente lê `AGENTS.md` e segue a mesma instrução textualmente.

O agente:

1. Lê `skills/sysdoc/SKILL.md` (fonte única de verdade do fluxo).
2. Lê `Aquisicao-Combustivel-2026/.sysdoc/cache/contexto_sysdoc.md` e os arquivos em `textos/`.
3. Aplica as quatro lentes obrigatórias:
   - **Técnica** — clareza do objeto, escopo, entregáveis, critérios de aceite, preço, coerência ETP×TR.
   - **Jurídica** — Lei 14.133/2021, normas vinculantes, competitividade, habilitação, sanções, garantia, fiscalização, recebimento, pagamento.
   - **Delic/modelos** — confronta os achados contra os modelos de referência em `modelos/`.
   - **Consistência ETP×TR** — toda decisão técnica do TR precisa ter lastro no ETP, e vice-versa.
4. Seleciona entre 5 e 10 achados relevantes.
5. Produz `Aquisicao-Combustivel-2026/dados_consolidados.json` no schema canônico (`templates/schema_sysdoc.json`), preenchendo `modelo_ia` com o slug real do modelo (ex.: `claude-sonnet-4-6`, `gpt-5`, `gemini-2-5-pro`).

### Passo 6 — Validar, versionar e renderizar

```bash
sysdoc publish Aquisicao-Combustivel-2026
```

A CLI executa três operações em sequência:

1. **Validate** — roda `templates/validate_sysdoc.py`. Se houver erros, o publish aborta com saída não-zero e o agente deve corrigir o JSON e rodar `publish` novamente.
2. **Versionamento** — copia `dados_consolidados.json` para `dados_consolidados_[modelo_ia]_[data].json` (ex.: `dados_consolidados_claude-sonnet-4-6_2026-05-07.json`). Se um arquivo idêntico já existir para o mesmo modelo + data, mantém. Se houver conteúdo diferente, auto-incrementa com `_2`, `_3`, etc.
3. **Render** — gera `analise_[modelo_ia]_[data].html` por `templates/render_analise.py`.

Saída esperada:

```
SysDoc JSON válido.
JSON versionado: Aquisicao-Combustivel-2026\dados_consolidados_claude-sonnet-4-6_2026-05-07.json
HTML gerado: Aquisicao-Combustivel-2026\analise_claude-sonnet-4-6_2026-05-07.html
```

Se a validação falhar, a CLI lista os erros, por exemplo:

```
Erros de validação:
  - itens[3].risco_jurídico='bloqueante' exige severidade in {'crítica','alta'}, encontrado 'média'
  - parecer_executivo tem 312 palavras (mínimo 450)
  - itens[5].de não rastreável em ETP.txt
```

O agente deve ler os erros, corrigir o JSON e rodar `publish` novamente. Esse loop é parte explícita do fluxo `sysdoc all` documentado em `skills/sysdoc/SKILL.md`.

### Passo 7 — Fazer o deploy

```bash
sysdoc deploy Aquisicao-Combustivel-2026
```

A CLI:

1. Localiza o HTML mais recente em `Aquisicao-Combustivel-2026/`.
2. Lê `vps_host` e `vps_path` de `.sysdoc/config.yaml`.
3. Conecta no servidor por SSH e busca o próximo `index{N}.html` livre.
4. Envia o HTML por SCP renomeando para o índice descoberto.

Saída esperada:

```
Iniciando deploy do arquivo: Aquisicao-Combustivel-2026\analise_claude-sonnet-4-6_2026-05-07.html
Consultando root@76.13.170.15 via SSH para encontrar próximo índice disponível...
Enviando para root@76.13.170.15:/opt/web/cfc-analise/html/index42.html ...
Deploy concluído com sucesso!
```

### Passo 8 — Comparar versões (opcional)

Quando múltiplas IAs analisam o mesmo processo, ou quando o mesmo modelo é executado em datas diferentes:

```bash
sysdoc compare Aquisicao-Combustivel-2026
```

Saída esperada:

```
ARQUIVO                                                     MODELO                       DATA          ITENS   BLOQ  RELEV
---------------------------------------------------------------------------------------------------------------------------
dados_consolidados_claude-sonnet-4-6_2026-05-07.json        claude-sonnet-4-6            2026-05-07        9      2      4
dados_consolidados_gpt-5_2026-05-07.json                    gpt-5                        2026-05-07        7      1      5
dados_consolidados_gemini-2-5-pro_2026-05-07.json           gemini-2-5-pro               2026-05-07       10      3      3
```

### Macro `sysdoc all`

Para executar do passo 4 ao 7 num único pedido ao agente:

```
/sysdoc all Aquisicao-Combustivel-2026
```

O agente orquestra: `analyze` → leitura do cache → geração do JSON → `publish` (com loop de correção se a validação falhar) → `deploy`. O comportamento detalhado do macro está em `skills/sysdoc/SKILL.md`, seção "Fluxo de Análise".

---

## Comandos da CLI

| Comando | O que faz |
|---------|-----------|
| `sysdoc status` | Lista projetos no diretório atual e exibe flags de presença para ETP, TR, modelos, JSON, HTML e cache preparado. |
| `sysdoc init [pasta]` | Cria estrutura base (`modelos/`, `.sysdoc/config.yaml`). Não sobrescreve `config.yaml` se já existir. |
| `sysdoc prepare [pasta]` | Extrai texto de `ETP.pdf`, `TR.pdf` e arquivos em `modelos/` para `.sysdoc/cache/textos/`. Gera `contexto_sysdoc.md` e `manifest.json`. |
| `sysdoc analyze [pasta] [-i "instrução"]` | Roda `prepare` se o cache não existir e imprime os caminhos para o agente de IA. Aceita `--instruction`/`-i` para foco temático. |
| `sysdoc validate [pasta]` | Valida `dados_consolidados.json` contra o schema, regras de coerência, acentuação PT-BR e rastreabilidade do campo `de`. |
| `sysdoc render [pasta]` | Renderiza HTML a partir do JSON existente, sem versionar. |
| `sysdoc publish [pasta]` | Executa `validate` + versionamento de JSON por modelo+data + `render`. |
| `sysdoc deploy [pasta]` | Envia o HTML mais recente para a VPS via SSH/SCP, descobrindo o próximo `index{N}.html` livre. Lê `vps_host`/`vps_path` de `.sysdoc/config.yaml`. |
| `sysdoc compare [pasta]` | Lista todos os JSONs versionados do projeto com modelo, data, contagem de itens, bloqueantes e relevantes. |
| `sysdoc --version` | Exibe a versão instalada (1.2.0). |

Todos os comandos retornam código de saída convencional: 0 para sucesso, não-zero para falha. Nenhum comando faz chamadas a modelos de linguagem.

---

## Configuração por projeto (`.sysdoc/config.yaml`)

Criado automaticamente por `sysdoc init`. Schema:

```yaml
projeto: <nome-da-pasta>
vps_host: "<usuario>@<host>"      # ex.: "root@76.13.170.15"
vps_path: "<caminho-absoluto>"    # ex.: "/opt/web/cfc-analise/html"
modelo_ia_padrao: "<slug>"        # ex.: "claude-sonnet-4-6"
```

Comportamento:

- `vps_host` e `vps_path` em branco ⇒ `sysdoc deploy` usa o fallback hardcoded.
- `modelo_ia_padrao` é metadado informativo (não é lido pela CLI atualmente; reservado para Phase 2).

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
├── ETP.pdf                                   # obrigatório
├── TR.pdf                                    # obrigatório
├── modelos/                                  # obrigatório (>= 1 arquivo)
│   └── ...                                   # PDF, DOCX, TXT ou MD
├── .sysdoc/
│   ├── config.yaml                           # projeto, vps_host, vps_path, modelo_ia_padrao
│   └── cache/
│       ├── manifest.json                     # SHA256, contagens e mapeamentos por arquivo
│       ├── contexto_sysdoc.md                # mapa determinístico para a IA
│       └── textos/
│           ├── ETP.txt
│           ├── TR.txt
│           └── REF-NN_<nome>.txt
├── dados_consolidados.json                   # produzido pela IA, base para publish
├── dados_consolidados_[modelo]_[data].json   # versionado por publish
├── dados_consolidados_[modelo]_[data]_2.json # auto-incrementado se houver divergência
└── analise_[modelo]_[data].html              # relatório final renderizado
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
