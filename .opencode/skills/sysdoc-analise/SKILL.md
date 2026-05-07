---
name: sysdoc-analise
description: Analisa comparativamente ETP.pdf e TR.pdf de licitação contra modelos/referências, gera dados_consolidados.json validado e HTML determinístico nomeado como analise_[modelo_ia]_[data].html. Acione quando o usuário digitar "/sysdoc", "sysdoc", "sysdoc analyze", "sysdoc render", "sysdoc deploy", "sysdoc [pasta]", ou pedir análise de licitação (ETP, TR, Delic, modelos).
---

# SysDoc — Wrapper OpenCode

Este arquivo é um **wrapper fino** para o OpenCode. Toda a especificação operacional (fluxo, lentes, schema, enums, regras de redação, exemplos, checklist) é **IA-agnóstica** e fica em:

```text
skills/sysdoc/SKILL.md
```

**Antes de qualquer ação**, leia `skills/sysdoc/SKILL.md`. É a fonte única de verdade e serve qualquer IA que opere o fluxo (Claude, GPT, Gemini, outras).

Leia também `AGENTS.md` na raiz do projeto, se existir — contém regras gerais para todos os agentes.

## Ajustes específicos do OpenCode

1. **Identificador do modelo** — preencha `modelo_ia` no JSON com o slug real do modelo em uso (ex.: `gpt-5`, `gpt-5-mini`, `gemini-2-5-pro`, `claude-sonnet-4-6`, `llama-3-3-70b`). O renderizador usa esse valor no nome do arquivo final. Nunca use valores genéricos como `ia`, `modelo`, `default`.

2. **Extração de PDF** — preferência, nesta ordem (sem MCP, OpenCode usa Bash):
   - `sysdoc analyze [pasta]` — roda `prepare` automaticamente quando o cache não existe e imprime os caminhos do contexto e dos textos extraídos. **Preferido**.
   - `sysdoc prepare [pasta]` — quando você só quer gerar o cache.
   - `pdftotext -layout arquivo.pdf saida.txt` via Bash, se disponível.
   - `pandoc -o saida.txt arquivo.docx` para `.docx` das referências.
   - Ler `.txt` direto quando já existir versão textual na pasta.

   Se o entry point `sysdoc` não estiver instalado, use `python sysdoc.py …`.

3. **Validação e render** — sempre via Bash, nunca escreva HTML manualmente:
   ```bash
   sysdoc validate [pasta]
   sysdoc publish [pasta]
   sysdoc render [pasta]
   sysdoc deploy [pasta]
   ```

4. **Português brasileiro** — todos os campos gerados devem usar norma culta e acentuação correta. Preserve literalidade apenas no campo `de`.

5. **Templates imutáveis** — nunca edite `templates/analise_template.html`, `templates/render_analise.py` ou `templates/validate_sysdoc.py`. O HTML é gerado **somente** pelo renderizador determinístico.

Qualquer divergência entre este wrapper e `skills/sysdoc/SKILL.md` — prevalece o canônico neutro.
