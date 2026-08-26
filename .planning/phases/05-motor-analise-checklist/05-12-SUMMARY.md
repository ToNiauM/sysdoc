---
phase: 05-motor-analise-checklist
plan: 12
subsystem: create-dvi
tags: [docx, dvi, create, offline, docx-template]
dependency-graph:
  requires: ["05-02", "05-07"]
  provides: ["sysdoc create dvi"]
  affects: ["sysdoc.py:create", "sysdoc.py:render_docx_template"]
tech-stack:
  added: []
  patterns: ["zipfile-based DOCX placeholder substitution", "flatten_json for template values"]
key-files:
  created:
    - tests/test_dvi_create.py
  modified:
    - sysdoc.py
    - CHANGELOG.md
decisions:
  - "Task 1 (template institucional): nenhum arquivo real disponível no repositório; seguiu-se a opção documentada no próprio plano ('usar fixture sintética') para prosseguir com Tasks 2 e 3"
  - "Mitigação T-05-41 (entradas ZIP com caminho absoluto ou '..') implementada em render_docx_template, compartilhada por tr e dvi"
metrics:
  duration: "~35min"
  completed: "2026-08-26"
---

# Phase 5 Plan 12: Saída DVI em DOCX (`sysdoc create dvi`) Summary

Novo tipo `dvi` no comando `sysdoc create`, preenchendo um template `.docx` de `referencias/` com os itens consolidados e os pareceres do JSON, 100% offline, no padrão de nomes `xx_projeto_dvi_data.docx`.

## What Was Built

- `create()` em `sysdoc.py` ganhou um ramo `tipo == "dvi"`: seleciona o template via `_select_reference_template(paths, "dvi", "", template_arg)`, monta `values` com `flatten_json(data)` e acrescenta as chaves derivadas `tabela_itens`, `total_itens`, `total_bloqueantes`, `total_pendentes`, `tipo`, `json` e `template`.
- `build_tabela_itens(itens)`: gera um bloco de texto com uma linha por item, no formato `ID — documento/seção — classificação (severidade, risco): parecer`. O valor bruto entra no dicionário `values`; o escape de `&`/`<`/`>` continua acontecendo uma única vez, dentro de `render_docx_template` (mesma técnica já usada para `corpo_etp` no tipo `tr` — sem escape duplo).
- Mensagem de erro específica quando não há template DVI em `referencias/` (nem `--template`): cita explicitamente `dvi.docx` (e as variantes aceitas `modelo_dvi.docx`, `template_dvi.docx`) e a pasta `referencias/`.
- Help do subcomando `create` e o `epilog` do parser passam a citar os tipos aceitos (`tr`, `dvi`) e um exemplo `create Combustivel dvi`.
- Mitigação de segurança (T-05-41, threat_model do plano): `render_docx_template` ganhou `_assert_safe_zip_entries`, que recusa (via `SystemExit`) qualquer template `.docx` cujo `infolist` contenha entrada com caminho absoluto ou segmento `..`, antes de reescrever o ZIP. Aplica-se a `tr` e `dvi` igualmente, pois ambos compartilham `render_docx_template`.
- Suíte `tests/test_dvi_create.py` (10 testes) cobre: geração bem-sucedida; nome no padrão `^\d{2}_[a-z0-9-]+_dvi_\d{4}-\d{2}-\d{2}\.docx$`; presença dos pareceres (`parecer_executivo`, `secao_etp.parecer_documento`, `secao_tr.parecer_documento`) e da `tabela_itens` no XML; escape de `&`/`<`/`>`; segunda geração produzindo prefixo `02_`; erro instrutivo quando não há template; respeito ao `--template` explícito; seleção por variantes de nome (`modelo_dvi.docx`); ausência de alteração no JSON de entrada (comparação de hash SHA-256 antes/depois); e rejeição de template com ZIP malicioso (`..` em entrada).
- Nenhum teste depende do template institucional real — todos usam um `.docx` sintético mínimo montado com `zipfile`.

## Task 1 — Template institucional do DVI (checkpoint)

Não existe nenhum arquivo `.docx` institucional do DVI no repositório: buscas por `*dvi*.docx`, por pastas `referencias/`/`Referencias/`/`modelos/`/`Modelos/`/`templates/` em toda a árvore (excluindo `.git`) não encontraram nenhum template real, apenas o placeholder `templates/projeto-padrao/modelos/COLOQUE_MODELOS_AQUI.txt`. Não havia interação humana disponível durante a execução (worktree paralelo em modo automático).

Seguindo a opção que o próprio plano autoriza no `resume-signal` da Task 1 ("usar fixture sintética"), a execução prosseguiu apenas com os testes automatizados usando um DOCX sintético gerado pela suíte — nenhum conteúdo institucional (marca, timbre, texto jurídico) foi inventado.

**Ação pendente para uso em produção:** antes de rodar `sysdoc create dvi` em um projeto real, é necessário colocar o modelo institucional do DVI em `referencias/dvi.docx` (ou `modelo_dvi.docx`/`template_dvi.docx`) com os placeholders `{{campo}}` — no mínimo `{{projeto.órgão}}`, `{{projeto.processo}}`, `{{projeto.objeto}}`, `{{parecer_executivo}}`, `{{secao_etp.parecer_documento}}`, `{{secao_tr.parecer_documento}}` e `{{tabela_itens}}`. Sem esse arquivo, o comando falha com a mensagem instrutiva implementada na Task 2 (coberta por `test_create_dvi_missing_template_fails_with_instructions`).

## Verification

```
python -m pytest tests/test_dvi_create.py -q   # 10 passed
python -m pytest tests/ -q                     # 267 passed
grep -c "tabela_itens" sysdoc.py                # 2
python sysdoc.py create --help                  # menciona "dvi"
```

Padrão de nome do artefato gerado (teste manual dentro da suíte): `01_projetodvi_dvi_2026-08-26.docx`, casando com `^\d{2}_[a-z0-9-]+_dvi_\d{4}-\d{2}-\d{2}\.docx$`. `word/document.xml` do DOCX gerado contém o texto de `parecer_executivo`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Validação de entradas ZIP do template DOCX**
- **Found during:** Task 2 (leitura do `threat_model` do plano)
- **Issue:** `render_docx_template` reescrevia qualquer entrada do ZIP de origem sem validar `item.filename`, deixando aberta a mitigação T-05-41 (`disposition: mitigate`) do próprio plano — template `.docx` malicioso com caminho absoluto ou `..` no ZIP.
- **Fix:** adicionada `_assert_safe_zip_entries()`, chamada no início de `render_docx_template`, que recusa (via `SystemExit`) entradas com caminho absoluto ou segmento `..`.
- **Files modified:** `sysdoc.py`
- **Commit:** `ab49874`
- **Teste adicionado:** `test_create_dvi_rejects_template_with_zip_path_traversal` em `tests/test_dvi_create.py`

### Notas sobre o critério de aceite de ausência de LLM

O critério de aceite `grep -c "import requests\|openai\|anthropic" sysdoc.py` == 0 (Task 2) não é satisfeito literalmente: `grep -c` retorna `1`, casando com a string pré-existente `DEFAULT_LLM_MODEL = "openai/gpt-4o-mini"` (linha 38, usada pelos comandos `analyze`/`connect`/`models`, documentados em `CLAUDE.md` como responsáveis por rotear a análise a provedores de LLM). Essa linha já existia antes desta execução e não pertence ao código do tipo `dvi`/`create` — não há nenhum `import requests`, `import openai` ou `import anthropic` real no arquivo (`grep -n "^import\|^from" sysdoc.py | grep -i "requests\|openai\|anthropic"` não retorna nada), e o ramo `dvi` adicionado não faz nenhuma chamada de rede ou LLM. Documentado aqui como divergência do critério literal, não como regressão desta plan.

## Self-Check: PASSED

- FOUND: tests/test_dvi_create.py
- FOUND: sysdoc.py
- FOUND: CHANGELOG.md
- FOUND commit: ab49874 (feat(05-12): add dvi type to sysdoc create)
- FOUND commit: abbe17c (test(05-12): cover sysdoc create dvi with synthetic fixtures)
