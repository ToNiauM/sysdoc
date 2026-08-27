---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 06
status: ready_to_execute
stopped_at: Completed 06-05-PLAN.md (create dvi ligado ao builder real, por tipo, via canal raw_xml)
last_updated: "2026-08-27T04:30:00.000Z"
progress:
  total_phases: 7
  completed_phases: 2
  total_plans: 24
  completed_plans: 22
  percent: 29
---

# STATE — SysDoc

**Project:** SysDoc - Sistema de Análise de Documentação de Licitação
**Current Phase:** 06
**Mode:** standard

## Project Reference

See: .planning/PROJECT.md

**Core value:** CLI offline para análise de documentos de licitação via agentes de IA.

## Progress

| Phase | Status | Plans | Progress |
|-------|--------|-------|----------|
| 1 | complete | 1/1 | 100% |
| 2 | complete | 1/1 | 100% |
| 3 | pending | 0/1 | 0% |
| 4 | pending | 0/1 | 0% |
| 5 | pending | 0/0 | 0% |
| 6 | in_progress | 5/7 | 71% |

## Recent Changes

- 2026-05-07: Projeto inicializado no GSD.
- 2026-05-07: Codebase mapeado.
- 2026-05-07: Phase 1 concluída — `sysdoc analyze`, `.sysdoc/config.yaml`, AGENTS.md, wrappers Claude Code/OpenCode e testes CLI.
- 2026-05-08: Phase 2 planejada — `02-RESEARCH.md`, `02-PATTERNS.md` e `02-01-PLAN.md`.
- 2026-05-12: Phase 2 concluída — `sysdoc create` gera DOCX determinístico a partir de JSON + templates em `referencias/`, com revisão ETP para `tipo=tr`; 67 testes passando.
- 2026-05-12: Phase adicionada — Templates TR a partir dos 4 modelos Lei 14.133 em `Referencias/`, com placeholders SysDoc anotados.
- 2026-08-26: Merge de branches — "Templates TR (Lei 14.133)" renumerada de Phase 5 para Phase 6; Phase 5 permanece "Motor de análise por checklist" (concluída, release 1.5.0).
- 2026-08-27: Phase 6 planejada (rodada 1: Despacho de Verificação Inicial) — 7 planos em 4 waves, cobrindo SYSD-16/17/18 e D-01 a D-14. Canal raw-XML separado (`render_docx_template(..., raw_xml=)`) adotado em vez de allowlist sobre `values`, eliminando por construção a injeção via chave homônima no `dados_consolidados.json`.
- 2026-08-27: Plano 06-01 concluído — gerador determinístico `templates/build_despacho_templates.py` cria `templates/dvi/despacho_geral.docx` e `templates/dvi/despacho_tic.docx`, moldura fiel a `processo-teste/referencias/dvi.md` com seis estilos nomeados e placeholder raw único `{{corpo_apontamentos_xml}}`; 11 testes novos, suíte completa (480) verde.
- 2026-08-27: Plano 06-02 concluído — `sysdoc_docx/corpo_dvi.py` filtra classificação (D-03), agrupa por peça em ordem canônica (D-05), isola pendências em seção própria ao final (D-04), resolve referência cruzada entre apontamentos equivalentes (D-07) e emite `<w:p>` com estilos nomeados prontos para injeção raw (D-08), sempre com o texto vindo do JSON escapado; 26 testes novos, suíte completa (506) verde.
- 2026-08-27: Plano 06-03 concluído — sigla DVI corrigida de "Documento de Verificação Inicial" para **Despacho de Verificação Inicial** (D-01) em `CLAUDE.md`, `AGENTS.md`, `README.md` (2 ocorrências), `checklists/dvi.yaml`, os três `SKILL.md`, `templates/build_dvi_base.py` (com `templates/dvi_base.docx` regerado) e 2 fixtures de teste; `tests/test_sigla_dvi.py` (4 testes) trava permanentemente a regressão via varredura de `git ls-files`; CHANGELOG registra a correção referenciando a entrada `[1.5.x]` anterior; suíte completa (510) verde.
- 2026-08-27: Plano 06-04 concluído — `render_docx_template(template, output, values, raw_xml=None)` abre canal de XML cru estruturalmente separado de `values` (D-09): `values` é sempre escapado, sem exceção por nome de chave; `RAW_XML_KEYS` permanece como allowlist fechada, mas só é consultada em `_validar_chave_raw`, nunca no corpo da função (travado por teste de introspecção). Campos institucionais do despacho (`vocativo`, `unidade`, `destinatario`, `signatario`, `cargo_signatario`, `autoridade`, `cargo_autoridade`) resolvidos por `valores_despacho()` a partir do novo bloco `despacho:` em `.sysdoc/config.yaml` (semeado por `init_config`), com marcador `[PREENCHER: <campo>]` quando ausente — nunca inventado. 17 testes novos em `tests/test_dvi_render_raw.py` provam a separação de canal isoladamente; suíte completa (532) verde.
- 2026-08-27: Plano 06-05 concluído — `sysdoc create <pasta> dvi` resolve `despacho_geral.docx`/`despacho_tic.docx` pelo `tipo` do `.sysdoc/config.yaml` (D-13), respeitando template customizado do órgão (D-14) via comparação SHA-256 contra as sementes do repo; injeta o corpo real montado por `sysdoc_docx.corpo_dvi` pelo canal `raw_xml`, nunca em `values`; `seed_dvi_template`/`init_command` semeiam a variante correspondente ao `tipo`. 22 testes novos em `tests/test_dvi_create_variante.py` provam precedência, variante, conteúdo filtrado e não-injeção ponta a ponta via `create()`; suíte completa (554) verde.

## Recent Decisions

- Templates de geração DOCX ficam em `referencias/`, não em um template fixo do repositório.
- `sysdoc create` permanece offline e determinístico, usando substituição ZIP/XML de placeholders em DOCX.
- `tipo=tr` é o padrão quando omitido; `--tipo` existe para scripts.
- Para TR, o ETP preparado é lido de `.sysdoc/cache/textos/documentos/ETP.txt`, com fallback legado para `.sysdoc/cache/textos/ETP.txt`.
- `templates/dvi/` é a pasta própria para templates institucionais do despacho, um DOCX por variante de verificação (`despacho_geral.docx`, `despacho_tic.docx`), no molde do gerador determinístico já usado por `templates/build_dvi_base.py`.
- Chave de equivalência de D-07 (referência cruzada) usa apenas `parecer` normalizado, não `parecer+fundamento` — medição contra `processo-teste/dados_consolidados.json` mostrou que o par `ETP-016`/`TR-002` tem `fundamento` que varia pelo nome da peça, mesmo apontando o mesmo achado.
- DVI = Despacho de Verificação Inicial (D-01), confirmado por `processo-teste/referencias/dvi.md` linha 1 e pelo dono do produto; `tests/test_sigla_dvi.py` trava permanentemente contra as duas expansões erradas já vistas no repositório.
- Canal de XML cru é um parâmetro dedicado (`raw_xml`), não uma allowlist sobre nome de chave em `values` — fecha por construção o vetor de chave homônima vinda de `dados_consolidados.json` (revisão do checker sobre D-09).
- Campos institucionais do despacho (vocativo, unidade, destinatário, signatário, autoridade) vêm de `.sysdoc/config.yaml` bloco `despacho:`, nunca do JSON da análise nem inferidos — campo ausente vira `[PREENCHER: <campo>]` visível no Word.
- Precedência de template DVI resolvida por SHA-256 contra as sementes do repo: um `.docx` em `referencias/` byte-idêntico a `templates/dvi/despacho_*.docx` conta como "semente intocada" e cede lugar à variante do `tipo`; só um `.docx` realmente diferente (customizado pelo órgão) vence sem precisar de `tipo`.

## Accumulated Context

### Roadmap Evolution

- Phase 5 added: Motor de análise por checklist com agentes plugáveis (PRD completo em `.planning/phases/05-motor-analise-checklist/PRD.md`)
- Phase 7 added (2026-08-26): Interface web para pregoeiros — fluxo visual de upload → extração → análise → output HTML/DOCX, abstraindo a CLI e o motor DVI

## Pending Todos

- Revisar a pasta não rastreada `Referencias/` antes de qualquer publicação ampla; ela parece conter modelos reais do usuário.

## Blockers/Concerns

- Nenhum bloqueio ativo para continuar o roadmap.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260826-o2d | Melhorias DX motor DVI: autocorreção de acentuação pós-validação (P2), progresso por item no run (P4), template DVI base semeado pelo init (P6) | 2026-08-26 | b376b5f | [260826-o2d-melhorias-dx-motor-dvi-autocorre-o-p-s-v](./quick/260826-o2d-melhorias-dx-motor-dvi-autocorre-o-p-s-v/) |
| 260826-p65 | Motor DVI: fatiador determinístico de peças no prepare (P1), re-ancoragem determinística do campo `de` antes de degradar (P3), preços de modelos configuráveis por alvo (P5) | 2026-08-26 | 8af987b | [260826-p65-motor-dvi-fatiador-deterministico-de-pec](./quick/260826-p65-motor-dvi-fatiador-deterministico-de-pec/) |

## Session Continuity

Last session: 2026-08-27T04:30:00Z
Stopped at: Completed 06-05-PLAN.md (create dvi ligado ao builder real, por tipo, via canal raw_xml)
Resume file: .planning/phases/06-templates-tr-a-partir-dos-modelos-lei-14-133/06-06-PLAN.md

## Current Focus

Phase 3: Integração Agentes IA. Próximo passo recomendado: `$gsd-discuss-phase 3`.

---

*Last updated: 2026-08-27 — Completed 06-05-PLAN.md: create dvi ligado ao builder real, por tipo, via canal raw_xml*
