---
phase: 06-templates-tr-a-partir-dos-modelos-lei-14-133
plan: 01
subsystem: templates
tags: [docx, zipfile, xml.sax.saxutils, despacho-verificacao-inicial, dvi]

requires:
  - phase: 05-motor-de-analise-por-checklist
    provides: "checklists/dvi.yaml, normas/vigencia.yaml (IN SGD/ME 94/2022 como norma da variante TIC)"
provides:
  - "templates/dvi/despacho_geral.docx e templates/dvi/despacho_tic.docx — molduras DOCX do Despacho de Verificação Inicial"
  - "templates/build_despacho_templates.py — gerador determinístico e byte-estável das duas variantes"
  - "Contrato de placeholders fixado: 9 campos institucionais + 1 placeholder raw {{corpo_apontamentos_xml}}"
  - "Estilos nomeados DviTitulo/DviSubtitulo/DviVocativo/DviCorpo/DviPecaTitulo/DviAlinea — DviPecaTitulo e DviAlinea reservados para o builder do Plano 02"
affects: [06-02, 06-03, 06-04]

tech-stack:
  added: []
  patterns:
    - "Gerador determinístico de DOCX: um parágrafo = um <w:r><w:t xml:space=\"preserve\">, ZipInfo.date_time fixo, entradas escritas em sorted() — herdado de templates/build_dvi_base.py"
    - "Placeholder raw isolado no próprio <w:p>: convenção para qualquer placeholder terminado em _xml que precise substituir o parágrafo hospedeiro inteiro (D-08)"

key-files:
  created:
    - templates/build_despacho_templates.py
    - templates/dvi/despacho_geral.docx
    - templates/dvi/despacho_tic.docx
    - tests/test_despacho_templates.py
  modified: []

key-decisions:
  - "Seguido D-08/D-10/D-11/D-12 do 06-CONTEXT.md sem desvio: placeholder raw isolado, regeração byte-estável, templates/dvi/ como pasta própria, um arquivo DOCX por variante de verificação"
  - "DviPecaTitulo e DviAlinea são declarados em word/styles.xml mas não usados na moldura desta rodada — existem apenas como contrato para o builder do Plano 02, conforme o plano determina explicitamente"
  - "word/_rels/document.xml.rels deixou de ser vazio: agora declara rId1 apontando para styles.xml, exigido pelo w:pStyle referenciado em cada parágrafo"

patterns-established:
  - "Templates DOCX institucionais (não-relatório) vivem em templates/<tipo>/, com um gerador Python por família de documento, no molde de templates/build_dvi_base.py"

requirements-completed: [SYSD-16]

duration: ~5min
completed: 2026-08-27
---

# Phase 06 Plan 01: Templates DOCX do Despacho de Verificação Inicial Summary

**Gerador determinístico produz `despacho_geral.docx` e `despacho_tic.docx` — moldura fiel ao modelo institucional real (título, SEI, vocativo, corpo, Observações, assinatura, De acordo), com seis estilos nomeados e um único placeholder raw `{{corpo_apontamentos_xml}}` isolado em seu próprio parágrafo.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-08-27T00:41:00-03:00 (aprox., logo após o commit `90d8348` do planejamento)
- **Completed:** 2026-08-27T00:44:47-03:00
- **Tasks:** 2/2
- **Files modified:** 4 (3 criados + 1 teste criado)

## Accomplishments
- `templates/build_despacho_templates.py` gera as duas variantes (`geral`, `tic`) de forma byte-idêntica em execuções repetidas (D-10)
- Moldura reproduz literalmente `processo-teste/referencias/dvi.md`: título, "Processo SEI n.º", vocativo, contextualização, frase de triagem, bloco de Observações (3 itens, com o item 2 divergindo por variante), assinatura e "De acordo"
- `word/styles.xml` declara os seis estilos nomeados exigidos como contrato para o Plano 02 (`DviTitulo`, `DviSubtitulo`, `DviVocativo`, `DviCorpo`, `DviPecaTitulo`, `DviAlinea`)
- Placeholder raw único `{{corpo_apontamentos_xml}}` isolado em seu `<w:p>`, sem texto adjacente — verificado por teste que extrai o parágrafo hospedeiro e confere que seu `<w:t>` é exatamente o placeholder
- 11 testes novos cobrindo geração determinística, estrutura do ZIP, estilos, órfãos de `w:pStyle`, contrato de placeholders e diferenças entre variantes; suíte completa (480 testes) permanece verde

## Task Commits

Each task was committed atomically:

1. **Task 1: Escrever o gerador determinístico das duas variantes** - `a9f456a` (feat)
2. **Task 2: Testes de estabilidade, estilos e placeholders dos templates** - `40d761e` (test)

**Plan metadata:** _(commit a seguir, deste SUMMARY + STATE + ROADMAP)_

## Files Created/Modified
- `templates/build_despacho_templates.py` - Gerador determinístico das duas variantes do despacho (styles.xml + document.xml + moldura + Observações por variante)
- `templates/dvi/despacho_geral.docx` - Template DOCX, variante geral (sem citação normativa específica)
- `templates/dvi/despacho_tic.docx` - Template DOCX, variante TIC (cita IN SGD/ME 94/2022 na Observação 2)
- `tests/test_despacho_templates.py` - 11 testes: geração determinística/byte-estável, entradas do ZIP, estilos, placeholders, variantes

## Decisions Made
- Nenhuma decisão nova fora do que já estava fixado em D-08/D-10/D-11/D-12 do `06-CONTEXT.md` — plano executado exatamente como especificado, incluindo os nomes de estilo, a ordem exata da moldura e o texto literal das Observações (transcrito de `processo-teste/referencias/dvi.md` linhas 61/63/65, com a variante TIC citando `normas/vigencia.yaml`).
- `word/_rels/document.xml.rels` passou de vazio para declarar a relação com `styles.xml` — consequência direta e obrigatória de introduzir `w:pStyle`, não uma decisão de escopo adicional.

## Deviations from Plan

None - plan executado exatamente como escrito. A única verificação manual fora do texto literal do plano foi confirmar que `test_todo_pstyle_referencia_estilo_declarado` de fato falha quando um estilo referenciado é removido do gerador (exigido pelos `acceptance_criteria` da Task 2) — feito removendo temporariamente `DviTitulo` de `_ESTILOS`, confirmando a falha, e revertendo com `git checkout --`.

## Issues Encountered
- `ruff` não está instalado neste ambiente de execução (`ruff: command not found`, `No module named ruff`). Como `E501` já é ignorado em `pyproject.toml`, a verificação de estilo foi feita manualmente: nenhuma linha viola quebras de import/ordenação, aspas duplas usadas consistentemente, `from __future__ import annotations` presente. Recomenda-se rodar `ruff check templates/build_despacho_templates.py tests/test_despacho_templates.py` assim que `ruff` estiver disponível no ambiente, como verificação de follow-up (não bloqueante — sem indício de violação real).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `templates/dvi/despacho_{geral,tic}.docx` e o contrato de placeholders (`{{projeto.processo}}`, `{{projeto.objeto}}`, `{{despacho.*}}`, `{{corpo_apontamentos_xml}}`) estão prontos para o Plano 02 (builder do corpo dos apontamentos) e Plano 04 (integração com `sysdoc create`/`render_docx_template`)
- Estilos `DviPecaTitulo` e `DviAlinea` já declarados em `word/styles.xml`, aguardando uso pelo builder do Plano 02
- Nenhum bloqueio identificado para as próximas rodadas desta fase (06-02 a 06-07)

---
*Phase: 06-templates-tr-a-partir-dos-modelos-lei-14-133*
*Completed: 2026-08-27*

## Self-Check: PASSED

All created files verified present on disk; all task commits (`a9f456a`, `40d761e`) and the summary commit (`c06141e`) verified present in `git log`.
