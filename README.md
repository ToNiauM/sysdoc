# SysDoc

## Objetivos e Propósito

O SysDoc nasceu da necessidade de automatizar e especializar a conferência técnica e jurídica entre o Estudo Técnico Preliminar (ETP) e o Termo de Referência (TR) em processos de contratação. O objetivo principal do projeto é servir como um especialista em comparação de documentos, capaz de:
- Identificar inconsistências, omissões e contradições entre os arquivos.
- Sugerir mudanças textuais prontas para copiar e colar.
- Apontar riscos jurídicos (bloqueantes, relevantes ou informativos) com alta precisão e fundamentação técnica.

Sua arquitetura foi construída para ser **IA-agnóstica**, ou seja, qualquer modelo moderno (Claude, GPT, Gemini) pode operá-lo seguindo um fluxo de trabalho (prompt) rigorosamente determinístico.

## Instalação e Configuração

Para instalar o SysDoc como um comando global no seu terminal, rode na pasta raiz do projeto:

```bash
pip install -e .
```

A partir de agora, você pode chamar `sysdoc` de qualquer diretório do seu terminal.

### 1. Conectar a uma API

O SysDoc trabalha com múltiplos provedores, sendo o **OpenRouter** o padrão de fábrica. Use o comando abaixo para escolher seu provedor e configurar a chave de API (OpenRouter, OpenAI, Gemini ou Anthropic):

```bash
sysdoc connect
```

### 2. Escolher o Modelo Padrão

Após configurar sua chave, você pode consultar a API em tempo real para listar os modelos disponíveis e definir qual você quer usar por padrão em todas as análises:

```bash
sysdoc models
```

*(Opcionalmente, você ainda pode definir variáveis de ambiente como `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY` ou `ANTHROPIC_API_KEY`)*.

## Uso (CLI Global)

```text
sysdoc [pasta]
sysdoc [pasta] - [instrução extra]
sysdoc render [pasta]
```

CLI determinístico (execute de qualquer lugar):

```bash
sysdoc status
sysdoc connect
sysdoc models
sysdoc prepare [pasta]
sysdoc analyze [pasta]
sysdoc validate [pasta]
sysdoc render [pasta]
sysdoc publish [pasta]
```

Interface gráfica local:

```bash
python sysdoc_gui.py
```

A GUI lista projetos e permite selecionar uma pasta ou criar projetos a partir de `templates/projeto-padrao/`.

Exemplos de uso via terminal:

```text
sysdoc analyze Complementares
sysdoc analyze Combustivel --model anthropic/claude-3.7-sonnet --instruction "foco em garantia contratual"
sysdoc render Leiloeiro
```

```bash
sysdoc prepare Combustivel
sysdoc analyze Combustivel
sysdoc publish Combustivel
```

## Estrutura Esperada

```text
[pasta]/
├── ETP.pdf
├── TR.pdf
├── modelos/ ou Modelos/
├── .sysdoc/cache/contexto_sysdoc.md
├── dados_consolidados.json
├── dados_consolidados_[modelo_ia]_[data].json
└── analise_[modelo_ia]_[data].html
```

O nome do HTML inclui o identificador real do modelo de IA que produziu a análise (ex.: `analise_claude-opus-4-7_2026-04-24.html`, `analise_gpt-5_2026-04-24.html`, `analise_gemini-2-5-pro_2026-04-24.html`). Isso evita colisões quando múltiplas IAs analisam a mesma pasta. Histórico do mesmo modelo/data usa `_2`, `_3`, ...

`dados_consolidados.json` é o arquivo ativo. `python sysdoc.py publish [pasta]` valida, preserva uma cópia versionada por modelo/data e renderiza o HTML.

## Fluxo Principal e Compatibilidade com Outras CLIs de IA

O fluxo operacional canônico (neutro a qualquer IA e com prompts determinísticos) fica em:

```text
skills/sysdoc/SKILL.md
```

**Integração de Agentes Externos**: O SysDoc foi projetado não só para ter uma CLI nativa (`sysdoc analyze`), mas também para permitir que você utilize **Gemini CLI, Claude Code, ou OpenCode** no mesmo fluxo de trabalho.
Essas ferramentas podem ler a documentação de prompt determinística e operar o `sysdoc prepare` e interagir com as pastas sem fricção.

Wrappers de harness específicos já inclusos:

- **Claude Code** → `.claude/skills/sysdoc-analise/SKILL.md` (apenas frontmatter + dicas de MCP/Bash; delega ao canônico)

A versão anterior (v3 com orchestrator + revisores em `agents/`) está preservada em `backup/sysdoc_20260424_125157/`.

## Preparação

Antes da análise por LLM, rode:

```bash
python sysdoc.py prepare [pasta]
```

Esse comando extrai textos para `[pasta]/.sysdoc/cache/textos/`, gera `[pasta]/.sysdoc/cache/manifest.json` e cria `[pasta]/.sysdoc/cache/contexto_sysdoc.md`.

O `contexto_sysdoc.md` é um mapa determinístico para economizar tokens: briefing provável, mapa de seções e extratos por tema. Ele não substitui a conferência dos trechos relevantes nos textos extraídos.

## Validação

```bash
python templates/validate_sysdoc.py [pasta]/dados_consolidados.json
sysdoc validate [pasta]
```

A validação reforça schema, coerência, `modelo_ia`, acentuação em norma culta do português brasileiro nos campos gerados e, quando houver cache preparado, rastreabilidade dos trechos `de`.

## Renderização

```bash
python templates/render_analise.py [pasta]/dados_consolidados.json [pasta]
sysdoc render [pasta]
```

Template (`templates/analise_template.html`) e renderizador (`templates/render_analise.py`) são **imutáveis** — mesmo JSON validado produz exatamente o mesmo HTML.
