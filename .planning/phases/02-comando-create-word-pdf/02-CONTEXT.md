# Phase 2 Context: Comando Create (Word/PDF)

**Phase:** 2 — Comando Create (Word/PDF)
**Date:** 2026-05-07
**Mode:** standard

## Domain

Implementar `sysdoc create [pasta]` que gera, de forma offline e determinística, um Termo de Referência em `.docx` a partir de:
- `[pasta]/dados_consolidados.json` (cabeçalho + cláusulas revisadas no campo `para`)
- `[pasta]/.sysdoc/cache/textos/ETP.txt` (corpo principal reaproveitado literalmente)

O documento gerado é uma **base para edição humana** no Word — não pretende ser produto final. O servidor abre, ajusta numeração/formatação/SEI e finaliza.

## Carrying Forward (decisões herdadas)

**De PROJECT.md / CLAUDE.md / SKILL.md:**
- Templates em `templates/` são imutáveis durante uma análise.
- Saída é versionada com `[modelo_ia]_[data]` no nome do arquivo (padrão do HTML).
- CLI determinística — `create` não chama LLM. Todo conteúdo "novo" vem do JSON ou do ETP literal.
- Comando segue padrão argparse com subparser (igual `prepare`, `analyze`, `render`, etc.).
- Pode invocar via `/sysdoc create` em harnesses de IA ou `sysdoc create` direto na CLI.

**De Phase 1 (sysdoc.py atual):**
- `extract_docx()` já lê `.docx` via `zipfile` + `ElementTree.fromstring` — referência viável para implementação DIY sem dependências.
- `prepare()` produz `[pasta]/.sysdoc/cache/textos/ETP.txt`. `create` deve assumir que esse arquivo existe (e rodar `prepare` se faltar, igual ao `analyze`).
- `slug()`, `extract_date()` e o padrão `resolve_next_json_archive()` já tratam naming versionado.
- `dataclass ProjectPaths` é o ponto único onde caminhos são resolvidos.

## Decisions Captured

### Escopo de tipos no MVP

**Decidido:**
- **Apenas TR (`.docx`)** na primeira iteração. Sem Parecer separado, sem PDF.
- O `.docx` é **base para edição humana**: esqueleto preenchido com dados + cláusulas revisadas; o servidor finaliza no Word.
- **Fonte do conteúdo:** cabeçalho do JSON consolidado (objeto, processo, valor, metadados) + corpo principal do **ETP literal** (de `.sysdoc/cache/textos/ETP.txt`) + cláusulas problemáticas substituídas pelo campo `para` dos itens da análise.

**Implicações para planning:**
- O gerador precisa carregar **dois inputs** simultaneamente: `dados_consolidados.json` e `ETP.txt`.
- Para cada item de `dados_consolidados.itens` com `documento == "ETP"` e `classificação ∈ {ajuste_necessário, risco}`, localizar o `de` no ETP.txt e substituir pelo `para`. Se `de` não for encontrado, registrar como pendente (sem inventar).
- O cabeçalho do `.docx` consome `projeto.objeto`, `projeto.processo`, `projeto.valor_estimado`, `projeto.órgão`, `data_análise`, `modelo_ia`.
- Itens com `documento == "TR"` ficam fora do .docx gerado (não há TR original como base ainda — esse é Phase futura).

## Open Decisions for Planning

Áreas que o usuário **não selecionou para discutir**. O planner/researcher devem propor abordagem e voltar ao usuário se houver tradeoff relevante:

### Localização e mutabilidade do template

- **Opção A:** template fixo em `templates/tr_template.docx`, imutável como o HTML.
- **Opção B:** customizável por projeto em `[pasta]/.sysdoc/template.docx`.
- **Opção C:** híbrido (default em `templates/`, override opcional em `[pasta]/`).
- **Recomendação inicial do planner:** começar com Opção A (consistência com a regra de imutabilidade já estabelecida); abrir Opção C como Phase 2 follow-up se a demanda aparecer.

### Engine de templating Word

- **`docxtpl`** (Jinja2 sobre docx) — padrão da indústria, suporta loops/condicionais, dependência nova.
- **`python-docx` puro** — substituição manual run-by-run; sem placeholders dinâmicos avançados.
- **DIY** com `zipfile` + `ElementTree` — zero dependência (paralelo ao `extract_docx()` atual), mas exige escrever a lógica de substituição.
- **Recomendação inicial do planner:** comparar `docxtpl` vs DIY no `gsd-phase-researcher`. Critério: complexidade do template requerido pelo TR (loops para iterar itens? condicionais por classificação?) define se vale a dependência nova.

### Mapeamento detalhado JSON→template

- **Decidido:** cabeçalho do JSON + corpo do ETP literal + `para` substituindo `de` em cláusulas problemáticas.
- **A definir no planning:** estrutura exata do template (placeholders por campo, formatação dos itens, como representar o `parecer` para o servidor visualizar enquanto edita).

### Forma de invocação CLI

- **Opção A:** `sysdoc create [pasta]` (TR é default; argumento opcional `--tipo`).
- **Opção B:** `sysdoc create [pasta] tr` (subarg posicional para tipo).
- **Opção C:** `sysdoc create-tr [pasta]` (subcommand separado).
- **Recomendação inicial do planner:** Opção A — consistente com `prepare`, `analyze`, `validate`, etc. (um arg posicional só); flag `--tipo` permite expandir para `parecer`/`pdf` em phases futuras sem quebrar compat.

### Comportamento se cache do ETP ausente

- **Recomendação inicial do planner:** rodar `prepare` automaticamente (mesmo padrão do `analyze`).

### Naming da saída

- **Recomendação inicial do planner:** `tr_[modelo_ia]_[data].docx` na raiz do projeto (paralelo ao `analise_[modelo_ia]_[data].html`); auto-incremento `_2`, `_3` se já existir igual ao `resolve_next_json_archive()`.

## Code Context (reusable assets)

- **`sysdoc.py:extract_docx()`** (linhas ~150-168) — pattern para leitura de `.docx` via `zipfile`/`ElementTree`. Direção inversa (leitura → escrita) requer ajuste, mas o esqueleto namespace `w:` é o mesmo.
- **`sysdoc.py:project_paths()`** — adicionar `tr_template`/`output_docx` ao `ProjectPaths` se relevante.
- **`sysdoc.py:slug()` e `sysdoc.py:extract_date()`** — usar diretamente para naming.
- **`sysdoc.py:resolve_next_json_archive()`** — padrão de auto-incremento `_2`, `_3` quando arquivo já existe.
- **`sysdoc.py:build_parser()`** (linha ~592) — onde adicionar o subparser `create`.
- **`sysdoc.py:main()`** — onde adicionar o handler `if args.command == "create": ...`.
- **`templates/render_analise.py`** — referência do estilo "renderizador determinístico" (não copiar lógica, mas seguir o padrão).

## Canonical Refs

Downstream agents (researcher, planner, executor) **devem** ler estes arquivos:

- `skills/sysdoc/SKILL.md` — fluxo canônico; já contém placeholder `/sysdoc create [pasta] [tipo]`.
- `AGENTS.md` — comandos e regras-chave para qualquer harness.
- `CLAUDE.md` — regras específicas do Claude Code; lista comandos e regras de imutabilidade.
- `templates/schema_sysdoc.json` — schema canônico do JSON consumido.
- `.planning/ROADMAP.md` — Goal/Success Criteria/Requirements de Phase 2 (SYSD-04, SYSD-05).
- `.planning/REQUIREMENTS.md` — definições SYSD-04 (gerador Word baseado em template) e SYSD-05 (comando create no CLI).
- `tests/test_validate.py` e `tests/test_cli.py` — padrão de testes a seguir.
- `sysdoc.py` — pontos de extensão (build_parser, main, ProjectPaths).

## Deferred Ideas (não entram em Phase 2)

- **Parecer Jurídico (.docx)** — documento separado consolidando os achados. Candidato a Phase 2.5 ou 3.
- **PDF a partir do .docx** — via LibreOffice headless ou `docx2pdf`. Phase futura.
- **Modo "documento final pronto"** — template fiel a um padrão oficial sem retrabalho. Exige mais especificação do órgão.
- **Modo "rascunho lado a lado"** — visualização de+para por cláusula. Útil mas escopo diferente.
- **Template customizável por projeto** — `[pasta]/.sysdoc/template.docx`. Reabrir se a Opção A da template location se mostrar limitada.
- **Geração de TR partindo do TR.pdf** — quando o objetivo for revisar/atualizar um TR existente em vez de criar um novo a partir do ETP.
- **Saída Markdown** (SYSD-09 v2) — fora do escopo Phase 2.
- **Template Word configurável por projeto** (SYSD-10 v2) — fora do escopo Phase 2.

## Acceptance Criteria (de ROADMAP.md)

1. Gera arquivo `.docx` a partir de template.
2. Preenche campos de `dados_consolidados.json`.
3. Funciona offline/sem LLM.

**Refinamento desta discussão:**
1. Gera `tr_[modelo_ia]_[data].docx` (ou padrão equivalente decidido no planning) a partir de template em `templates/`.
2. Preenche cabeçalho a partir de `dados_consolidados.json` e corpo a partir de `ETP.txt` literal, com cláusulas problemáticas substituídas pelo `para` dos itens.
3. Sem chamadas LLM; rodável offline; falha clara se inputs faltam (ETP.txt, JSON ou template).

## Next

Rode `/clear` e em seguida:

```
/gsd-plan-phase 2
```

O planner vai:
1. Resolver as Open Decisions acima (template location, engine, CLI shape, naming) consultando o codebase e propondo recomendação.
2. Detalhar a estrutura do template `tr_template.docx`.
3. Listar tasks atômicas com testes correspondentes.
