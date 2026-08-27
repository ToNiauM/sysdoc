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
- [x] **SYSD-18**: `sysdoc create <pasta> dvi` monta o despacho a partir de `dados_consolidados.json` + `.sysdoc/config.yaml` (bloco `despacho:`) + templates de `templates/dvi/` — Planos 06-03/06-04/06-05.

**Nota:** os demais requisitos de Phase 6 (TR/ETP, rodadas seguintes) ainda não foram numerados; entram nesta seção conforme cada rodada for planejada.

### Referência cruzada — pendentes de numeração formal (ver ROADMAP)

Os itens abaixo existem hoje apenas no `ROADMAP.md` (Rodada 2 — Templates TR, ainda pendente de execução). Registrados aqui só para fechar a lacuna de numeração apontada pela nota de sincronia; escopo não é reaberto nesta fase (D-20).

- [ ] **SYSD-11**: (reservado no ROADMAP para a Rodada 2 de Phase 6; não detalhado até o momento do planejamento daquela rodada) — Pending
- [ ] **SYSD-12**: (reservado no ROADMAP para a Rodada 2 de Phase 6; não detalhado até o momento do planejamento daquela rodada) — Pending
- [ ] **SYSD-13**: Derivar e anotar os templates DOCX de TR em `templates/tr/` com placeholders SysDoc — Pending
- [ ] **SYSD-14**: Atualizar `_select_reference_template` para preferir `templates/tr/` antes de `referencias/` com fallback documentado — Pending
- [ ] **SYSD-15**: Testes E2E cobrindo cada categoria, ausência de placeholders não substituídos e fallback para `referencias/` — Pending

## v4 Requirements (Phase 7 — Interface web para pregoeiros)

### Interface web para pregoeiros

- [x] **SYSD-19**: Funções de `sysdoc`/`sysdoc_dvi` chamáveis como biblioteca, com a CLI preservada.
- [x] **SYSD-20**: Pacote Django `sysdoc_web` como extra opcional `web`, sem entrar na instalação base.
- [x] **SYSD-21**: Autenticação obrigatória sem auto-cadastro, com chaves de API só no servidor.
- [x] **SYSD-22**: Processo e análise persistidos no banco, com estado honesto após reinício.
- [x] **SYSD-23**: Fila single-worker, uma análise por vez, sem broker externo.
- [x] **SYSD-24**: `docker compose up` sobe a aplicação inteira, sem passo manual de migração.
- [x] **SYSD-25**: Upload validado com PDF único do processo como caminho principal e escolha de aplicabilidade em linguagem de processo.
- [x] **SYSD-26**: Progresso em tempo real por polling, com falha traduzida para o pregoeiro.
- [x] **SYSD-27**: Revisão humana bloqueante antes do despacho e campos institucionais gravados no `config.yaml` do projeto.
- [x] **SYSD-28**: Downloads do HTML da análise e do DOCX do despacho, sem expor o `dados_consolidados.json`.
- [x] **SYSD-29**: Documentação de produto atualizada, com o contrato das skills inalterado.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-LLM simultânea | Uma LLM por análise |
| Cloud storage | Local-only |

A interface web foi promovida a requisito ativo na Phase 7 (SYSD-19..SYSD-29). A CLI continua sendo o caminho canônico para agentes de IA.

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
| SYSD-11 | Phase 6 (rodada 2, não planejada) | Pending |
| SYSD-12 | Phase 6 (rodada 2, não planejada) | Pending |
| SYSD-13 | Phase 6 (rodada 2, não planejada) | Pending |
| SYSD-14 | Phase 6 (rodada 2, não planejada) | Pending |
| SYSD-15 | Phase 6 (rodada 2, não planejada) | Pending |
| SYSD-16 | Phase 6 (06-01) | ✅ Complete |
| SYSD-17 | Phase 6 (06-02) | Complete |
| SYSD-18 | Phase 6 (06-03/06-04/06-05) | Complete |
| SYSD-19 | Phase 7 (07-01) | ✅ Complete |
| SYSD-20 | Phase 7 (07-02) | ✅ Complete |
| SYSD-21 | Phase 7 (07-02) | ✅ Complete |
| SYSD-22 | Phase 7 (07-03) | ✅ Complete |
| SYSD-23 | Phase 7 (07-03) | ✅ Complete |
| SYSD-24 | Phase 7 (07-04) | ✅ Complete |
| SYSD-25 | Phase 7 (07-05) | ✅ Complete |
| SYSD-26 | Phase 7 (07-06) | ✅ Complete |
| SYSD-27 | Phase 7 (07-07) | ✅ Complete |
| SYSD-28 | Phase 7 (07-07) | ✅ Complete |
| SYSD-29 | Phase 7 (07-08) | ✅ Complete |

**Coverage:**
- v1 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0 ✓
- v3 (Phase 6, rodada 1): SYSD-16/17/18 concluídos; SYSD-11 a SYSD-15 (rodada 2) referenciados pelo ROADMAP, ainda `Pending`
- v4 (Phase 7): SYSD-19 a SYSD-29 concluídos — interface web para pregoeiros entregue

---

*Requirements defined: 2026-05-07*
*Last updated: 2026-08-27 after Phase 7 completion*
