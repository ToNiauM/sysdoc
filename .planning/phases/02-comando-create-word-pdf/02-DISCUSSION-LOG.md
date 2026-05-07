# Phase 2 Discussion Log

**Phase:** 2 — Comando Create (Word/PDF)
**Date:** 2026-05-07
**Mode:** discuss (default, single-area)

## Areas Selected by User

- ✅ Escopo de tipos no MVP

## Areas NOT Selected (deferred to planning recommendations)

- ☐ Localização e mutabilidade do template
- ☐ Engine de templating Word
- ☐ Mapeamento de dados JSON→docx (parcialmente decidido pelo escopo)

## Discussion: Escopo de tipos no MVP

### Q1: Que documento(s) o `sysdoc create` gera na primeira iteração (MVP)?

**Options:**
- Apenas TR (.docx) ✅
- TR + Parecer Jurídico (.docx)
- TR (.docx) + TR (.pdf)
- TR + Parecer + PDF de ambos

**Selected:** Apenas TR (.docx)

**Notes:** Foco mínimo. Parecer e PDF ficam como deferred ideas para phases futuras.

### Q2: O TR gerado serve como produto final ou como base para edição humana?

**Options:**
- Base para edição humana ✅
- Documento final pronto
- Rascunho lado a lado

**Selected:** Base para edição humana

**Notes:** O servidor abre no Word, ajusta numeração, formatação e SEI. SysDoc preenche o esqueleto + cláusulas revisadas.

### Q3: Que conteúdo preenche o TR.docx gerado?

**Options:**
- JSON consolidado + ETP literal ✅
- Apenas JSON consolidado
- JSON + TR original literal

**Selected:** JSON consolidado + ETP literal

**Notes:** Cabeçalho do TR vem do JSON (objeto, processo, valor); corpo principal é reaproveitado do `ETP.txt` extraído; cláusulas problemáticas são substituídas pelo campo `para` da análise.

## Deferred Ideas (capturadas em CONTEXT.md "Deferred Ideas")

- Parecer Jurídico (.docx)
- PDF (a partir do .docx via LibreOffice headless ou docx2pdf)
- Modo "documento final pronto"
- Modo "rascunho lado a lado"
- Template customizável por projeto
- Geração de TR partindo do TR.pdf existente

## Open Decisions Left for Planning

Não selecionadas pelo usuário; planner deve propor com recomendação:

- **Template location:** templates/ vs por-projeto vs híbrido. Recomendação: templates/ (Opção A).
- **Engine:** docxtpl vs python-docx vs DIY zipfile. Recomendação: pesquisar no `gsd-phase-researcher`.
- **CLI shape:** `sysdoc create [pasta]` vs `sysdoc create [pasta] tr`. Recomendação: Opção A com flag opcional `--tipo`.
- **Output naming:** `tr_[modelo_ia]_[data].docx`. Recomendação: paralelo ao HTML.
- **Cache miss behavior:** rodar `prepare` automaticamente. Recomendação: igual ao `analyze`.
