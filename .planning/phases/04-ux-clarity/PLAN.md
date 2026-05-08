# Phase 4 — Clareza de UX: Fim da Ambiguidade `sysdoc analyze`

## Princípio (não-negociável)

**A CLI do SysDoc é 100% determinística. Ela nunca chama LLMs.**

A análise técnica/jurídica é feita pelo "cérebro" da IA dentro de um **harness consagrado** (Claude Code, OpenCode, Codex, Gemini CLI, etc.) via slash command (`/sysdoc analyze ...`). O harness é quem lê o cache, raciocina e produz `dados_consolidados.json`.

Esta fase **não** introduz `--auto`, `sysdoc auto`, modo "autônomo no terminal" ou qualquer caminho que peça à CLI para chamar provider de LLM. Toda mensagem de UX deve reforçar — e nunca contradizer — esse princípio.

## Motivação

`sysdoc analyze [pasta]` é hoje **enganoso**:

- Dentro de um harness, o agente intercepta o slash, roda a CLI, lê o cache, gera o JSON. Funciona.
- No terminal puro, `python sysdoc.py analyze Pasta` extrai PDFs e imprime "Próximo passo: o Agente de IA deve ler os arquivos acima…" — uma mensagem que pressupõe que o usuário sabe o que é um agente, qual abrir, e como passar o contexto. Usuário novo fica perdido.

O nome `analyze` cria expectativa de análise. A CLI entrega preparação. A correção não é renomear — é **deixar absolutamente claro o que é responsabilidade da CLI (preparar) e o que é responsabilidade do harness (analisar)**, e fornecer instruções concretas para colocar o usuário no harness certo.

## Objetivo

Após esta fase, um usuário que rode `sysdoc analyze` ou `sysdoc guia` deve, sem abrir documentação, saber:

1. O que a CLI acabou de fazer (extraiu PDFs e gerou cache).
2. Que a análise precisa ser disparada **dentro de um harness de IA** — não há caminho alternativo.
3. Quais harnesses são suportados e qual o slash command exato a colar no chat.
4. Onde está o cache, caso ele precise inspecionar.

## Critérios de Aceite

1. `python sysdoc.py analyze Pasta` imprime um diagrama ASCII que:
   - Anuncia que cache foi preparado.
   - Diz explicitamente "este comando NÃO executa análise — análise acontece dentro de um harness de IA".
   - Lista pelo menos 3 harnesses suportados (Claude Code, OpenCode, Codex/Gemini CLI).
   - Mostra o slash command exato a colar (`/sysdoc analyze <pasta>`).
   - Mostra os caminhos do cache (`paths.cache`, `paths.context`).
2. `python sysdoc.py guia [pasta]` é um wizard de onboarding que:
   - Verifica pré-requisitos (`ETP.pdf`, `TR.pdf`, `modelos/`).
   - Oferece configurar VPS (`vps_host`, `vps_path`) se ainda não estiver no `config.yaml`.
   - Roda `prepare` automaticamente.
   - Imprime instruções específicas para o harness escolhido pelo usuário.
   - Salva `.sysdoc/cache/roteiro.txt` com os comandos exatos para o projeto.
3. `sysdoc guia` detecta `sys.stdin.isatty() is False` e sai com código 1 + mensagem útil em vez de travar em `input()` (proteção contra rodar dentro de harness ou em pipe).
4. `python sysdoc.py analyze Pasta --dry-run` imprime o diagrama sem reextrair PDFs (útil para reler instruções quando o cache já existe).
5. Nenhum texto de saída, comentário, docstring ou doc menciona "modo autônomo", "--auto", "análise no terminal", "OpenRouter", "API key" no contexto da CLI.
6. `python -m pytest tests/ -v` passa, incluindo os novos testes.

---

## Tarefas

### A1. Refatorar `print_analysis_handoff()` em `sysdoc.py`

Substituir o output das linhas 440-449 por um diagrama estruturado.

- [ ] Criar `_render_handoff_box(paths: ProjectPaths, instruction: str = "") -> str`.
- [ ] Conteúdo de referência (texto exato pode variar):

  ```
  ╔══════════════════════════════════════════════════════════════════╗
  ║  CACHE PREPARADO                                                 ║
  ║                                                                  ║
  ║  Os textos de ETP.pdf e TR.pdf foram extraídos e estão prontos.  ║
  ║                                                                  ║
  ║  ▸ A CLI do SysDoc NÃO executa análise.                          ║
  ║    A análise é feita pela IA dentro de um harness.               ║
  ║                                                                  ║
  ║  ANÁLISE — abra um harness de IA na pasta deste projeto e        ║
  ║  digite no chat:                                                 ║
  ║                                                                  ║
  ║      /sysdoc analyze <pasta>                                     ║
  ║                                                                  ║
  ║  Harnesses suportados:                                           ║
  ║      • Claude Code        • OpenCode                             ║
  ║      • Codex CLI          • Gemini CLI                           ║
  ║                                                                  ║
  ║  Não sabe por onde começar?                                      ║
  ║      sysdoc guia <pasta>                                         ║
  ║                                                                  ║
  ║  Cache:    <paths.cache>                                         ║
  ║  Contexto: <paths.context>                                       ║
  ╚══════════════════════════════════════════════════════════════════╝
  ```

- [ ] Se `instruction` for não-vazia, incluir linha "Instrução adicional: <instruction>" antes do bloco "ANÁLISE".
- [ ] `print_analysis_handoff()` passa a só chamar `print(_render_handoff_box(...))`.
- [ ] Remover qualquer texto que sugira caminho alternativo (terminal puro, autônomo, etc.).

### A2. Adicionar `--dry-run` ao `analyze`

- [ ] Em `build_parser()`, `analyze_parser.add_argument("--dry-run", action="store_true", help="Reimprime o handoff sem reextrair PDFs.")`.
- [ ] Em `analyze()`, se `dry_run=True`:
  - Não chamar `prepare()`.
  - Se `paths.context` não existe, imprimir aviso e retornar 1.
  - Caso contrário, imprimir o handoff box e retornar 0.
- [ ] Atualizar `main()` para passar `args.dry_run`.

### A3. Criar comando `sysdoc guia`

- [ ] Nova função `guia(project: str) -> int` em `sysdoc.py`.
- [ ] Subparser `guia` em `build_parser()` com argumento `project` (default `.`).
- [ ] Roteamento em `main()`.

**Comportamento (modo interativo, `sys.stdin.isatty() is True`):**

1. Verifica `ETP.pdf`, `TR.pdf`, `modelos/` via `_find_file_case_insensitive` / `paths.modelos`. Se faltar, instrui o que copiar para a pasta e retorna 1.
2. Lê `config.yaml`. Se `vps_host` ou `vps_path` estiverem vazios, pergunta se quer configurar agora; se sim, lê valores e chama `config_command(...)`.
3. Pergunta qual harness o usuário usa, com lista numerada:

   ```
   Qual harness de IA você vai usar para a análise?
     1) Claude Code
     2) OpenCode
     3) Codex CLI
     4) Gemini CLI
     5) Outro / não tenho certeza
   ```

4. Roda `prepare(project)`.
5. Imprime instruções específicas:
   - Para 1–4: nome do binário (`claude`, `opencode`, `codex`, `gemini`), comando para abrir o harness na pasta, e o slash command exato a colar (`/sysdoc analyze <pasta>`).
   - Para 5: lista todos os harnesses + link para `AGENTS.md` na raiz do repo.
6. Salva `.sysdoc/cache/roteiro.txt` com:
   - Pasta do projeto.
   - Harness escolhido.
   - Comando para abrir o harness.
   - Slash command exato.
   - Próximos comandos da CLI a rodar depois (`sysdoc validate`, `sysdoc publish`, `sysdoc deploy`).
7. Retorna 0.

**Comportamento (modo não-interativo, `sys.stdin.isatty() is False`):**

- Não chama `input()`.
- Imprime: "guia interativo requer terminal interativo. Para ver o handoff sem interação, use: sysdoc analyze <pasta> --dry-run".
- Retorna 1.

### A4. Testes em `tests/test_cli.py`

- [ ] `test_handoff_box_states_no_analysis` — output contém frase indicando que a CLI não analisa.
- [ ] `test_handoff_box_lists_harnesses` — output cita "Claude Code", "OpenCode", "Codex", "Gemini".
- [ ] `test_handoff_box_shows_slash_command` — output contém literalmente `/sysdoc analyze`.
- [ ] `test_handoff_box_contains_paths` — output contém os caminhos `paths.cache` e `paths.context`.
- [ ] `test_handoff_with_instruction` — `-i "foco em garantia"` faz o texto aparecer no output.
- [ ] `test_handoff_box_does_not_mention_auto` — output **não** contém "auto", "OpenRouter", "API key", "autônomo" (regressão para evitar churn de princípio).
- [ ] `test_analyze_dry_run_skips_prepare` — `--dry-run` não atualiza `paths.context` (mtime preservado).
- [ ] `test_analyze_dry_run_without_cache_fails` — `--dry-run` em projeto sem cache retorna ≠ 0.
- [ ] `test_guia_help` — `sysdoc guia --help` funciona.
- [ ] `test_guia_non_tty_returns_1` — quando `sys.stdin.isatty()` é False, retorna 1 e não chama `input`.
- [ ] `test_guia_creates_roteiro` — modo interativo simulado (monkeypatch `input` + `sys.stdin.isatty`) cria `.sysdoc/cache/roteiro.txt` com o slash command.
- [ ] `test_guia_missing_inputs` — `guia` em pasta sem ETP/TR retorna 1.

### A5. Documentação

- [ ] `CHANGELOG.md`: entrada nova com:
  - "analyze: handoff visual deixando claro que a análise acontece no harness, não na CLI".
  - "analyze: novo flag --dry-run".
  - "Novo comando: sysdoc guia (onboarding para o harness)".
- [ ] `README.md`: na seção de comandos, ajustar a descrição de `analyze` para frase honesta ("prepara cache e mostra como disparar a análise no harness") e mencionar `guia`.
- [ ] **NÃO alterar:** `skills/sysdoc/SKILL.md`, `.claude/skills/sysdoc-analise/SKILL.md`, `.opencode/skills/sysdoc-analise/SKILL.md`, `AGENTS.md`. Os macros e slash commands continuam idênticos — esta fase é puramente UX da CLI determinística.

---

## Impacto por Arquivo

| Arquivo | Mudança |
|---------|---------|
| `sysdoc.py` | +`_render_handoff_box`, +`guia()`, +subparser `guia`, +`--dry-run` em `analyze`, refator de `print_analysis_handoff` |
| `tests/test_cli.py` | +12 testes (incluindo regressão "no LLM mention") |
| `README.md` | Texto honesto de `analyze` + menção a `guia` |
| `CHANGELOG.md` | Entrada nova |

---

## O que esta fase deliberadamente NÃO faz

- **Não chama LLM.** A CLI continua 100% offline e determinística. Análise é função do harness. Este é um princípio permanente, não um TODO futuro.
- **Não renomeia comandos.** `analyze`, `prepare`, `all` mantêm os nomes. A confusão era a *mensagem*, não o *nome*.
- **Não toca em SKILL.md, AGENTS.md ou wrappers.** Os contratos com os harnesses não mudam.
- **Não modifica `templates/`.** Renderer, validator e schema permanecem imutáveis.

---

## Ordem de Execução (commits atômicos)

1. A1 — `_render_handoff_box` + refator de `print_analysis_handoff`.
2. A2 — `--dry-run` no `analyze`.
3. A3 — `sysdoc guia` com `isatty()` check.
4. A4 — testes (incluindo a regressão "no LLM mention").
5. A5 — README + CHANGELOG.

---

*Phase: 4 | Tarefas: 5 | Princípio: CLI determinística, análise no harness*
*Atualizado: 2026-05-07*
