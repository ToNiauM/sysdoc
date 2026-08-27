---
phase: 06-templates-tr-a-partir-dos-modelos-lei-14-133
plan: 02
subsystem: docx-generation
tags: [xml-escape, docx, dvi, despacho, deterministic-builder]

requires:
  - phase: 06-01
    provides: "templates/dvi/despacho_geral.docx e despacho_tic.docx com placeholder raw {{corpo_apontamentos_xml}} e estilos DviPecaTitulo/DviAlinea"
provides:
  - "sysdoc_docx.corpo_dvi.build_corpo_despacho_xml(dados) -> XML de <w:p> filtrado, agrupado por peça, numerado e com referência cruzada resolvida"
  - "sysdoc_docx.corpo_dvi.montar_apontamentos(dados) -> estrutura intermediária de seções/alíneas para inspeção e teste"
  - "pacote sysdoc_docx/ registrado em pyproject.toml, pronto para sysdoc.py importar no Plano 04"
affects: [06-03, 06-04, 06-05, 06-06, 06-07]

tech-stack:
  added: []
  patterns:
    - "Builder Python puro -> string para placeholder raw (mesmo padrão de build_tabela_itens em sysdoc.py:1214), mas devolvendo XML já pronto em vez de texto simples"
    - "Único emissor de texto do módulo (_paragrafo) — todo texto passa por xml.sax.saxutils.escape antes de entrar no <w:t>"
    - "Resolução em duas passadas: numeração fechada antes de gerar texto, para permitir referência cruzada apontar para rótulo (item N, alínea x) já resolvido"

key-files:
  created:
    - sysdoc_docx/__init__.py
    - sysdoc_docx/corpo_dvi.py
    - tests/test_dvi_corpo.py
  modified:
    - pyproject.toml

key-decisions:
  - "Chave de equivalência de D-07 usa apenas parecer normalizado (não parecer+fundamento como o plano originalmente instruía) — ver Deviations"
  - "Comparação de anterioridade entre alíneas usa índice inteiro por seção, não a string da letra, para não quebrar a partir da 27ª alínea (\"aa\" < \"z\" lexicograficamente, mas é a alínea posterior)"

requirements-completed: [SYSD-17]

duration: 25min
completed: 2026-08-27
---

# Phase 6 Plan 02: Builder do corpo de apontamentos do despacho DVI Summary

**Builder Python puro que filtra os 49 itens de `dados_consolidados.json` para as 11 alíneas que realmente importam (D-03), agrupa por peça em ordem canônica, resolve 2 referências cruzadas automáticas (D-07) e devolve XML de `<w:p>` pronto para o placeholder raw do template do Plano 01 — com todo texto de origem LLM escapado por `xml.sax.saxutils.escape`.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-08-27T03:45:59Z (herdado do fim do Plano 01)
- **Completed:** 2026-08-27T03:56:00Z
- **Tasks:** 2/2
- **Files modified:** 4 (3 criados, 1 modificado)

## Accomplishments
- `sysdoc_docx/corpo_dvi.py` materializa a regra que governa a fase inteira: "no DVI deve conter tão somente o que tem de ser ajustado" — `conforme` nunca aparece, `pendente` vira seção própria ao final, o campo `para` nunca é lido.
- Seções por peça são dinâmicas (D-05): sobre `processo-teste/dados_consolidados.json`, produz exatamente `1) ESTUDO TÉCNICO PRELIMINAR - ETP` (5 alíneas), `2) TERMO DE REFERÊNCIA - TR` (6 alíneas) e `3) PENDÊNCIAS DE DOCUMENTAÇÃO` (14 alíneas) — os 24 itens `conforme` desaparecem do documento.
- Referência cruzada (D-07) resolvida corretamente contra o dataset real: 2 ocorrências de `Vide apontamento constante na alínea`, apontando `TR-002` → alínea "c" do item 1 e `TR-001` → alínea "e" do item 1.
- `TestSegurancaXml` prova, com 4 payloads adversariais (`</w:t>`, `&`, `]]>`, `<script>`), que nenhum deles escapa do `<w:t>`; a suíte falha deliberadamente quando `escape()` é removido de `_paragrafo` (verificado manualmente antes de reverter).

## Task Commits

1. **Task 1: Criar o pacote sysdoc_docx e o builder do corpo do despacho** - `06220a7` (feat)
2. **Task 2: Testes do builder — filtro, numeração, referência cruzada e escape** - `9d7eeab` (test)

**Plan metadata:** commit deste SUMMARY (a seguir)

## Files Created/Modified
- `sysdoc_docx/__init__.py` - docstring do pacote de geração DOCX determinística
- `sysdoc_docx/corpo_dvi.py` - builder puro: constantes (D-03 a D-08), helpers privados (`_texto`, `_letra`, `_chave_equivalencia`, `_paragrafo`, `_cabecalho_peca`, `_prefixo_secao`, `_corpo_parecer_fundamento`, `_texto_alinea`, `_texto_referencia_cruzada`), `montar_apontamentos()` e `build_corpo_despacho_xml()`
- `tests/test_dvi_corpo.py` - 26 testes em 7 classes (`TestFiltroDeClassificacao`, `TestSecoesDinamicas`, `TestPendencias`, `TestTextoDaAlinea`, `TestReferenciaCruzada`, `TestSegurancaXml`, `TestIntegracaoProcessoTeste`)
- `pyproject.toml` - `[tool.setuptools] packages = ["sysdoc_dvi", "sysdoc_docx"]`

## Decisions Made
- Comparação de "alínea anterior" (D-07) feita por `(número_da_seção, índice_0-based)` em vez de comparar as strings de letra — a comparação lexicográfica de string quebraria a partir da 27ª alínea de uma seção (`"aa" < "z"` como string, mas `"aa"` é a alínea posterior). Não observável no dataset atual (máximo 14 alíneas numa seção), mas é uma correção estrutural preventiva de baixo custo.
- `_corpo_parecer_fundamento` trata `parecer`/`fundamento` vazios individualmente (concatenação sem espaço solto) em vez de assumir que ambos sempre estão preenchidos — nenhum item do schema tem esses campos como opcionais, mas o helper fica correto mesmo se um vier vazio.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Chave de equivalência de D-07 usa só `parecer`, não `parecer+fundamento`**
- **Found during:** Task 1, verificação contra `processo-teste/dados_consolidados.json`
- **Issue:** O plano instruía `_chave_equivalencia` a normalizar `parecer + "␟" + fundamento`, com base num achado do planejamento afirmando que os pares `ETP-016`/`TR-002` e `ETP-019`/`TR-001` têm "parecer+fundamento idênticos" entre ETP e TR. Medindo diretamente no dataset: `ETP-019`/`TR-001` de fato têm `parecer` e `fundamento` idênticos, mas `ETP-016`/`TR-002` têm `parecer` idêntico (25.660 caracteres) e `fundamento` que **difere** apenas pelo nome da peça ("...numeração sequencial de seções do ETP" vs "...do TR") — um efeito colateral do verificador determinístico de numeração de seções, que sempre menciona a peça analisada no `fundamento`. Usando a chave `parecer+fundamento` como escrito no plano, apenas 1 das 2 referências cruzadas esperadas era detectada, violando o critério de aceite explícito ("exatamente 2 ocorrências... os pares ETP-016/TR-002 e ETP-019/TR-001").
- **Fix:** `_chave_equivalencia` passou a normalizar apenas `parecer` (NFKC + colapso de espaços + `.strip()` + `.casefold()`), descartando `fundamento` da chave. Verificado que, entre os 11 itens que entram no corpo (`ajuste_necessário`/`risco`), essa chave não produz nenhum falso positivo — só os 2 pares esperados colidem.
- **Files modified:** `sysdoc_docx/corpo_dvi.py` (`_chave_equivalencia`, com docstring documentando a medição que motivou a mudança)
- **Verification:** `python3 -c "...montar_apontamentos(d)..."` sobre o dataset real mostra `vide count: 2` (era `1` com a chave original); suíte completa de 506 testes verde.
- **Committed in:** `06220a7`

## Known Stubs

Nenhum. O módulo não introduz stub — ele é consumido apenas pelos testes desta rodada; a integração com `sysdoc create dvi` (leitura do placeholder raw) é escopo do Plano 04.

## Threat Flags

Nenhum flag novo — toda a superfície de risco identificada (injeção via `parecer`/`fundamento`/`seção`, injeção via `w:pStyle`) já estava coberta pelo `<threat_model>` do próprio plano e foi mitigada e testada conforme especificado (`T-06-02-01` a `T-06-02-05`).

## Verification Results

```
python3 -m pytest tests/test_dvi_corpo.py -v   → 26 passed
python3 -m pytest tests/ -q                     → 506 passed
ruff check sysdoc_docx/ tests/test_dvi_corpo.py → All checks passed!
python3 -c "import sysdoc_docx.corpo_dvi"       → exit 0, sem import de sysdoc/sysdoc_dvi
```

## Self-Check: PASSED

- FOUND: sysdoc_docx/__init__.py
- FOUND: sysdoc_docx/corpo_dvi.py
- FOUND: tests/test_dvi_corpo.py
- FOUND: pyproject.toml (packages atualizado)
- FOUND: commit 06220a7
- FOUND: commit 9d7eeab
