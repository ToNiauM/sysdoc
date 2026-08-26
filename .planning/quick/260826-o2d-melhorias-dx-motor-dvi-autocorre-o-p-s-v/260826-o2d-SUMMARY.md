---
phase: quick-260826-o2d
plan: 01
subsystem: dvi-engine
tags: [python, docx, cli, validation, pt-br]

requires:
  - phase: 05-motor-analise-checklist
    provides: sysdoc-dvi run/relatorio/config pipeline, checklists/dvi.yaml, validate_sysdoc.py imutável
provides:
  - Autocorreção determinística de acentuação no passo 8 do pipeline DVI (sysdoc_dvi/autocorrecao.py)
  - Progresso por item impresso no passo 5 do run
  - Template DVI base semeado por `sysdoc init` em referencias/dvi.docx
affects: [sysdoc_dvi, sysdoc-cli, dvi-templates]

tech-stack:
  added: []
  patterns:
    - "Autocorreção de validação: coletar erros estruturados (--json) → parsear padrão conhecido → aplicar correção mínima → revalidar uma única vez, nunca em laço"
    - "Template DOCX mínimo gerado por script determinístico e commitado como binário, com ZipInfo.date_time fixo para regeração byte-estável"

key-files:
  created:
    - sysdoc_dvi/autocorrecao.py
    - templates/build_dvi_base.py
    - templates/dvi_base.docx
    - tests/test_dvi_autocorrecao.py
    - tests/test_dvi_progresso.py
    - tests/test_dvi_template_base.py
  modified:
    - sysdoc_dvi/despacho.py
    - sysdoc_dvi/pipeline.py
    - sysdoc.py
    - CHANGELOG.md

key-decisions:
  - "seed_dvi_template é chamado apenas em init_command (não dentro de ensure_project_structure) para manter a semeadura restrita ao comando sysdoc init e evitar efeitos colaterais em config_command/all_command, que também chamam ensure_project_structure"
  - "RESERVED_TEMPLATE_NAMES é um dict tipo->nomes para permitir extensão futura a outros tipos reservados sem mudar a assinatura de _select_reference_template"

requirements-completed: [QUICK-P2, QUICK-P4, QUICK-P6]

duration: ~45min
completed: 2026-08-26
---

# Quick Task 260826-o2d: Melhorias de DX no motor DVI (P2+P4+P6) Summary

**Autocorreção determinística de acentuação no passo 8, progresso por item no passo 5, e template DVI base semeado por `sysdoc init` — três correções nascidas de uma rodada real do motor DVI que morria sem sinal de vida e exigia preparação manual.**

## Performance

- **Duration:** ~45min
- **Started:** 2026-08-26T17:20:00-03:00 (aprox.)
- **Completed:** 2026-08-26T17:40:31-03:00
- **Tasks:** 3/3 completed
- **Files modified:** 9 (3 criados de produção, 3 testes novos, 3 modificados)

## Accomplishments

- Um run do motor DVI que antes morria no passo 8 por `referencia` sem acento agora autocorrige deterministicamente, revalida uma única vez e conclui gerando HTML — sem chamar modelo, sem laço de reparo, sem tocar no campo `de`.
- O passo 5 (execução do checklist, historicamente mudo por até ~10 minutos) agora imprime `   [n/total] ID: classificação` a cada item concluído, com `total` refletindo os itens pendentes do run atual mesmo em retomadas por checkpoint.
- `sysdoc init <pasta>` semeia `referencias/dvi.docx` a partir de um template mínimo gerado deterministicamente (`templates/build_dvi_base.py`), permitindo que `sysdoc create <pasta> dvi` funcione na primeira execução sem preparação manual; templates institucionais existentes nunca são sobrescritos, e `create tr` continua exigindo um template de TR real.

## Task Commits

Each task was committed atomically:

1. **Tarefa 1 (P2): mensagem em norma culta + autocorreção determinística de acentuação no passo 8** - `7774a71` (fix)
2. **Tarefa 2 (P4): progresso por item no passo 5** - `aabed3a` (feat)
3. **Tarefa 3 (P6): template DVI base semeado por sysdoc init** - `aa3bdf2` (feat)

_Todas as tarefas usaram `tdd="true"`: testes e implementação foram desenvolvidos e commitados juntos por tarefa (sem gate RED/GREEN separado exigido pelo plano)._

## Files Created/Modified

- `sysdoc_dvi/autocorrecao.py` - `coletar_erros_validacao`, `parsear_erros_acentuacao`, `aplicar_correcoes_acentuacao`, `autocorrigir_json`; nunca chama modelo, nunca reescreve o campo `de`, correção em passada única
- `sysdoc_dvi/despacho.py` - mensagem de reclassificação por fundamentação fora da base legal corrigida para norma culta
- `sysdoc_dvi/pipeline.py` - passo 8 autocorrige e revalida uma vez antes de declarar falha; passo 5 imprime progresso por item; `_gravar_relatorio` aceita `correcoes` e as registra em `avisos`
- `templates/build_dvi_base.py` - gerador determinístico (byte-estável) do template DVI base
- `templates/dvi_base.docx` - template DVI mínimo commitado como binário, 12 placeholders íntegros, sem `{{projeto}}`
- `sysdoc.py` - `RESERVED_TEMPLATE_NAMES`, `seed_dvi_template`, guarda no fallback de `_select_reference_template`, chamada em `init_command`
- `tests/test_dvi_autocorrecao.py`, `tests/test_dvi_progresso.py`, `tests/test_dvi_template_base.py` - 31 testes novos cobrindo os três itens
- `CHANGELOG.md` - entradas em Corrigido (P2) e Adicionado (P4, P6)

## Decisions Made

- `seed_dvi_template` é chamado apenas dentro de `init_command`, não dentro de `ensure_project_structure` (que também é usada por `config_command` e `all_command`), para manter a semeadura de template restrita à semântica de `sysdoc init` descrita no `<behavior>` do plano, evitando side effects em outros comandos que apenas garantem a estrutura de pastas.
- `RESERVED_TEMPLATE_NAMES` foi modelado como `dict[str, set[str]]` (tipo → nomes reservados) em vez de um `set` fixo, para que a guarda no fallback de `_select_reference_template` generalize a outros tipos reservados no futuro sem mudança de assinatura.

## Deviations from Plan

### Auto-fixed Issues

Nenhum desvio classificado nas Regras 1-4 foi necessário — o código seguiu o plano à risca. Um único ajuste de implementação (não uma correção de bug) é registrado abaixo por transparência:

**1. [Ajuste de implementação, não uma regra de desvio] Local da chamada de `seed_dvi_template`**
- **Encontrado durante:** Tarefa 3
- **Contexto:** o plano sugeria chamar `seed_dvi_template` dentro de `ensure_project_structure` (linha 1234) e imprimir a linha de semeadura em `init_command`.
- **Decisão:** a chamada foi feita inteiramente em `init_command`, após `ensure_project_structure` retornar, porque `ProjectPaths` é `@dataclass(frozen=True)` — não há campo para propagar "houve semeadura nesta chamada" de volta para `init_command` se a função de baixo nível fizesse a cópia silenciosamente. Chamar apenas em `init_command` mantém a linha impressa condicionada corretamente ao resultado real da chamada, sem side effects em `config_command`/`all_command` (que também chamam `ensure_project_structure`).
- **Arquivos:** `sysdoc.py`
- **Verificação:** todos os `<behavior>`/`<done>` da Tarefa 3 e as truths do plano relacionadas a `sysdoc init`/`create dvi`/`create tr` passam nos testes (`tests/test_dvi_template_base.py`).
- **Commit:** `aa3bdf2` (parte do commit da tarefa)

---

**Total deviations:** 0 correções pela regra de desvio; 1 ajuste de implementação documentado por transparência.
**Impact on plan:** Nenhum. Todas as truths e artefatos do plano foram entregues exatamente como especificado; a única diferença é onde, dentro do código, a chamada acontece.

## Issues Encountered

- **cwd-drift no ambiente de execução (não relacionado ao código do plano):** no início da execução, um `cd /opt/app/sysdoc` dentro de um comando Bash moveu o shell para o repositório principal (fora do worktree), fazendo uma verificação inicial mostrar conteúdo desatualizado. Identificado e corrigido imediatamente (sentinel de worktree criado, todos os comandos subsequentes usaram caminhos relativos a partir da raiz do worktree). Nenhum arquivo foi escrito fora do worktree.
- `ruff` (linter declarado em `pyproject.toml` como dependência dev) não está instalado neste ambiente de execução; a verificação de lint do plano (item 4 de `<verification>`) foi substituída por uma varredura manual de imports não utilizados via `ast` nos arquivos tocados, sem achados além de imports pré-existentes fora do escopo desta tarefa (`time`, `urllib.error`, `urllib.request` em `sysdoc.py`, já presentes antes desta execução).

## User Setup Required

None - nenhuma configuração de serviço externo é necessária. Nenhuma dependência nova foi adicionada (apenas stdlib: `zipfile`, `shutil`, `subprocess`, `re`, `json`, `itertools`).

## Next Phase Readiness

- O motor DVI agora sobrevive a um erro de acentuação nascido do próprio código sem exigir reexecução manual, dá sinal de vida item a item durante o passo mais longo do run, e `sysdoc create dvi` funciona logo após `sysdoc init`, sem preparação manual de template.
- Nenhum bloqueio identificado. `python3 -m pytest tests/ -q` passa integralmente (426 testes, eram 395 antes desta execução + 31 novos).
- `ruff` não instalado neste ambiente — recomenda-se rodar `python3 -m ruff check sysdoc.py sysdoc_dvi templates/build_dvi_base.py tests` num ambiente com a ferramenta disponível antes de publicar, embora a varredura manual não tenha encontrado problemas nos arquivos tocados.

---
*Phase: quick-260826-o2d*
*Completed: 2026-08-26*

## Self-Check: PASSED

- FOUND: sysdoc_dvi/autocorrecao.py
- FOUND: templates/build_dvi_base.py
- FOUND: templates/dvi_base.docx
- FOUND: tests/test_dvi_autocorrecao.py
- FOUND: tests/test_dvi_progresso.py
- FOUND: tests/test_dvi_template_base.py
- FOUND: commit 7774a71 (fix(dvi): mensagem em norma culta e autocorreção de acentuação no passo 8)
- FOUND: commit aabed3a (feat(dvi): progresso por item no passo 5 do run)
- FOUND: commit aa3bdf2 (feat(cli): sysdoc init semeia template DVI base em referencias/)
