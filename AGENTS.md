# SysDoc — Project Instructions for AI Agents

Arquivo genérico para **todos os harnesses de IA** (Claude Code, OpenCode, Codex, Antigravity, Cline, Gemini CLI, etc.). Wrappers específicos por harness existem em `.claude/skills/`, `.opencode/skills/` e similares — eles delegam ao SKILL canônico.

## What This Is

CLI IA-agnóstico para preparação, análise e geração determinística a partir de documentos. O caso comum continua sendo TR/ETP, mas a entrada agora é genérica: qualquer documento suportado em `documentos/`, com apoio em `referencias/`. A CLI é estritamente determinística e **não** faz chamadas a LLM — quem analisa é o Agente de IA externo (você), lendo os artefatos gerados pela CLI.

## Single Source of Truth

**Antes de qualquer ação, leia `skills/sysdoc/SKILL.md`.** Fluxo canônico, lentes obrigatórias, schema, enums, regras de redação, exemplos e checklist final estão lá. Este arquivo só lista os comandos e regras de alto nível.

## Commands

```bash
sysdoc status                            # lista projetos e estado operacional
sysdoc init [pasta]                      # cria estrutura base + .sysdoc/config.yaml
sysdoc prepare [pasta]                   # extrai PDFs/DOCX para .sysdoc/cache/
sysdoc analyze [pasta] [-i "instrução"]  # prepare + imprime caminhos para o agente
sysdoc config --vps <host> --path <dir> [pasta] # configura VPS e pasta remota
sysdoc validate [pasta]                  # valida dados_consolidados.json
sysdoc render [pasta]                    # renderiza HTML a partir do JSON
sysdoc publish [pasta]                   # validate + versionar JSON + render
sysdoc deploy [pasta]                    # envia HTML para VPS via SSH
sysdoc create [pasta] [tipo]             # gera DOCX a partir de JSON + template
sysdoc compare [pasta]                   # compara versões de análise
```

Se o entry point `sysdoc` não estiver instalado, use `python sysdoc.py …` na raiz do repositório.

## Macros de Prompt (Orquestrados pelo Agente)

Quando o usuário digitar uma macro, você (Agente) orquestra:

1. **`/sysdoc init [pasta]`** — rode `sysdoc init [pasta]`, peça documentos em `documentos/` e referências/templates em `referencias/`, depois `sysdoc analyze [pasta]`.
2. **`/sysdoc analyze [pasta] [prompt]`** — rode `sysdoc analyze [pasta] -i "prompt"`, leia `contexto_sysdoc.md` + `.sysdoc/cache/textos/`, gere `dados_consolidados.json`.
3. **`/sysdoc all [pasta]`** — orquestre: analyze → gerar JSON → publish → deploy.
4. **`/sysdoc render [pasta]`** — rode `sysdoc render [pasta]`.
5. **`/sysdoc deploy [pasta]`** — rode `sysdoc deploy [pasta]`.
6. **`/sysdoc create [pasta] [tipo]`** — rode `sysdoc create [pasta] [tipo]`; quando omitido, `tipo=tr`. Para `tipo=tr`, aplica revisão ETP com substituição `de`→`para`, seleciona template por categoria de contratação em `referencias/` e grava como `tr_[modelo]_[data].docx` na raiz do projeto.

## Key Rules

- **Templates imutáveis**: `templates/analise_template.html`, `templates/render_analise.py` e `templates/validate_sysdoc.py` **nunca** podem ser editados durante uma análise.
- **Nunca escreva HTML manualmente** — apenas o renderizador determinístico produz HTML.
- **`modelo_ia`** no JSON deve ser o **slug real** do modelo (ex.: `claude-sonnet-4-6`, `gpt-5`, `gemini-2-5-pro`). Valores genéricos (`ia`, `modelo`, `default`) reprovam na validação.
- **Português culto**: todos os campos gerados em norma culta com acentuação correta. Exceção: campo `de` preserva literalidade do documento original.
- **Não invente** artigos, acórdãos, números SEI, valores, datas ou cláusulas. Quando a base for insuficiente, classifique como `pendente`.
- **Coerência** (validador rejeita se violar):
  - `classificação=risco` → `risco_jurídico ∈ {relevante, bloqueante}`
  - `classificação=conforme` → `risco_jurídico=informativo`
  - `risco_jurídico=bloqueante` → `severidade ∈ {crítica, alta}`
- **`.sysdoc/config.yaml`** (criado por `sysdoc init`) tem `vps_host`, `vps_path`, `modelo_ia_padrao`. O `deploy` lê daqui se preenchido.

## Before Any Edit

1. Leia `skills/sysdoc/SKILL.md` (fluxo canônico).
2. Rode os testes: `python -m pytest tests/ -v`.
3. Faça suas mudanças, mantendo `templates/` imutável.
4. Rode os testes novamente — todos devem passar.
5. Atualize `CHANGELOG.md` com a mudança.
6. Commits atômicos por assunto.

## Project Structure

```
.
├── sysdoc.py                          # CLI entry point
├── pyproject.toml                     # dependencies (pypdf, pyyaml)
├── skills/sysdoc/SKILL.md             # canonical operational flow
├── .claude/skills/sysdoc-analise/     # Claude Code wrapper
├── .opencode/skills/sysdoc-analise/   # OpenCode wrapper
├── templates/
│   ├── analise_template.html          # IMMUTABLE
│   ├── render_analise.py              # IMMUTABLE
│   ├── validate_sysdoc.py             # IMMUTABLE
│   └── schema_sysdoc.json
├── tests/
│   ├── test_validate.py               # validator + utility tests
│   └── test_cli.py                    # CLI behavior tests
├── AGENTS.md                          # this file
├── CLAUDE.md                          # Claude Code-specific notes
└── [projetos]/                        # cada análise é uma subpasta
    ├── documentos/
    ├── referencias/
    ├── output/
    └── .sysdoc/
        ├── config.yaml                # projeto, vps_host, vps_path, modelo_ia_padrao
        └── cache/
            ├── manifest.json
            ├── contexto_sysdoc.md
            └── textos/
                ├── documentos/
                └── referencias/
```

`IGNORED_DIRS` (nunca tratado como projeto): `.git`, `.claude`, `backup`, `skills`, `templates`.
