---
wave: 1
depends_on: []
files_modified:
  - sysdoc.py
  - skills/sysdoc/SKILL.md
  - .claude/skills/sysdoc-analise/SKILL.md
  - AGENTS.md
  - .opencode/skills/sysdoc-analise/SKILL.md
autonomous: true
---

# Plan: CLI-style GSD

## Must-Haves

- [ ] CLI responde a `/sysdoc` no contexto de agentes
- [ ] Estrutura `.sysdoc/config.yaml` por projeto
- [ ] Comando `analyze` com prompt opcional
- [ ] AGENTS.md com instruções para todos os harnesses
- [ ] SKILL.md atualizado para novo fluxo de comandos

## Tasks

### Task 1: Adicionar comando `analyze` ao CLI

<read_first>
- sysdoc.py (CLI principal, linhas 592-650)
- skills/sysdoc/SKILL.md (fluxo canônico)
</read_first>

<action>
Em `sysdoc.py`, adicionar subcomando `analyze` ao argparse:

1. No `build_parser()` (linha 592), adicionar:
   ```python
   analyze_parser = sub.add_parser("analyze", help="Prepara contexto e exibe instruções para análise por LLM.")
   analyze_parser.add_argument("project", help="Pasta do projeto SysDoc.")
   analyze_parser.add_argument("--instruction", "-i", default="", help="Instrução extra para a LLM.")
   ```

2. No `main()` (linha 626), adicionar handler:
   ```python
   if args.command == "analyze":
       return analyze(args.project, instruction=args.instruction)
   ```

3. Criar função `analyze(project: str, instruction: str = "") -> int`:
   - Roda `prepare(project)` automaticamente se cache não existe
   - Imprime caminho do contexto: `paths.context`
   - Imprime caminho dos textos: `paths.source_cache`
   - Se `instruction` fornecida, imprime como dica
   - Retorna 0

O comando `analyze` é deliberadamente mínimo — ele apenas prepara e informa onde está o cache. A análise real é feita pelo harness (agente IA) lendo os arquivos.
</action>

<acceptance_criteria>
- `python sysdoc.py analyze --help` retorna ajuda do comando
- `python sysdoc.py analyze [pasta]` roda prepare se cache não existe e imprime caminhos
- `python sysdoc.py analyze [pasta] -i "foco em garantia"` imprime a instrução
- `sysdoc analyze` funciona como entry point (via pyproject.toml)
</acceptance_criteria>

---

### Task 2: Adicionar suporte a `.sysdoc/config.yaml`

<read_first>
- sysdoc.py (estrutura ProjectPaths, linhas 62-94)
- pyproject.toml (dependências)
</read_first>

<action>
1. Adicionar `pyyaml>=6.0` às dependências em `pyproject.toml`:
   ```toml
   dependencies = [
       "pypdf>=4.0.0",
       "pyyaml>=6.0",
   ]
   ```

2. Em `sysdoc.py`, adicionar à dataclass `ProjectPaths`:
   ```python
   config: Path  # .sysdoc/config.yaml
   ```
   Atualizar `project_paths()` para incluir `config=cache.parent / "config.yaml"`.

3. Criar função `init_config(project: str) -> int`:
   - Cria `.sysdoc/config.yaml` com valores padrão:
     ```yaml
     projeto: [nome da pasta]
     vps_host: ""
     vps_path: ""
     modelo_ia_padrao: ""
     ```
   - Não sobrescreve se já existe

4. Atualizar `init_command()` para chamar `init_config()` após criar estrutura.

5. Atualizar `deploy()` para ler `vps_host` e `vps_path` do config.yaml se disponível (fallback para hardcoded).
</action>

<acceptance_criteria>
- `pyyaml` adicionado às dependências
- `sysdoc init [pasta]` cria `.sysdoc/config.yaml` com valores padrão
- `project_paths()` inclui caminho para config
- `deploy()` lê config.yaml para VPS se disponível
- `python -m pytest tests/ -v` passa
</acceptance_criteria>

---

### Task 3: Atualizar SKILL.md para novo fluxo

<read_first>
- skills/sysdoc/SKILL.md (fluxo canônico atual)
</read_first>

<action>
Atualizar `skills/sysdoc/SKILL.md` para refletir os comandos `/sysdoc`:

1. Seção "Macros de Acionamento" — atualizar comandos:
   - `/sysdoc init [pasta]` — criar estrutura + preparar
   - `/sysdoc analyze [pasta] [prompt]` — preparar + analisar
   - `/sysdoc render [pasta]` — gerar HTML
   - `/sysdoc deploy [pasta]` — enviar VPS
   - `/sysdoc create [pasta] docx` — criar documento (placeholder para Phase 2)

2. Seção "Ferramentas de CLI" — atualizar para:
   ```bash
   sysdoc status
   sysdoc prepare [pasta]
   sysdoc analyze [pasta] [-i instrução]
   sysdoc validate [pasta]
   sysdoc render [pasta]
   sysdoc publish [pasta]
   sysdoc deploy [pasta]
   ```

3. Atualizar fluxo `sysdoc all` para `sysdoc analyze`:
   - Fase 1: Roda `sysdoc analyze [pasta]` (que inclui prepare)
   - Fase 2: Lê cache/contexto_sysdoc.md
   - Fase 3: Gera análise (LLM do harness)
   - Fase 4: Roda `sysdoc publish [pasta]`
   - Fase 5: Roda `sysdoc deploy [pasta]`
</action>

<acceptance_criteria>
- SKILL.md documenta comando `analyze` com `-i` flag
- Fluxo `sysdoc all` atualizado para `sysdoc analyze`
- Comando `create` documentado como placeholder
- Exemplos de invocação atualizados
</acceptance_criteria>

---

### Task 4: Atualizar wrapper Claude Code

<read_first>
- .claude/skills/sysdoc-analise/SKILL.md (wrapper atual)
</read_first>

<action>
Atualizar `.claude/skills/sysdoc-analise/SKILL.md`:

1. Atualizar `description` no frontmatter para incluir novos padrões de trigger:
   ```yaml
   description: Analisa comparativamente ETP.pdf e TR.pdf de licitação contra modelos/referências, gera dados_consolidados.json validado e HTML determinístico. Acione quando o usuário digitar "/sysdoc", "sysdoc analyze", "sysdoc render", "sysdoc deploy", "sysdoc create", ou pedir análise/comparação de documentos de licitação.
   ```

2. Atualizar seção de extração de PDF para mencionar `sysdoc analyze`:
   - Prefira `sysdoc analyze [pasta]` que já inclui prepare

3. Atualizar exemplos de validação/render para usar `sysdoc` diretamente (não `python sysdoc.py`)
</action>

<acceptance_criteria>
- `.claude/skills/sysdoc-analise/SKILL.md` trigger inclui `/sysdoc`
- Exemplos usam `sysdoc` command (não `python sysdoc.py`)
- Referência a `analyze` command incluída
</acceptance_criteria>

---

### Task 5: Criar SKILL para OpenCode

<read_first>
- .claude/skills/sysdoc-analise/SKILL.md (formato Claude Code)
</read_first>

<action>
Criar `.opencode/skills/sysdoc-analise/SKILL.md` — adaptação do wrapper Claude Code para OpenCode:

1. Mesma estrutura do wrapper Claude Code
2. Sem referências a MCP `PDF_Tools` (OpenCode não tem)
3. Prefere `sysdoc prepare` via Bash para extração
4. Trigger patterns: "sysdoc", "/sysdoc", "análise de licitação"

OpenCode usa `CLAUDE.md` como instructions file, então não precisa de settings.local.json.
</action>

<acceptance_criteria>
- `.opencode/skills/sysdoc-analise/SKILL.md` criado
- Sem referências a MCP tools
- Trigger patterns para OpenCode incluídos
</acceptance_criteria>

---

### Task 6: Criar AGENTS.md

<read_first>
- CLAUDE.md (instruções atuais)
- skills/sysdoc/SKILL.md (fluxo canônico)
</read_first>

<action>
Criar `AGENTS.md` na raiz do projeto — arquivo de instruções para todos os harnesses (Codex, Antigravity, etc.):

```markdown
# SysDoc — Project Instructions

## What This Is
CLI IA-agnóstico para análise comparativa de documentos ETP/TR em contratações públicas brasileiras.

## Commands
- `sysdoc status` — listar projetos
- `sysdoc init [pasta]` — criar estrutura
- `sysdoc prepare [pasta]` — extrair PDFs/DOCX para cache
- `sysdoc analyze [pasta] [-i instrução]` — preparar + exibir contexto para análise
- `sysdoc validate [pasta]` — validar JSON
- `sysdoc render [pasta]` — gerar HTML
- `sysdoc publish [pasta]` — validar + versionar + renderizar
- `sysdoc deploy [pasta]` — enviar HTML para VPS

## Key Rules
- `templates/analise_template.html` e `templates/render_analise.py` são imutáveis
- `skills/sysdoc/SKILL.md` é a fonte única de verdade operacional
- Rode `python -m pytest tests/ -v` antes e depois de qualquer mudança
- `modelo_ia` no JSON deve ser slug real do modelo
- Não invente artigos, acórdãos, números SEI, valores ou datas
- Todo campo gerado em português brasileiro culto com acentuação correta
- Campo `de` preserva literalidade do original

## Before Any Edit
1. Read `skills/sysdoc/SKILL.md`
2. Run tests: `python -m pytest tests/ -v`
3. Update `CHANGELOG.md` after changes
```

Também atualizar `CLAUDE.md` para referenciar `AGENTS.md`:
- Adicionar linha: "Para outros agentes de IA, veja `AGENTS.md`."
</action>

<acceptance_criteria>
- `AGENTS.md` criado na raiz com comandos e regras
- `CLAUDE.md` referencia `AGENTS.md`
- Arquivo é genérico o suficiente para qualquer harness
</acceptance_criteria>

---

### Task 7: Atualizar testes

<read_first>
- tests/test_validate.py (testes existentes)
- sysdoc.py (funções a testar)
</read_first>

<action>
Criar `tests/test_cli.py` com testes para:

1. `test_analyze_command_help` — `sysdoc analyze --help` funciona
2. `test_analyze_runs_prepare` — analyze roda prepare se cache não existe
3. `test_analyze_with_instruction` — instruction é impressa na saída
4. `test_init_creates_config` — init cria `.sysdoc/config.yaml`
5. `test_project_paths_includes_config` — ProjectPaths inclui config
6. `test_config_yaml_format` — config.yaml tem campos esperados

Usar `tmp_path` fixture do pytest para projetos temporários.
</action>

<acceptance_criteria>
- `tests/test_cli.py` criado com ≥ 6 testes
- `python -m pytest tests/test_cli.py -v` passa
- `python -m pytest tests/ -v` passa (regression)
</acceptance_criteria>

---

## Verification

1. `python -m pytest tests/ -v` — todos os testes passam
2. `sysdoc analyze --help` — comando documentado
3. `sysdoc init TestProject && cat TestProject/.sysdoc/config.yaml` — config criado
4. `sysdoc analyze TestProject -i "foco em garantia"` — instrução exibida
5. `.opencode/skills/sysdoc-analise/SKILL.md` existe
6. `AGENTS.md` existe na raiz
7. `skills/sysdoc/SKILL.md` documenta `analyze`
