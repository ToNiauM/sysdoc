# Requirements: SysDoc GSD-Style System

**Defined:** 2026-05-07
**Core Value:** CLI offline para análise de documentos de licitação via agentes de IA

## v1 Requirements

### CLI Interface

- [x] **SYSD-01**: CLI aceita /sysdoc prefix (compatibilidade com agentes)
- [x] **SYSD-02**: Estrutura .sysdoc/config.yaml por projeto
- [x] **SYSD-03**: Help contextual para cada comando

### Document Generation

- [x] **SYSD-04**: Gerador de Word a partir de template
- [x] **SYSD-05**: Comando `sysdoc create` no CLI

### Integration

- [ ] **SYSD-06**: SKILL.md atualizado para invocation
- [ ] **SYSD-07**: AGENTS.md com formato de comandos

## v2 Requirements

### Additional Formats

- **SYSD-08**: Suporte a PDF na saída create
- **SYSD-09**: Saída Markdown para integração com outros agentes
- **SYSD-10**: Template de documento Word configurável por projeto

## v3 Requirements (Phase 6 — Templates institucionais)

### Despacho de Verificação Inicial (rodada 1)

- [x] **SYSD-16**: Templates DOCX do Despacho de Verificação Inicial (`templates/dvi/despacho_geral.docx`, `templates/dvi/despacho_tic.docx`), gerados deterministicamente e fiéis ao modelo institucional real.
- [x] **SYSD-17**: Builder do corpo dos apontamentos (XML por peça/alínea, referências cruzadas) — Plano 06-02.
- [ ] **SYSD-18**: `sysdoc create <pasta> dvi` monta o despacho a partir de `dados_consolidados.json` + `.sysdoc/config.yaml` (bloco `despacho:`) + templates de `templates/dvi/` — Planos 06-03/06-04.

**Nota:** os demais requisitos de Phase 6 (TR/ETP, rodadas seguintes) ainda não foram numerados; entram nesta seção conforme cada rodada for planejada.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Interface GUI | Agentes não usam GUI |
| Multi-LLM simultânea | Uma LLM por análise |
| Cloud storage | Local-only |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SYSD-01 | Phase 1 | ✅ Complete |
| SYSD-02 | Phase 1 | ✅ Complete |
| SYSD-03 | Phase 1 | ✅ Complete |
| SYSD-04 | Phase 2 | ✅ Complete |
| SYSD-05 | Phase 2 | ✅ Complete |
| SYSD-06 | Phase 3 | Pending |
| SYSD-07 | Phase 3 | Pending |
| SYSD-16 | Phase 6 (06-01) | ✅ Complete |
| SYSD-17 | Phase 6 (06-02) | Complete |
| SYSD-18 | Phase 6 (06-03/06-04) | Pending |

**Coverage:**
- v1 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0 ✓
- v3 (Phase 6, rodada 1): SYSD-16 concluído; SYSD-17/18 pendentes nesta mesma fase

---

*Requirements defined: 2026-05-07*
*Last updated: 2026-05-07 after initialization*
