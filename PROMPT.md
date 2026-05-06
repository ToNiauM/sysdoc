# PROMPT - SysDoc

> Versão: 4.3 | Atualizado em: 2026-04-27

Contrato mestre do SysDoc. O fluxo é **IA-agnóstico**: qualquer modelo (Claude, GPT, Gemini, outros) pode operá-lo seguindo o mesmo arquivo canônico.

## Fonte única de verdade

Toda a especificação operacional (fluxo, lentes, schema, enums, regras de redação, exemplos, checklist) fica em:

```text
skills/sysdoc/SKILL.md
```

Wrappers específicos de harness (por ex. `.claude/skills/sysdoc-analise/SKILL.md` para Claude Code) apenas adicionam dicas de ferramentas da plataforma e **delegam a lógica ao canônico**.

## Acionamento

```text
sysdoc [pasta]
sysdoc [pasta] - [instrução extra opcional]
sysdoc render [pasta]
```

CLI determinístico:

```bash
python sysdoc.py status
python sysdoc.py prepare [pasta]
python sysdoc.py validate [pasta]
python sysdoc.py render [pasta]
python sysdoc.py publish [pasta]
```

Exemplos:

```text
sysdoc Complementares
sysdoc Combustivel - foco nas contradições sobre garantia
sysdoc render Leiloeiro
```

`sysdoc render [pasta]` apenas reexecuta `templates/render_analise.py` sobre `[pasta]/dados_consolidados.json`. Não refaz análise.

## Objetivo

Analisar comparativamente:

- `[pasta]/ETP.pdf`
- `[pasta]/TR.pdf`
- referências em `[pasta]/modelos/` ou `[pasta]/Modelos/`

Gerar:

- `[pasta]/dados_consolidados.json`
- `[pasta]/dados_consolidados_[modelo_ia]_[data].json` quando publicado pelo CLI
- `[pasta]/analise_[modelo_ia]_[data].html`

O nome do HTML **sempre** inclui o identificador real do modelo de IA que produziu a análise (ex.: `analise_claude-opus-4-7_2026-04-24.html`, `analise_gpt-5_2026-04-24.html`, `analise_gemini-2-5-pro_2026-04-24.html`). Isso permite que múltiplas IAs operem o mesmo fluxo sem sobrescrever análises. Histórico do mesmo modelo/data usa sufixo `_2`, `_3`, ...

## Fluxo em alto nível

1. Verificar entradas obrigatórias.
2. Preparar contexto determinístico, quando possível:
   ```bash
   python sysdoc.py prepare [pasta]
   ```
3. Aplicar, no mesmo fluxo, as lentes técnica, jurídica, Delic/modelos e consistência ETP x TR. Não simule handoffs entre agentes.
4. Gerar JSON no schema canônico (`templates/schema_sysdoc.json`), preenchendo `modelo_ia` com o identificador real do modelo.
5. Validar:
   ```bash
   python templates/validate_sysdoc.py [pasta]/dados_consolidados.json
   python sysdoc.py validate [pasta]
   ```
6. Corrigir até passar.
7. Publicar:
   ```bash
   python sysdoc.py publish [pasta]
   ```
   ou renderizar diretamente:
   ```bash
   python templates/render_analise.py [pasta]/dados_consolidados.json [pasta]
   ```

## Regras inegociáveis

- Fonte única de verdade: `skills/sysdoc/SKILL.md` (neutro, IA-agnóstico).
- Template e renderizador são imutáveis: `templates/analise_template.html`, `templates/render_analise.py`.
- Nenhum HTML escrito manualmente. Publicação sempre via renderizador.
- `modelo_ia` sempre preenchido com o identificador real do modelo (nunca `ia`, `modelo`, `default` ou genérico).
- Todos os campos gerados devem usar norma culta do português brasileiro, com acentuação correta. Trechos `de` preservam a literalidade do documento original.
- Hierarquia normativa: `lei/norma aplicável > regulamento vinculante > modelo oficial > referência técnica confiável > texto atual`.
- Não inventar artigo, número SEI, acórdão, data, valor ou cláusula. Na dúvida, classificar como `pendente`.

## Histórico

- v4.3 (2026-04-27): adiciona CLI `sysdoc.py`, preparação determinística em `.sysdoc/cache/`, publicação com JSON versionado, validação de acentuação e rastreabilidade dos trechos `de`.
- v4.2 (2026-04-24): fluxo consolidado como IA-agnóstico; canônico em `skills/sysdoc/SKILL.md`; wrapper Claude Code em `.claude/skills/sysdoc-analise/SKILL.md`.
- v4.0: pasta `agents/` removida; conteúdo original (v3 com orchestrator + revisores) preservado em `backup/sysdoc_20260424_125157/`.
