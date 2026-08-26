# Phase 5: Motor de análise por checklist com agentes plugáveis - Context

**Gathered:** 2026-08-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Entregar o motor de análise DVI dirigido por checklist tipado (`checklists/dvi.yaml`), executável pelo novo binário `sysdoc-dvi` (orquestrador multi-provedor via API) ou por qualquer harness agêntico, com verificações determinísticas em Python (calculo, vigencia, mecanica), grounding check do campo `de`, síntese dedicada de pareceres, relatório de execução e saída DVI em DOCX via `sysdoc create dvi`. A CLI `sysdoc` permanece 100% determinística — nenhum comando dela chama LLM.

**Requisitos completos (RF1–RF10, RNF1–RNF5, critérios de aceite CA1–CA8):** ver `PRD.md` nesta pasta — funciona como spec travada; não re-decidir o que o PRD fixa.

</domain>

<decisions>
## Implementation Decisions

### Entry point e operação da CLI (resolve D2 do PRD)
- **D-01:** Binários por produto: `sysdoc` mantém todos os comandos atuais, determinísticos; novo executável **`sysdoc-dvi`** concentra o fluxo de análise (`run`, `relatorio`, e um `config` mínimo). Nome `sysdoc-agent` do PRD foi substituído por `sysdoc-dvi`.
- **D-02:** DVI e comparação TR×ETP são dois modos do mesmo motor: nesta fase só o checklist DVI entra no motor; a comparação TR×ETP continua via harness como hoje e vira outro checklist do motor em fase futura (`--checklist comparacao-tr-etp`).
- **D-03:** `sysdoc-dvi run [pasta]` executa o pipeline completo: prepare (se cache ausente) → mapeamento de peças → análise por checklist → validate → render HTML → relatório. `sysdoc create dvi` (DOCX) e `sysdoc deploy` permanecem manuais porque exigem revisão humana antes.
- **D-04:** Falha no meio da execução: checkpoint incremental em `.sysdoc/cache/` com resultados por item; re-rodar `run` retoma pulando itens já resolvidos.

### Versionamento e nomenclatura (resolve D1 e D4 do PRD)
- **D-05:** Versão única do repositório: a entrega sai como **SysDoc 1.5.0**; o rótulo "v0.2.0" é abandonado.
- **D-06:** Valores novos do contrato em ASCII sem acento: tipos `presenca | julgamento | calculo | vigencia | mecanica`; campos `origem_verificacao` (`llm|deterministico|lookup`), `checklist_id`, `checklist_hash`, `schema_version`. Os campos acentuados já existentes do schema (`classificação`, `risco_jurídico`) permanecem intocados.
- **D-07:** Ids de item do checklist com prefixo por escopo: `DVI-GER-001`, `DVI-TIC-001`, `DVI-AMB-001`. Ids estáveis — item desativado não libera o número.
- **D-08:** **Novo padrão de nomes de artefatos: `xx_nome_tipo_data.extensao`**, onde `xx` é o contador de produção daquele artefato no projeto (01 na primeira geração; regerar produz 02, 03... nunca reutilizado), `nome` é o slug da pasta do projeto, `tipo` é o artefato (`analise`, `relatorio`, `dvi`, `tr`, `dados`). Ex.: `01_processo-042_dvi_2026-08-26.docx`. O `modelo_ia` sai do nome de arquivo e vive apenas nos metadados do JSON.
- **D-09:** O padrão de nomes vale para **todos** os artefatos gerados a partir da 1.5.0 (analise HTML, tr DOCX, JSON versionado, dvi, relatorio). Arquivos antigos não são renomeados. Isso implica evolução de `render_analise.py`/publish/create entre versões — permitido, com registro no CHANGELOG (imutabilidade vale só durante uma análise).

### Tabela de vigência (resolve D3 do PRD)
- **D-10:** Tabela global `normas/vigencia.yaml` no repositório + override opcional por projeto em `referencias/vigencia.yaml`; no merge, a entrada do projeto vence.
- **D-11:** A tabela nasce semeada com toda norma citada nos itens do checklist DVI durante a conversão dos prompts, com `conferida_em` da data da curadoria; o dono revisa antes do merge.
- **D-12:** Norma com `conferida_em` há mais de 180 dias gera aviso no relatório de execução (não bloqueia, não vira pendente); limiar configurável.
- **D-13:** Matching de citações: normalizador determinístico (nº/n°/no, "de 2021" vs "/2021", caixa, espaços) + campo `aliases` por entrada da tabela (ex.: "NLLC"). Citação que não casa → "norma não catalogada" → item `pendente` (conforme RF7).

### Checklists e provedores LLM
- **D-14:** Arquivo único `checklists/dvi.yaml` com todos os itens; o campo `aplicabilidade` (geral/tic/ambos) faz o roteamento via `--tipo`/config. Hash do checklist é de um arquivo só. Futuro: `comparacao-tr-etp.yaml` como outro produto.
- **D-15:** **Camada de provedores multi-modelo, reusando o padrão do sysdoc.py**: roteamento OpenRouter/OpenAI/Gemini/Anthropic via `requests`, chaves em `~/.sysdoc/config.json` (`sysdoc connect`). Config mapeia `economico` e `forte` para qualquer `provedor/modelo` (ex.: `openrouter/deepseek-chat`, `openai/gpt-5`, `anthropic/claude-opus-5`); flags `--economico`/`--forte` sobrepõem. Adicionar provedor = um módulo novo. (Substitui a menção do PRD a "SDK Anthropic como implementação de referência" — a implementação de referência é o cliente multi-provedor `requests`.)
- **D-16:** Sem modelos configurados, `sysdoc-dvi run` aborta com mensagem clara de como configurar (`~/.sysdoc/config.json` seção `dvi` ou `sysdoc-dvi config`). Nenhum modelo é escolhido à revelia do usuário.
- **D-17:** JSON estruturado por item: usar `json_schema`/`json_object` quando o provedor suporta; resposta inválida → 1 retry com o erro apontado; persistindo → item vira `pendente` com `falha_estruturada` registrada no relatório (análise nunca aborta por um item).

### Claude's Discretion
- Detalhes do formato do checkpoint de retomada (D-04) e do relatório de execução (nomes de campos internos).
- Estrutura interna do pacote do orquestrador (módulos, protocolo `AnalysisAgent`), respeitando o contrato mínimo do RF8.
- Como `sysdoc-dvi` reusa a CLI como biblioteca (import direto de `sysdoc.py` vs subprocess) — decidir no planning.
- Tolerância numérica default das verificações de `calculo` (RF4) — configurável, escolher default sensato.
- Limiar default da correspondência aproximada do grounding check (RF5) — configurável.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Spec da fase
- `.planning/phases/05-motor-analise-checklist/PRD.md` — Requisitos travados (RF1–RF10, RNF1–RNF5, CA1–CA8, riscos). MUST read antes de planejar. As decisões D-01…D-17 acima resolvem/sobrepõem as "Decisões em aberto" D1–D4 do PRD e o trecho do RF8 sobre SDK Anthropic.

### Contrato de dados e fluxo canônico
- `templates/schema_sysdoc.json` — schema atual; evolui retrocompatível com os campos novos (D-06).
- `templates/validate_sysdoc.py` — validador vigente; o JSON do motor deve passar nele (RNF5); evolução só entre versões com testes.
- `skills/sysdoc/SKILL.md` — fluxo canônico; passa a declarar `checklists/dvi.yaml` como fonte canônica dos itens (RF8).
- `AGENTS.md` e `CLAUDE.md` — regras para harnesses; atualizar para o fluxo por itens.

### Código a estender
- `sysdoc.py` — padrão multi-provedor via `requests` + `~/.sysdoc/config.json` a reusar (D-15); `ProjectPaths`; padrões `slug()`/`extract_date()`/auto-incremento; `build_parser()`/`main()` para `create dvi`; naming novo (D-08/D-09) toca aqui e no renderer.
- `tests/test_cli.py` e `tests/test_validate.py` — padrão de testes a seguir (RNF4).
- `.planning/ROADMAP.md` — goal da fase.

### Insumos de negócio (fora do repo — obter com o dono)
- Os dois prompts DVI monolíticos (processos gerais e TIC) — fonte dos ~50 itens a converter para `checklists/dvi.yaml` (RF1) e das normas para semear `normas/vigencia.yaml` (D-11).
- Template institucional do DVI em DOCX — colocar em `referencias/` para o `sysdoc create dvi` (RF10).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `sysdoc.py` roteamento de provedores (OpenRouter/OpenAI/Gemini/Anthropic) com `requests` e chaves via `sysdoc connect` — base direta da camada de provedores do motor (D-15).
- `sysdoc.py:ProjectPaths` — ponto único de resolução de caminhos; ganha os caminhos de checklist, vigência, relatório e checkpoint.
- Padrões `slug()`, `extract_date()`, auto-incremento de arquivo — base para o contador `xx` do naming novo (D-08).
- `templates/render_analise.py` + `analise_template.html` — renderização permanece; só o nome do arquivo de saída muda (D-09).
- Gerador DOCX da Phase 2 (`sysdoc create`, substituição ZIP/XML de placeholders) — reusar para `create dvi` com template em `referencias/`.
- `jinja2` já é dependência — usar para os templates curtos de prompt (RNF1).
- `pyyaml` já é dependência — checklists e tabela de vigência.

### Established Patterns
- CLI determinística sem LLM (constraint de PROJECT.md) — preservada pela decisão de binário separado (D-01).
- Validação centralizada em `validate_sysdoc.py`; coerência classificação↔risco↔severidade já enforced — os campos novos entram como evolução retrocompatível.
- Saídas versionadas e nunca sobrescritas — reforçado pelo contador de produção `xx` (D-08).
- Testes pytest com `tmp_path` fixtures (test_cli.py) — seguir para o motor.

### Integration Points
- `pyproject.toml`: novo entry point `sysdoc-dvi` (console script) + dependências do motor.
- `sysdoc.py build_parser()/main()`: novo tipo `dvi` no `create`.
- `.sysdoc/config.yaml` do projeto: chave de aplicabilidade (`tipo: geral|tic`) e overrides de peças (`pecas:`), conforme RF2/RF3.
- `~/.sysdoc/config.json`: seção `dvi` com mapeamento `economico`/`forte` → `provedor/modelo` (D-15/D-16).
- `.sysdoc/cache/`: manifest com âncoras de peças (RF3), checkpoint de retomada (D-04).

</code_context>

<specifics>
## Specific Ideas

- Saída do `run` no estilo do handoff atual do `sysdoc analyze`: passos numerados, contagens por tipo de item, custo/duração ao final e instrução do próximo comando (`sysdoc create dvi`).
- Mensagens de erro sempre com o remédio na própria mensagem (ex.: config de modelos ausente mostra o JSON exato a preencher).
- Exemplo canônico de nome de arquivo: `01_processo-042_dvi_2026-08-26.docx`; regeração no dia seguinte → `02_processo-042_dvi_2026-08-27.docx`.

</specifics>

<deferred>
## Deferred Ideas

- Checklist `comparacao-tr-etp.yaml` no motor (`sysdoc-dvi run --checklist ...`) — fase futura; nesta fase a comparação TR×ETP continua via harness.
- Binário `sysdoc-docs` para agrupar geração/comparação de documentos — reavaliar depois que o `sysdoc-dvi` estabilizar.
- Wizard interativo de configuração de modelos (estilo `sysdoc guia`) — alternativa registrada ao abort com mensagem (D-16).
- Verificação de formatação visual sobre o DOCX original — já fora de escopo no PRD (§4).

</deferred>

---

*Phase: 05-motor-analise-checklist*
*Context gathered: 2026-08-26*
