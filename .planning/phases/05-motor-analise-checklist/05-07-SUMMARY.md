---
phase: 05-motor-analise-checklist
plan: 07
subsystem: motor-dvi
tags: [mapeamento-de-pecas, manifest, ancoras, rf3]
dependency-graph:
  requires: ["05-01", "05-02"]
  provides: ["sysdoc_dvi.pecas.mapear_pecas", "sysdoc.detectar_ancoras", "manifest.ancoras"]
  affects: ["sysdoc.py", "sysdoc_dvi/pecas.py"]
tech-stack:
  added: []
  patterns:
    - "Detecção por âncoras textuais normalizadas (sem acento/caixa) com contagem por peça"
    - "Override de config vence detecção automática; detecção vence fallback por nome de arquivo"
    - "Erro com remédio embutido na mensagem (padrão do repositório)"
key-files:
  created:
    - sysdoc_dvi/pecas.py
    - tests/test_dvi_pecas.py
  modified:
    - sysdoc.py
decisions:
  - "peca_sugerida por documento só resolve quando o vencedor supera estritamente o segundo colocado; empate devolve None"
  - "Ambiguidade entre dois arquivos disputando a mesma peça usa a mesma regra (score estritamente maior) e aborta citando os candidatos"
  - "Overrides do .sysdoc/config.yaml e overrides passados por parâmetro são casados apenas contra entradas já existentes no manifest — nunca usados diretamente como caminho de arquivo"
metrics:
  duration_minutes: 25
  completed: "2026-08-26"
---

# Phase 5 Plan 07: Mapeamento de Peças (RF3) Summary

Motor de âncoras textuais no manifest + `sysdoc_dvi.pecas.mapear_pecas` com override manual e abort explícito, mitigando o risco nº 1 do PRD (análise no contexto errado).

## What Was Built

1. **`sysdoc.py`** — constante `PECA_ANCORAS` (ETP, TR, MCP, RISCOS, PROCESSO), `detectar_ancoras(texto)` (contagem normalizada sem acento/caixa por peça) e `peca_sugerida(ancoras)` (vencedor só quando supera estritamente o segundo colocado). `write_extracted_text` passou a gravar `ancoras` e `peca_sugerida` em cada entrada de `manifest["files"]`, sem alterar as chaves existentes (`label`, `category`, `source`, `cache`, `sha256`, `chars`, `words`).

2. **`sysdoc_dvi/pecas.py`** (novo) — `PecaMapeada` (dataclass frozen), `ErroMapeamentoPeca` e `mapear_pecas(projeto, exigidas, overrides=None)`. Ordem de resolução por peça: override (`.sysdoc/config.yaml` chave `pecas`, mesclado com overrides passados por parâmetro) → âncora vencedora (`peca_sugerida` da entrada, com desempate estrito) → fallback pelo nome do arquivo (stem ou label igual à peça) → abort (`ErroMapeamentoPeca`) se a peça é exigida e nenhum candidato foi encontrado. Peças não exigidas e não localizadas são omitidas silenciosamente. O caminho do `.txt` é resolvido a partir do campo `cache` do manifest e recusado se cair fora de `projeto/.sysdoc/cache/` (mitigação T-05-21). Apenas entradas com `category == "documentos"` são consideradas.

3. **`tests/test_dvi_pecas.py`** (novo) — 20 testes em cinco classes: `TestAncoras` (contagem por peça para textos sintéticos de ETP/TR/MCP/Mapa de Riscos + empate + texto vazio), `TestManifest` (prepare grava `ancoras`/`peca_sugerida` sem quebrar chaves legadas), `TestMapeamento` (âncora vencedora, fallback por nome, ambiguidade, filtro por `category`, path traversal recusado), `TestOverride` (override por parâmetro, override via config.yaml, override inválido) e `TestAbort` (peça exigida ausente com remédio `pecas:` na mensagem, manifest ausente, nunca mapeamento parcial silencioso). Nenhum teste depende de PDF real ou de rede.

## Verification

```
python -m pytest tests/ -q          → 136 passed
python -m pytest tests/test_dvi_pecas.py -q → 20 passed
grep -c "PECA_ANCORAS" sysdoc.py    → 2
grep -c "def detectar_ancoras" sysdoc.py → 1
grep -c "class ErroMapeamentoPeca" sysdoc_dvi/pecas.py → 1
```

`sysdoc.prepare` de um projeto sintético grava `ancoras`/`peca_sugerida` no manifest sem alterar as chaves anteriores (verificado manualmente e via `TestManifest`).

## TDD Gate Compliance

Task 2 (`tdd="true"`) seguiu o ciclo completo:
- RED: `70004bc test(05-07): cobre mapear_pecas antes da implementação (RED)` — coleção falhava com `ModuleNotFoundError` antes da implementação.
- GREEN: `e170ae0 feat(05-07): implementar mapear_pecas com override e abort explícito` — os 7 testes RED passaram sem alterar os testes.
- Sem REFACTOR separado (implementação já limpa na primeira passada).

Task 3 expandiu a suíte RED/GREEN original de 7 para 20 testes, cobrindo as classes descritas no plano (`test(05-07): suíte completa de test_dvi_pecas`).

## Deviations from Plan

None - plan executado conforme escrito.

**Nota sobre o worktree:** este agente foi inicialmente spawnado com o worktree apontando para um commit-base desatualizado (fase 5 antiga "Templates TR a partir dos modelos Lei 14.133", sem o diretório `05-motor-analise-checklist`). O passo obrigatório de verificação de branch (`worktree_branch_check`) identificou a divergência e corrigiu via `git reset --hard` para o commit-base correto (`f9d608770e0624db4c8fd2249b2e050f2351b4d7`) antes de qualquer edição — nenhum commit foi perdido, pois o branch do worktree ainda não tinha trabalho próprio.

**Nota sobre verificação de rede:** a verificação do plano (`grep -rn "openai\|anthropic\|requests" sysdoc.py` vazio) encontra um hit pré-existente (`DEFAULT_LLM_MODEL = "openai/gpt-4o-mini"`, linha 38), que já existia antes deste plano e é apenas um nome de modelo em string, não uma chamada de rede real (`sysdoc.py` continua sem `import requests`, `import openai` ou `import anthropic` — confirmado pelo acceptance criteria da Task 1, que verifica exatamente essas importações). Fora do escopo desta execução; não alterado.

## Threat Flags

None — os três itens do `<threat_model>` do plano (T-05-21, T-05-22, T-05-23) foram todos mitigados na implementação: override resolvido apenas contra entradas do manifest com recusa de caminho fora de `.sysdoc/cache/` (T-05-21); vencedor por âncora precisa superar estritamente o segundo colocado, com abort em empate (T-05-22); `PecaMapeada` guarda `label`, `caminho`, `origem` e `score` para rastreabilidade (T-05-23). Nenhuma superfície nova fora do threat model foi introduzida.

## Self-Check: PASSED

- FOUND: sysdoc_dvi/pecas.py
- FOUND: tests/test_dvi_pecas.py
- FOUND commit 543a45c (feat: âncoras no manifest)
- FOUND commit 70004bc (test: RED)
- FOUND commit e170ae0 (feat: GREEN mapear_pecas)
- FOUND commit 813045d (test: suíte completa)
