# SysDoc — Análise comparativa de licitação assistida por IA

O **SysDoc** automatiza a conferência técnica e jurídica entre o **Estudo Técnico Preliminar (ETP)** e o **Termo de Referência (TR)** em processos de contratação pública (Lei 14.133/2021).

A CLI é **estritamente offline e determinística**: ela extrai os PDFs, prepara o contexto, valida o JSON da análise, renderiza o HTML e faz o deploy. **A análise em si é feita pelo seu agente de IA** (Claude Code, OpenCode, Codex, Antigravity, Cline, Gemini CLI, Cursor, etc.) lendo os artefatos que a CLI gera. Sem amarração a um modelo específico — o mesmo fluxo serve qualquer LLM.

---

## Instalação

```bash
git clone <repo> sysdoc
cd sysdoc
pip install -e .
```

O entry point `sysdoc` fica disponível em qualquer pasta. Requisitos: Python 3.10+.

---

## Pipeline Ideal

```
                    ┌────────────────────────┐
   sysdoc init      │  MeuProjeto/           │   ◀── você copia ETP.pdf, TR.pdf
   ─────────────▶   │  ├─ modelos/           │       e referências em modelos/
                    │  └─ .sysdoc/           │
                    │     └─ config.yaml     │
                    └───────────┬────────────┘
                                │
                                │  sysdoc analyze
                                ▼
                    ┌────────────────────────┐
                    │  .sysdoc/cache/        │   ◀── extração determinística
                    │  ├─ textos/ETP.txt     │       (pypdf + zipfile/DOCX)
                    │  ├─ textos/TR.txt      │
                    │  ├─ textos/REF-*.txt   │
                    │  ├─ contexto_sysdoc.md │
                    │  └─ manifest.json      │
                    └───────────┬────────────┘
                                │
                                │  Agente de IA lê contexto + textos
                                │  Aplica lentes (técnica, jurídica,
                                │  Delic, consistência ETP×TR)
                                ▼
                    ┌────────────────────────┐
                    │ dados_consolidados.json│   ◀── produzido pela IA,
                    └───────────┬────────────┘       respeitando schema canônico
                                │
                                │  sysdoc publish
                                ▼
                    ┌────────────────────────┐
                    │ dados_consolidados_    │
                    │  [modelo_ia]_[data].   │   ◀── versionamento por modelo+data
                    │       json             │
                    │ analise_[modelo_ia]_   │
                    │  [data].html           │
                    └───────────┬────────────┘
                                │
                                │  sysdoc deploy
                                ▼
                    ┌────────────────────────┐
                    │  VPS: index{N}.html    │   ◀── índice auto-incrementado
                    │  (vps_host/vps_path    │       lido de .sysdoc/config.yaml
                    │   em config.yaml)      │
                    └────────────────────────┘
```

A CLI nunca chama LLM. Quem analisa é o agente de IA que você está usando — o SysDoc fornece os artefatos determinísticos que tornam essa análise barata, rastreável e reproduzível.

---

## Workflow Recomendado (Passo-a-Passo)

### 1. Crie o projeto

```bash
sysdoc init MeuProjeto
```

Isso cria:

```
MeuProjeto/
├── modelos/                 # coloque PDF/DOCX/TXT/MD de referência aqui
├── .sysdoc/
│   └── config.yaml          # projeto, vps_host, vps_path, modelo_ia_padrao
└── README.md                # instruções básicas
```

Edite `MeuProjeto/.sysdoc/config.yaml` com o `vps_host` e `vps_path` se for fazer deploy.

### 2. Coloque os documentos

- `MeuProjeto/ETP.pdf` — Estudo Técnico Preliminar (obrigatório)
- `MeuProjeto/TR.pdf` — Termo de Referência (obrigatório)
- `MeuProjeto/modelos/` — Referências (modelos Delic, jurisprudência, etc.) (obrigatório, no mínimo 1 arquivo)

### 3. Prepare o contexto

```bash
sysdoc analyze MeuProjeto
```

A CLI:
- Roda `prepare` automaticamente se o cache ainda não existe
- Extrai texto de PDF/DOCX para `.sysdoc/cache/textos/`
- Gera `contexto_sysdoc.md` (mapa determinístico que economiza tokens da IA)
- Imprime os caminhos para o agente

Você pode passar uma instrução de foco:

```bash
sysdoc analyze MeuProjeto -i "foco em garantia contratual e sanções"
```

### 4. Peça a análise ao seu agente de IA

Abra o chat do seu agente **na pasta do SysDoc**. Os agentes que reconhecem o slash `/sysdoc` (Claude Code, OpenCode, etc.) entendem comandos como:

```
/sysdoc analyze MeuProjeto foco em garantia contratual
```

Para harnesses sem skill instalada, o atalho é igual:

```
sysdoc analyze MeuProjeto
```

O agente lê `skills/sysdoc/SKILL.md` (fonte única de verdade), o `contexto_sysdoc.md`, os textos extraídos, aplica as **lentes obrigatórias** (técnica, jurídica, Delic/modelos, consistência ETP×TR) e produz `MeuProjeto/dados_consolidados.json` no schema canônico (`templates/schema_sysdoc.json`).

### 5. Valide, versione e renderize

```bash
sysdoc publish MeuProjeto
```

Faz três coisas em sequência:
1. `sysdoc validate` — checa schema, coerência classificação×severidade×risco, acentuação PT-BR, rastreabilidade do `de`.
2. Versiona o JSON: `dados_consolidados_[modelo_ia]_[data].json`.
3. Renderiza HTML imutável: `analise_[modelo_ia]_[data].html`.

Se a validação falhar, o agente lê os erros, corrige o JSON e roda `publish` de novo.

### 6. Faça o deploy

```bash
sysdoc deploy MeuProjeto
```

Lê `vps_host` / `vps_path` de `.sysdoc/config.yaml`, descobre o próximo `index{N}.html` livre via SSH e envia por SCP. Se o config estiver vazio, usa o fallback hardcoded.

### 7. Compare versões (opcional)

```bash
sysdoc compare MeuProjeto
```

Tabela com modelo, data, número de itens, bloqueantes e relevantes — útil quando múltiplas IAs analisaram o mesmo processo.

---

## Macro `sysdoc all` (orquestração pelo agente)

Se quiser fazer tudo em um comando, peça ao agente:

```
/sysdoc all MeuProjeto
```

O agente orquestra as etapas 3–6 acima:

1. `sysdoc analyze MeuProjeto`
2. Lê o cache, gera `dados_consolidados.json`
3. `sysdoc publish MeuProjeto` (valida, versiona, renderiza — corrige iterativamente se a validação falhar)
4. `sysdoc deploy MeuProjeto`

---

## Comandos da CLI

| Comando | Determinístico | O que faz |
|---------|----------------|-----------|
| `sysdoc status` | sim | Lista projetos na pasta atual com flags ETP/TR/MODELOS/JSON/HTML/PREP. |
| `sysdoc init [pasta]` | sim | Cria estrutura base + `.sysdoc/config.yaml`. |
| `sysdoc prepare [pasta]` | sim | Extrai PDFs/DOCX para `.sysdoc/cache/textos/` e gera `contexto_sysdoc.md`. |
| `sysdoc analyze [pasta] [-i "foco"]` | sim | Roda `prepare` se necessário e imprime os caminhos para o agente. |
| `sysdoc validate [pasta]` | sim | Valida `dados_consolidados.json` (schema + coerência + PT-BR + rastreabilidade). |
| `sysdoc render [pasta]` | sim | Renderiza HTML a partir do JSON sem versionar. |
| `sysdoc publish [pasta]` | sim | Valida + versiona JSON por modelo/data + renderiza HTML. |
| `sysdoc deploy [pasta]` | sim | Envia o HTML mais recente para a VPS por SSH/SCP. |
| `sysdoc compare [pasta]` | sim | Compara versões geradas (modelo, data, contagem de riscos). |

Todos os comandos são **offline** e **não chamam LLM**. A análise vem do agente de IA que você está usando.

---

## Suporte multi-harness

Cada harness tem um wrapper fino que delega ao SKILL canônico:

| Harness | Wrapper | Como acionar |
|---------|---------|--------------|
| Claude Code | `.claude/skills/sysdoc-analise/SKILL.md` | `/sysdoc`, `sysdoc analyze`, "análise de licitação" |
| OpenCode | `.opencode/skills/sysdoc-analise/SKILL.md` | `/sysdoc`, `sysdoc analyze`, "análise de licitação" |
| Outros (Codex, Antigravity, Cline, Gemini CLI, Cursor) | `AGENTS.md` na raiz | Leia `AGENTS.md` + `skills/sysdoc/SKILL.md`, depois rode `sysdoc analyze` |

A fonte única de verdade operacional é `skills/sysdoc/SKILL.md` (IA-agnóstica). Os wrappers só adicionam dicas específicas do harness (ex.: MCP `PDF_Tools` no Claude Code, Bash-only no OpenCode).

---

## Estrutura de um projeto

```
MeuProjeto/
├── ETP.pdf                                # obrigatório
├── TR.pdf                                 # obrigatório
├── modelos/                               # obrigatório (≥ 1 arquivo)
│   └── ...                                # PDF, DOCX, TXT, MD
├── .sysdoc/
│   ├── config.yaml                        # projeto, vps_host, vps_path, modelo_ia_padrao
│   └── cache/
│       ├── manifest.json
│       ├── contexto_sysdoc.md             # mapa determinístico para a IA
│       └── textos/
│           ├── ETP.txt
│           ├── TR.txt
│           └── REF-*.txt
├── dados_consolidados.json                # produzido pelo agente de IA
├── dados_consolidados_[modelo]_[data].json # versionado por publish
└── analise_[modelo]_[data].html           # relatório final
```

Pastas reservadas (nunca tratadas como projeto): `.git`, `.claude`, `.opencode`, `backup`, `skills`, `templates`.

---

## Dicas importantes

- **PDF escaneado:** se o PDF não tiver camada de texto, a extração retorna conteúdo curto. O SysDoc avisa em `prepare`. Use `pdftotext -layout` ou OCR antes.
- **`modelo_ia` no JSON:** sempre o slug real do modelo que produziu a análise (`claude-sonnet-4-6`, `gpt-5`, `gemini-2-5-pro`). Valores genéricos (`ia`, `modelo`) reprovam na validação.
- **Português culto:** todos os campos gerados devem estar em norma culta com acentuação correta. Exceção: o campo `de` preserva literalidade do documento original.
- **Templates imutáveis:** `templates/analise_template.html`, `templates/render_analise.py` e `templates/validate_sysdoc.py` **não** podem ser editados durante uma análise. O HTML é sempre produto do renderizador determinístico.
- **Histórico:** cada `publish` cria um novo `analise_*.html` com modelo + data; o anterior fica intacto. Múltiplas IAs operam o mesmo projeto sem sobrescrever.
- **Configuração de deploy:** edite `MeuProjeto/.sysdoc/config.yaml` — se `vps_host` / `vps_path` ficarem em branco, `deploy` cai no fallback hardcoded.

---

## Documentação adicional

- `skills/sysdoc/SKILL.md` — fluxo canônico IA-agnóstico (lentes, schema, exemplos, checklist)
- `AGENTS.md` — instruções genéricas para qualquer harness de IA
- `CLAUDE.md` — notas específicas do Claude Code
- `CHANGELOG.md` — histórico de versões
- `.planning/` — artefatos GSD (PROJECT.md, ROADMAP.md, STATE.md, fases)
