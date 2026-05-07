---
name: sysdoc-analise
description: Analisa comparativamente ETP.pdf e TR.pdf de licitação contra modelos/referências, gera dados_consolidados.json validado e HTML determinístico nomeado como analise_[modelo_ia]_[data].html. Acione quando o usuário digitar "/sysdoc", "sysdoc analyze", "sysdoc render", "sysdoc deploy", "sysdoc create", "sysdoc [pasta]", "sysdoc [pasta] - [instrução]", ou pedir análise/comparação de documentos de licitação (ETP, TR, Delic, modelos).
---

# SysDoc — Wrapper Claude Code

Este arquivo é um **wrapper fino** para o Claude Code. Toda a especificação operacional (fluxo, lentes, schema, enums, regras de redação, exemplos, checklist) é **IA-agnóstica** e fica em:

```text
skills/sysdoc/SKILL.md
```

**Antes de qualquer ação**, leia `skills/sysdoc/SKILL.md`. É a fonte única de verdade e serve qualquer IA que opere o fluxo (Claude, GPT, Gemini, outras).

## Ajustes específicos do Claude Code

1. **Identificador do modelo** — preencha `modelo_ia` no JSON com o identificador real do modelo Claude em uso (ex.: `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5`). O renderizador usa esse valor no nome do arquivo final.

2. **Extração de PDF** — preferência, nesta ordem:
   - `sysdoc analyze [pasta]` — roda `prepare` automaticamente quando o cache não existe e imprime os caminhos do contexto e dos textos extraídos. **Preferido**.
   - `sysdoc prepare [pasta]` — quando você só quer gerar o cache sem as instruções de análise.
   - MCP `PDF_Tools` (`read_pdf_content`) — já autorizado em `.claude/settings.local.json`.
   - `pdftotext -layout` via Bash, se disponível.
   - `pandoc` para `.docx` das referências.
   - Ler `.txt` direto quando já existir versão textual na pasta.

   Não use ferramenta de imagem em PDFs com camada de texto — gasta tokens sem ganho.

3. **Validação e render** — sempre via Bash, nunca escreva HTML manualmente:
   ```bash
   sysdoc validate [pasta]
   sysdoc publish [pasta]
   sysdoc render [pasta]
   sysdoc deploy [pasta]
   ```
   (Se o entry point `sysdoc` não estiver instalado, use `python sysdoc.py …`.)

4. **Português brasileiro** — todos os campos gerados devem usar norma culta e acentuação correta. Preserve literalidade apenas no campo `de`.

Qualquer divergência entre este wrapper e `skills/sysdoc/SKILL.md` — prevalece o canônico neutro.
