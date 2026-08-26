---
phase: 05-motor-analise-checklist
plan: 01
subsystem: motor-dvi
tags: [checklist, tipos, contratos, cli, jinja2, yaml]
dependency-graph:
  requires: []
  provides:
    - sysdoc_dvi package (tipos, checklist, cli, prompts, verificacoes)
    - checklists/dvi.yaml seed checklist
    - sysdoc-dvi console script (skeleton)
  affects:
    - pyproject.toml (version 1.5.0, new deps, new entry point)
tech-stack:
  added: [requests>=2.31, jinja2>=3.1]
  patterns:
    - "Data-driven checklist validated structurally (no silent normalization); ErroChecklist cites item id + field"
    - "AnalysisAgent Protocol as the code-level plug point for future providers"
key-files:
  created:
    - sysdoc_dvi/__init__.py
    - sysdoc_dvi/tipos.py
    - sysdoc_dvi/checklist.py
    - sysdoc_dvi/cli.py
    - sysdoc_dvi/verificacoes/__init__.py
    - sysdoc_dvi/prompts/__init__.py
    - checklists/dvi.yaml
    - tests/test_dvi_checklist.py
  modified:
    - pyproject.toml
decisions:
  - "5 dos 6 itens semente do checklists/dvi.yaml entram com base_legal_texto: pendente e ativo: false porque a transcrição literal do dispositivo não pôde ser conferida sem acesso à fonte; apenas DVI-GER-001 (verificação mecânica sem citação legal específica) entra ativo por padrão"
  - "Task 1 (checkpoint de legitimidade de pacotes) foi auto-aprovada em modo automático, aplicando a política de fallback [ASSUMED] já documentada no próprio plano para requests/jinja2"
metrics:
  duration: "~35min"
  completed: "2026-08-26"
---

# Phase 5 Plan 01: Fundação do motor DVI — pacote, contratos e checklist tipado Summary

Criado o pacote `sysdoc_dvi` (contratos `ItemChecklist`/`ResultadoItem`/`UsoModelo`/`AnalysisAgent`), o carregador data-driven `checklists/dvi.yaml` com validação estrutural estrita, e o esqueleto do console script `sysdoc-dvi`, sem qualquer chamada a LLM na CLI determinística `sysdoc`.

## What Was Built

- **`sysdoc_dvi/tipos.py`** — aliases ASCII (`Aplicabilidade`, `Peca`, `TipoVerificacao`, `ModeloAlvo`, `OrigemVerificacao`), dataclasses `ItemChecklist`, `UsoModelo`, `ResultadoItem` (mantendo os nomes de campo acentuados já existentes no schema: `classificação`, `severidade`... `risco_jurídico`, `seção`), e o `Protocol AnalysisAgent` (`executar_item`, `executar_lote`) — contrato mínimo consumido pelos planos seguintes desta fase.
- **`sysdoc_dvi/checklist.py`** — `carregar_checklist(path)`, `filtrar_itens(itens, aplicabilidade)`, `hash_checklist(path)`, `ErroChecklist`. Validação 100% estrutural: campo obrigatório ausente, valor fora de domínio, id fora do padrão `DVI-(GER|TIC|AMB)-\d{3}` ou id duplicado levantam `ErroChecklist` citando o id do item e o campo — nenhuma normalização silenciosa. `documento_saida` assume ETP para peças ETP/MCP/RISCOS/PROCESSO e TR para peça TR quando omitido; valor explícito só pode ser `ETP`/`TR`.
- **`checklists/dvi.yaml`** — semente com 6 itens (`DVI-AMB-001..004`, `DVI-GER-001`, `DVI-TIC-001`) cobrindo os cinco tipos de verificação (`presenca`, `julgamento`, `calculo`, `vigencia`, `mecanica`) e as três aplicabilidades (`geral`, `tic`, `ambos`). Ver "Decisions Made" sobre por que 5 dos 6 itens nascem `ativo: false`.
- **`sysdoc_dvi/cli.py`** — `build_parser()`/`main()` no mesmo estilo de `sysdoc.py` (reconfigura stdout/stderr utf-8), subcomandos `run` (`project`, `--tipo geral|tic`, `--checklist`, `--economico`, `--forte`, `--resume/--no-resume`), `relatorio` (`project`) e `config` (`--economico`, `--forte`, `--listar`). Handlers imprimem "não implementado" e retornam 2 nesta task; `--version` responde `SysDoc DVI 1.5.0`.
- **`sysdoc_dvi/prompts/__init__.py`** — `montar_prompt(nome, **contexto)` com `jinja2.Environment(loader=FileSystemLoader(sysdoc_dvi/prompts/), autoescape=False, undefined=jinja2.StrictUndefined)`. Nenhum `.jinja` criado ainda.
- **`sysdoc_dvi/verificacoes/__init__.py`** — vazio, reservado para as ondas 2/3.
- **`pyproject.toml`** — `version = "1.5.0"` (D-05); `requests>=2.31` e `jinja2>=3.1` adicionados a `dependencies`; `[project.scripts]` ganhou `sysdoc-dvi = "sysdoc_dvi.cli:main"`; novo bloco `[tool.setuptools]` com `packages = ["sysdoc_dvi"]` e `py-modules = ["sysdoc"]` (necessário porque o setuptools não consegue mais auto-descobrir um único alvo de topo com `sysdoc_dvi/` presente).

## Verification

- `python -m pytest tests/ -q` → **91 passed** (67 preexistentes + 24 novos em `tests/test_dvi_checklist.py`).
- `python -c "import sysdoc_dvi, sysdoc_dvi.cli, sysdoc_dvi.tipos; print(sysdoc_dvi.__version__)"` → `1.5.0`.
- `python -m sysdoc_dvi.cli --version` → `SysDoc DVI 1.5.0` (sem importar `requests`/`anthropic`/`openai`).
- `grep -rn "anthropic\|openai\|requests" sysdoc.py | grep -v "^.*#" | grep -c "import"` → `0` (CLI determinística intacta).
- `python -c "from sysdoc_dvi.checklist import carregar_checklist, filtrar_itens, hash_checklist; m,i=carregar_checklist('checklists/dvi.yaml'); print(len(i), len(filtrar_itens(i,'tic')))"` → `6 0` (0 < 6 — apenas `DVI-GER-001` está ativo, e ele é `aplicabilidade: geral`, então o filtro `tic` retorna 0 conforme esperado).
- `grep -c 'DVI-\(GER\|TIC\|AMB\)-[0-9][0-9][0-9]' checklists/dvi.yaml` → `6`.
- `python sysdoc.py --version` → `SysDoc 1.4.0` (permitido pelo plano; `sysdoc.py` não está em `files_modified` desta task).

## Deviations from Plan

### Auto-fixed / Documented Issues

**1. [Auto-mode checkpoint] Task 1 (checkpoint de legitimidade de pacotes) auto-aprovada**
- **Encontrado em:** Task 1 (`checkpoint:human-verify`, `gate="blocking-human"`).
- **Situação:** O plano já documenta que, como não existe `## Package Legitimacy Audit` em RESEARCH.md nesta fase, `requests` e `jinja2` são tratados como `[ASSUMED]`. O orquestrador instruiu modo automático com aplicação dessa política de fallback documentada em vez de bloquear.
- **Verificação independente feita:** `pip show requests` confirma mantenedor Kenneth Reitz (o mesmo mantenedor histórico do projeto `psf/requests`), versão instalada `2.32.5` (≥ 2.31 exigido); `pip show jinja2` confirma versão instalada `3.1.6` (≥ 3.1 exigido) — projeto Pallets, amplamente conhecido. Nenhum outro pacote novo foi instalado nesta fase.
- **Ação:** Task 2 liberada para declarar as dependências em `pyproject.toml`.

**2. [Rule 4-adjacent / plan bug documented, not fixed in code] Acceptance criterion literal do Task 3 é auto-contraditório**
- **Encontrado em:** Task 3, verificação `grep -v '^#' checklists/dvi.yaml | grep -c 'presença\|julgamento\|cálculo\|vigência\|mecânica' == 0`.
- **Problema:** O padrão inclui a palavra `julgamento`, que não possui variante acentuada em português — é idêntica em ASCII e não-ASCII. Como o plano exige um item real com `tipo: julgamento` (valor ASCII correto, D-06) e como campos de prosa (`pergunta`, `referencia`) legitimamente contêm `cálculo`/`vigência` em português correto (exigido pelo restante do CLAUDE.md: "campos gerados devem estar em norma culta"), este grep nunca pode retornar `0` para um checklist que satisfaça os demais requisitos do próprio plano.
- **Verificação real aplicada (o que a intenção D-06 realmente exige — apenas o campo `tipo:` em ASCII):** `grep -n '^\s*tipo:' checklists/dvi.yaml` mostra as 6 ocorrências, todas com valores ASCII (`presenca`, `julgamento`, `calculo`, `vigencia`, `mecanica`) — nenhuma acentuada. Requisito real satisfeito; apenas o comando de verificação literal do plano está incorreto.
- **Nenhuma alteração de código foi feita** — este é um problema no comando de verificação do plano, não no artefato produzido.

### Nenhuma outra alteração fora do escopo do plano.

## Decisions Made

- **Checklist semente majoritariamente inativo por segurança jurídica:** 5 dos 6 itens de `checklists/dvi.yaml` (`DVI-AMB-001..004`, `DVI-TIC-001`) usam `base_legal_texto: pendente` e `ativo: false` porque este executor não teve como conferir a transcrição literal exata dos dispositivos citados (Lei 14.133/2021, IN SEGES/ME 65/2021, IN SGD/ME 94/2022) sem acesso à fonte primária — exatamente a saída explicitamente prevista na Task 3 do plano ("se a transcrição exata não for conhecida, usar `pendente`... e registrar o item como `ativo: false`"). Apenas `DVI-GER-001` (verificação `mecanica` sem citação legal específica — padrão redacional interno) entra `ativo: true`. Isso é intencional e não é um bug: os testes de `filtrar_itens`/roteamento geral-TIC usam dados sintéticos (`ativo=True`) e cobrem o comportamento integralmente; a semente real do repositório precisa de revisão humana (dono do produto) antes de qualquer item real virar `ativo: true`, o que é responsabilidade de um plano/tarefa futura de curadoria de conteúdo, não desta fundação técnica.
- **`[tool.setuptools]` explícito em `pyproject.toml`:** necessário para evitar erro de auto-descoberta do setuptools (múltiplos possíveis pacotes de topo: `sysdoc.py`, `templates/`, `tests/`, `sysdoc_dvi/`) — conforme já antecipado no `<action>` da Task 2 do plano.

## Known Stubs

- `sysdoc_dvi/cli.py`: os três handlers (`run`, `relatorio`, `config`) imprimem `"não implementado"` e retornam `2`. Isso é o esqueleto intencional desta task — os planos seguintes da fase (ondas 2/3) implementam o pipeline real.
- `sysdoc_dvi/verificacoes/__init__.py`: vazio, reservado para funções puras de `calculo`/`vigencia`/`mecanica` de planos futuros.
- `sysdoc_dvi/prompts/`: nenhum template `.jinja` criado ainda; `montar_prompt` funcional mas sem templates para carregar.
- `checklists/dvi.yaml`: 5 dos 6 itens semente são `ativo: false` (ver "Decisions Made" acima) — não são código morto, mas reduzem a cobertura funcional real do checklist até curadoria humana da base legal.

## Threat Flags

Nenhuma nova superfície de ameaça fora do `<threat_model>` do plano foi introduzida. `T-05-SC` (instalação de `requests`/`jinja2`) foi mitigada conforme registrado acima; `T-05-01` (yaml.safe_load apenas) e `T-05-03` (hash do checklist exposto) estão implementados em `sysdoc_dvi/checklist.py`. `T-05-02` (restringir caminho de `--checklist` a `checklists/` do repositório/projeto) ainda **não** se aplica nesta task — `sysdoc_dvi/cli.py` apenas declara a flag `--checklist`; a resolução/validação do caminho é responsabilidade do plano que implementa o handler `run` de fato (fora do escopo desta task).

## Self-Check: PASSED

- FOUND: sysdoc_dvi/__init__.py
- FOUND: sysdoc_dvi/tipos.py
- FOUND: sysdoc_dvi/checklist.py
- FOUND: sysdoc_dvi/cli.py
- FOUND: sysdoc_dvi/verificacoes/__init__.py
- FOUND: sysdoc_dvi/prompts/__init__.py
- FOUND: checklists/dvi.yaml
- FOUND: tests/test_dvi_checklist.py
- FOUND commit 2ed8a0d (feat: pacote sysdoc_dvi, contratos, entry point)
- FOUND commit 08d4326 (test: RED — testes do checklist DVI)
- FOUND commit 90f86cc (feat: GREEN — checklist.py + checklists/dvi.yaml)

## TDD Gate Compliance

Task 3 (`tdd="true"`): RED confirmado (`ModuleNotFoundError: No module named 'sysdoc_dvi.checklist'` antes da implementação, commit `08d4326`) → GREEN confirmado (24/24 testes passando após implementação, commit `90f86cc`). Nenhum commit `refactor` necessário — implementação não exigiu limpeza adicional após o GREEN.
