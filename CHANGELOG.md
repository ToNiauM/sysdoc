# CHANGELOG — SysDoc

Todas as mudanças notáveis são documentadas aqui seguindo [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [1.2.0] — 2026-05-07

### Removido

- **`sysdoc_gui.py`**: GUI Tkinter removida. SysDoc passa a ser exclusivamente CLI + slash `/sysdoc` em harnesses de IA. Justificativa: agentes de IA (Claude Code, OpenCode, Codex, Antigravity, Cline, Gemini CLI) são a interface primária e não usam GUI; manter `tkinter` aumentava superfície de manutenção sem ganho prático.
- **`setup.py`**: removida referência a `sysdoc_gui` em `py_modules`.

### Adicionado

- **Phase 1 / GSD CLI-style** — SysDoc agora é invocável como sistema estilo GSD por agentes de IA via `/sysdoc [comando]`.
- **`sysdoc analyze [pasta] [-i instrução]`** (`sysdoc.py`): novo subcomando que roda `prepare` automaticamente quando o cache não existe e imprime os caminhos do contexto e dos textos extraídos. Aceita `--instruction` / `-i` para foco temático.
- **`.sysdoc/config.yaml`** (`sysdoc.py`): novo arquivo de configuração por projeto com `projeto`, `vps_host`, `vps_path` e `modelo_ia_padrao`. Criado automaticamente por `sysdoc init`.
- **`load_config()` e `init_config()`** (`sysdoc.py`): funções utilitárias para ler/criar configuração do projeto.
- **`ProjectPaths.config`** (`sysdoc.py`): dataclass agora inclui caminho para `.sysdoc/config.yaml`.
- **`deploy()` lê config.yaml** (`sysdoc.py`): `vps_host` e `vps_path` agora são lidos do config; valores hardcoded servem apenas como fallback.
- **`pyyaml>=6.0`** (`pyproject.toml`): adicionado às dependências.
- **`.opencode/skills/sysdoc-analise/SKILL.md`**: wrapper OpenCode equivalente ao Claude Code, sem MCP, prefere `sysdoc analyze` via Bash.
- **`AGENTS.md`**: arquivo genérico com instruções, comandos e regras-chave para todos os harnesses (Codex, Antigravity, Cline, Gemini CLI, etc.).
- **`tests/test_cli.py`**: 10 testes cobrindo `analyze`, `init_config`, `ProjectPaths.config`, formato YAML e `load_config`.

### Atualizado

- **`skills/sysdoc/SKILL.md`**: macros de acionamento incluem `/sysdoc analyze` e placeholder `/sysdoc create`. Fluxo `sysdoc all` agora começa por `sysdoc analyze`.
- **`.claude/skills/sysdoc-analise/SKILL.md`**: triggers atualizados para `/sysdoc`, `sysdoc analyze`, `sysdoc deploy`, `sysdoc create`. Exemplos usam `sysdoc` direto em vez de `python sysdoc.py`.
- **`CLAUDE.md`**: referência a `AGENTS.md` para outros agentes.

---

## [1.1.0] — 2026-05-06

### Adicionado
- **M1-B** (`sysdoc.py`): `extract_pdf()` avisa quando texto extraído < 100 chars (PDF provavelmente escaneado).
- **M1-C** (`sysdoc.py`): `extract_docx()` agora extrai tabelas (`w:tbl`) além de parágrafos, separando células com ` | `.
- **M2-A** (`sysdoc.py`): `analyze()` faz retry automático com erros da validação incluídos no prompt quando o JSON retornado falha na validação. Nova função auxiliar `run_validate_and_capture()`.
- **M2-B** (`sysdoc.py`): `call_openrouter_json()` usa `json_schema` formal para modelos `openai/` e `google/`; demais usam `json_object`.
- **M3-A** (`sysdoc.py`): `status()` renderiza tabela alinhada com colunas `ETP TR MODELOS JSON HTML PREP`.
- **M3-B** (`sysdoc_gui.py`): campo "Instrução extra" na GUI, passado como `--instruction` ao chamar `analyze`.
- **M3-C** (`sysdoc.py`): novo subcomando `sysdoc compare [pasta]` — lista JSONs versionados com resumo de itens, bloqueantes e relevantes por modelo.
- **M4-B** (`pyproject.toml`): configuração do linter `ruff>=0.4` em `[tool.ruff.lint]` com regras E/F/W/I.

### Corrigido
- **M1-A** (`sysdoc.py`, `pyproject.toml`): dependência `PyPDF2` (deprecada) substituída por `pypdf>=4.0.0`.

---

## [1.0.0] — 2026-05-06

### Adicionado
- **`sysdoc init [pasta]`** — cria estrutura básica de um novo projeto SysDoc via CLI, com ou sem template em `templates/projeto-padrao/`.
- **`sysdoc analyze --dry-run`** — prepara o contexto e exibe o prompt completo sem chamar a LLM. Útil para inspecionar o que seria enviado.
- **`sysdoc --version`** — exibe a versão instalada.
- **`sysdoc models` com filtro e paginação** — o usuário pode filtrar por texto e navegar com [P]róxima/[V]oltar entre páginas de 30 modelos.
- **`sysdoc connect` com validação de chave** — a chave de API é testada com uma chamada real antes de ser salva (✅ ou ⚠️).
- **`python templates/validate_sysdoc.py --json`** — output estruturado em JSON para integrações externas.
- **`tests/test_validate.py`** — 27 testes automatizados cobrindo validador, rastreabilidade, coerência de enums e funções utilitárias.
- **`ROADMAP.md`** — documento de próximas melhorias planejadas, legível por qualquer modelo de IA.
- **GUI: botões 🔑 Conectar API e 📝 Modelos** — abre terminal interativo para `sysdoc connect` e `sysdoc models`.
- **GUI: indicador de progresso pulsante** — label anima com `...` durante execução.
- **GUI: botão 📄 Abrir HTML** — habilitado automaticamente após render/publish, abre no navegador padrão.
- **`pyproject.toml`** completo com authors, license MIT, keywords e dependência dev `pytest`.

### Corrigido
- **B1** (`sysdoc_gui.py`): modelo padrão hardcoded `gpt-5.4-mini` (inexistente) substituído por leitura dinâmica do `~/.sysdoc/config.json`.
- **B3** (`sysdoc.py`): leitura dos textos extraídos após `prepare` usa path absoluto consistente, sem lógica frágil de `is_absolute()`.
- **B4** (`sysdoc.py`): chamadas LLM agora têm retry com backoff exponencial (5s → 10s → 20s) para erros 429, 500, 502, 503, 504.
- **B5** (`sysdoc_gui.py`): `create_project()` não trava mais com `iterdir()` quando a pasta não existe.
- **B7** (`validate_sysdoc.py`): entrada duplicada `"orgao"` removida do dicionário `PT_BR_ACCENT_TERMS`.
- **B8** (`sysdoc.py`): regex de detecção de processo corrigida para cobrir formato SEI `NNNNN.NNNNNN/AAAA-NN`.
- **C5** (`sysdoc.py`): mensagem de erro ao rodar sem API key citava `sysdoc config`; corrigido para `sysdoc connect`.
- **D4** (`sysdoc.py`): arquivos `ETP.pdf` e `TR.pdf` agora são encontrados de forma case-insensitive (`etp.pdf`, `Etp.pdf`, etc.).

### Refatorado
- **C1** (`sysdoc.py`): `call_openai_json` e `call_openrouter_json` (80% idênticos) unificados na função base `_call_openai_compatible_json`.
- **C2** (`sysdoc.py`): removida função `detect_provider()` (código morto, nunca chamada).
- **C3** (`sysdoc.py`): help text de `--model` corrigido de "Modelo OpenAI" para agnóstico.
- **C4** (`sysdoc_gui.py`): label "Modelo OpenAI" → "Modelo".
- **C7** (`pyproject.toml`): versão bumped de `0.1.0` para `1.0.0`; metadados completos.

---

## [0.1.0] — 2026-04-27

### Adicionado
- CLI inicial com subcomandos: `status`, `connect`, `models`, `prepare`, `analyze`, `validate`, `render`, `publish`.
- Fluxo IA-agnóstico com suporte a OpenRouter, OpenAI, Gemini e Anthropic.
- Extração determinística de PDFs e DOCX para cache em `.sysdoc/cache/`.
- Geração de `contexto_sysdoc.md` com briefing, mapa de seções e extratos por tema.
- Schema canônico `templates/schema_sysdoc.json` com validação de coerência.
- Validador determinístico `templates/validate_sysdoc.py` com verificação de acentuação PT-BR e rastreabilidade.
- Renderizador HTML `templates/render_analise.py` com template imutável.
- Versionamento de JSON por modelo/data (`dados_consolidados_[modelo]_[data].json`).
- GUI Tkinter básica (`sysdoc_gui.py`).
- Skill canônica em `skills/sysdoc/SKILL.md`.
