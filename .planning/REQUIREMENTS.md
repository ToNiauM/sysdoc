# Requirements: SysDoc GSD-Style System

**Defined:** 2026-05-07
**Core Value:** CLI offline para análise de documentos de licitação via agentes de IA

## v1 Requirements

### CLI Interface

- [x] **SYSD-01**: CLI aceita /sysdoc prefix (compatibilidade com agentes)
- [x] **SYSD-02**: Estrutura .sysdoc/config.yaml por projeto
- [x] **SYSD-03**: Help contextual para cada comando

### Document Generation

- [ ] **SYSD-04**: Gerador de Word (python-docx) a partir de template
- [ ] **SYSD-05**: Comando `sysdoc create` no CLI

### Integration

- [ ] **SYSD-06**: SKILL.md atualizado para invocation
- [ ] **SYSD-07**: AGENTS.md com formato de comandos

## v2 Requirements

### Additional Formats

- **SYSD-08**: Suporte a PDF na saída create
- **SYSD-09**: Saída Markdown para integração com outros agentes
- **SYSD-10**: Template de documento Word configurável por projeto

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
| SYSD-04 | Phase 2 | Pending |
| SYSD-05 | Phase 2 | Pending |
| SYSD-06 | Phase 3 | Pending |
| SYSD-07 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0 ✓

---

*Requirements defined: 2026-05-07*
*Last updated: 2026-05-07 after initialization*