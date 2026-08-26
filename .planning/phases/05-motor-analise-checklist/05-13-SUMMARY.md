---
phase: 05-motor-analise-checklist
plan: 13
subsystem: checklist-dvi
tags: [dvi, checklist, yaml, vigencia, conversao-prompts]

# Dependency graph
requires:
  - phase: 05-motor-analise-checklist
    provides: "checklists/dvi.yaml seed (plano 05-01) e normas/vigencia.yaml formato (plano 05-04)"
provides:
  - "checklists/dvi.yaml completo: 75 itens tipados (29 DVI-AMB-*, 27 DVI-GER-*, 19 DVI-TIC-*) cobrindo os cinco tipos de verificação e as três aplicabilidades"
  - "normas/vigencia.yaml semeado com as 14 normas citadas nos dois prompts-fonte, incluindo a substituição institucional Portaria PRES CFC 266/2025 → Resolução CFC 1.799/26"
  - "tests/test_dvi_checklist_conteudo.py: 12 testes de invariante de conteúdo, incluindo o teste de mutação que prova CA4"
affects: [05-14, 05-15, "qualquer plano que consuma checklists/dvi.yaml completo"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "referencia com prefixo 'Padrão interno:' marca item ativo cujo checklist não é uma norma externa (numeração, assinatura, modelo de proposta) — isento do invariante de cobertura na tabela de vigência"

key-files:
  created:
    - tests/test_dvi_checklist_conteudo.py
  modified:
    - checklists/dvi.yaml
    - normas/vigencia.yaml
    - .gitignore

key-decisions:
  - "Task 1 (checkpoint) resolvida: o dono do produto forneceu referencias/prompts-dvi/dvi_geral.md e dvi_tic.md, comitados em 0064125b; esta execução parte desse commit"
  - "Granularidade de conversão para listas enumeradas (Art. 9º IN 58/2022, Art. 11/12 IN 94/2022, Art. 9º IN 81/2022): um item presenca por inciso de nível superior (sem desmembrar sub-alíneas a/b/c em itens próprios) — produz 40 itens de presença só nos quatro blocos de elementos obrigatórios, explicando o total de 75 itens frente à estimativa de '~50' do PRD/CONTEXT"
  - "DVI-GER-001 (seed): a verificação de numeração sequencial do TR aparece com texto idêntico nos dois prompts-fonte (TR §23 geral e TR §23 TIC); reclassificada para aplicabilidade: ambos mantendo o id DVI-GER-001 (prefixo GER preservado por instrução explícita do plano — 'preservar ids onde correspondem, enriquecer em vez de renumerar'). checklist.py não valida correspondência entre prefixo do id e campo aplicabilidade, então isso é estruturalmente válido; documentado aqui como desvio intencional e mínimo"
  - "DVI-AMB-001, DVI-AMB-002 e DVI-TIC-001 (seed) permanecem inalterados (pendente/ativo:false): nenhum dos dois prompts-fonte contém transcrição literal correspondente (necessidade genérica art. 18 §1º I, critério de julgamento genérico, e alinhamento ao PDTIC não é mencionado em nenhum dos dois prompts)"
  - "Campo 'referencia' de item ativo normalmente contém apenas o nome da norma (sem número de artigo/inciso), para que consultar_norma() resolva a citação inteira contra normas/vigencia.yaml; detalhes de artigo/inciso ficam em pergunta/base_legal_texto. Para checks puramente procedimentais sem norma externa (numeração, assinatura, modelo de proposta, cronograma, coerência ETP×TR, obrigações das partes, sanções/PROJUR), referencia usa o prefixo 'Padrão interno:' e é isento do invariante de cobertura de vigência — decisão registrada e testada explicitamente em tests/test_dvi_checklist_conteudo.py"
  - "Regra de ativação: item nasce ativo:true quando o prompt-fonte descreve um critério de verificação autocontido e acionável (mesmo citando lei apenas por número, ex.: reajuste com a regra explícita do Art. 25 §7º, garantia com os percentuais 5%/85% explícitos); nasce ativo:false/pendente quando o prompt apenas remete a 'legislação aplicável' ou 'jurisprudência do TCU' sem descrever o conteúdo da norma/entendimento (ex.: subcontratação, condições de pagamento IN 77/2022 sem os prazos/limites, jurisprudência TCU genérica) — nunca reconstruído de memória, conforme CLAUDE.md"
  - "TR item de 'Formatação do Documento' (margens, fonte, espaçamento) convertido em item DVI-AMB-027 mas mantido ativo:false: verificação de formatação visual está explicitamente fora do escopo desta fase (RF4/PRD §4 — requer o DOCX original, não o texto extraído)"
  - "Seções 'RESULTADO' dos dois prompts (formato de relatório de auditoria) NÃO viraram itens de checklist — já atendidas pela síntese existente (sysdoc_dvi/sintese.py), conforme regra de conversão nº 4"
  - "A instrução dos prompts-fonte 'Deixe o texto mais natural possível, visando eliminar os indícios de que trata-se de um texto feito por IA' foi DELIBERADAMENTE NÃO implementada: o SysDoc registra modelo_ia nos metadados do JSON (exigido pelo validador) e o DVI é uma minuta assistida por IA para revisão humana, não um documento que deva ocultar sua origem — divergência do prompt-fonte registrada aqui conforme instrução do orquestrador"
  - "A observação 'Se tiver algum DVI ao final do processo, desconsidere' (só no dvi_geral.md) é orientação de mapeamento de peças, não um item de checklist — registrada como comentário no cabeçalho descricao de checklists/dvi.yaml"
  - "referencias/prompts-dvi/dvi_geral.md e dvi_tic.md: adicionados ao .gitignore (T-05-43) e removidos do índice (git rm --cached) nesta execução; o commit de checkpoint 0064125b que os introduziu permanece no histórico (não reescrito) — mitigação vale para commits futuros"

patterns-established:
  - "Prefixo 'Padrão interno:' em referencia como marcador estrutural, testável, para checks sem norma externa formal"

requirements-completed: [RF1, RF2, RF7, RNF1]

# Metrics
duration: ~55min
completed: 2026-08-26
---

# Phase 5 Plan 13: Conversão dos prompts DVI monolíticos — Summary

**Os dois prompts DVI monolíticos (processos gerais e TIC, fornecidos pelo dono do produto após o checkpoint da Task 1) foram convertidos integralmente em 75 itens tipados de `checklists/dvi.yaml`, e `normas/vigencia.yaml` foi semeado com as 14 normas citadas — nenhum dispositivo legal foi inventado; itens sem transcrição literal disponível nasceram `ativo: false` com `base_legal_texto: pendente`.**

## Performance

- **Duration:** ~55 min (retomada; Task 1 já resolvida por entrada humana antes desta sessão)
- **Started:** 2026-08-26T12:00:00-03:00 (aprox., retomada pós-checkpoint)
- **Completed:** 2026-08-26T12:59:22-03:00
- **Tasks:** 2/2 executadas nesta sessão (Task 1 resolvida em sessão anterior via commit 0064125b)
- **Files modified:** 4 (checklists/dvi.yaml, normas/vigencia.yaml, .gitignore, tests/test_dvi_checklist_conteudo.py — mais a remoção de rastreamento de referencias/prompts-dvi/*.md)

## Accomplishments

- Leitura integral de `referencias/prompts-dvi/dvi_geral.md` (240 linhas) e `dvi_tic.md` (230 linhas), os dois prompts monolíticos de auditoria de processo.
- Conversão de todas as verificações em 75 itens tipados em `checklists/dvi.yaml`: 45 `presenca`, 21 `julgamento`, 3 `calculo`, 2 `vigencia`, 4 `mecanica`; 29 `ambos`, 27 `geral` (26 com id GER + o item DVI-GER-001 reclassificado como ambos), 19 `tic`.
- Deduplicação disciplinada: toda verificação com o mesmo conteúdo substantivo nos dois prompts (auditoria de cálculos do MCP, vigência de normativos, cálculos do ETP/TR, garantia contratual/adicional, SRP/adesão Acórdão 1.872/2018, POC/amostra, subcontratação, cota 25%, cronograma físico-financeiro, condições de pagamento, numeração sequencial do TR, assinaturas, formatação, verificação cruzada ETP×TR, sanções/PROJUR/CFC, reajuste Art. 25 §7º) virou um único item `DVI-AMB-*`, nunca duplicada.
- `normas/vigencia.yaml` semeado com 8 novas normas (IN SEGES/ME 81/2022, Portaria SEGES 938/2022, IN SEGES 77/2022, IN nº 05/2017, Decreto 11.462/2023, Portaria STI/MP 46/2016, Portaria PRES CFC 266/2025, Resolução CFC 1.799/26), somando 14 normas na tabela; status honesto (`pendente_de_conferencia` salvo onde o prompt-fonte afirma o status, caso da substituição CFC).
- `tests/test_dvi_checklist_conteudo.py` criado com 12 testes cobrindo todos os invariantes pedidos pela Task 3, incluindo o teste de mutação que prova CA4 do PRD.
- Suíte completa (`pytest tests/`) verde: **376 testes passando**, incluindo os 24 testes pré-existentes de `test_dvi_checklist.py` e os 12 novos.
- `referencias/prompts-dvi/*.md` adicionados ao `.gitignore` e removidos do índice do git (T-05-43), mantendo o conteúdo em disco para consulta local sem versionar o insumo interno do órgão.

## Task Commits

1. **Task 2 — Converter os prompts em itens tipados do checklist** — `280bc53` `feat(05-13): convert DVI prompts into typed checklist items (Task 2)` — `checklists/dvi.yaml` (75 itens), `.gitignore` (+`referencias/prompts-dvi/`), remoção do rastreamento dos dois prompts-fonte do índice git.
2. **Task 3 — Semear a tabela de vigência e travar os invariantes de conteúdo** — `85bd39e` `test(05-13): seed normas/vigencia.yaml and lock checklist content invariants (Task 3)` — `normas/vigencia.yaml` (+8 normas), `tests/test_dvi_checklist_conteudo.py` (novo, 12 testes).

## Files Created/Modified

- `checklists/dvi.yaml` — de 6 para 75 itens; seed enriquecido (DVI-AMB-003, DVI-AMB-004, DVI-GER-001 ativados/enriquecidos com texto literal dos prompts-fonte); demais 4 seeds inalterados por falta de correspondência literal.
- `normas/vigencia.yaml` — de 6 para 14 normas.
- `.gitignore` — nova linha `referencias/prompts-dvi/`.
- `tests/test_dvi_checklist_conteudo.py` — novo arquivo, 12 testes.
- `.planning/phases/05-motor-analise-checklist/05-13-SUMMARY.md` — este resumo (substitui a versão que documentava apenas o bloqueio da Task 1).

## Decisions Made

Ver `key-decisions` no frontmatter — resume as decisões de granularidade de conversão, o tratamento do seed DVI-GER-001 (reclassificado para `ambos` mantendo o id), o padrão `Padrão interno:` no campo `referencia` para checks sem norma externa, a regra de ativação de itens (autocontido/acionável → ativo; remissão genérica sem conteúdo → pendente), a decisão de não implementar a instrução de ocultar autoria por IA, e a remoção do rastreamento dos prompts-fonte do git.

## Deviations from Plan

### Auto-fixed / Rule 2 (missing critical functionality) — mitigação de disclosure dos prompts-fonte

- **Found during:** Task 2.
- **Issue:** os dois arquivos `referencias/prompts-dvi/dvi_geral.md` e `dvi_tic.md`, fornecidos pelo dono do produto para resolver o checkpoint da Task 1, já haviam sido comitados ao repositório (commit `0064125b`, fora do escopo desta execução) antes do `.gitignore` ser atualizado. Isso é exatamente a ameaça `T-05-43` (Information Disclosure) que a Task 2 deveria mitigar.
- **Fix:** acrescentado `referencias/prompts-dvi/` ao `.gitignore` e executado `git rm --cached` nos dois arquivos, untracking-os para commits futuros. O histórico do commit `0064125b` não foi reescrito (fora do escopo e arriscado sem coordenação); a mitigação vale a partir desta execução em diante.
- **Files modified:** `.gitignore`; remoção de `referencias/prompts-dvi/dvi_geral.md` e `dvi_tic.md` do índice.
- **Commit:** `280bc53`.

Nenhum outro desvio das Rules 1–3 foi necessário. Nenhuma questão arquitetural (Rule 4) surgiu.

## Issues Encountered

Nenhum bloqueio técnico. A principal dificuldade foi de design, não de execução: reconciliar a instrução textual da Task 3 ("todo referencia de item ativo é encontrado por consultar_norma na tabela") com o `must_haves.truths` do plano ("Toda norma citada nos itens tem entrada correspondente em normas/vigencia.yaml") para itens cujo checklist é puramente procedimental (numeração, assinatura, modelo de proposta) e não cita norma externa alguma. Resolvido com o marcador estrutural `Padrão interno:` no campo `referencia`, testado explicitamente — ver key-decisions.

## Known Stubs

Nenhum. Todos os 75 itens têm dado real (não placeholder). Os 12 itens `ativo: false` (incluindo os 4 seeds originais não enriquecidos) são pendências explícitas e documentadas, não stubs silenciosos — cada um declara `base_legal_texto: pendente` e uma `referencia` explicando por que a base legal não pôde ser transcrita do prompt-fonte.

## User Setup Required

Nenhuma ação humana pendente para este plano. Os dois arquivos-fonte permanecem em `referencias/prompts-dvi/` no disco (agora ignorados pelo git) para eventual nova conferência humana.

**Recomendação para o dono do produto:** os 12 itens `ativo: false` desta conversão (`DVI-AMB-001`, `DVI-AMB-002`, `DVI-AMB-011`, `DVI-AMB-012`, `DVI-AMB-024`, `DVI-AMB-027`, `DVI-GER-016`, `DVI-TIC-001`, `DVI-TIC-007`, e mais 3 já existentes no seed original) são candidatos naturais a uma curadoria futura: fornecer a transcrição literal do dispositivo (ex.: art. 7º da IN SEGES 77/2022 com os prazos/limites reais) ativaria o item sem alteração de código.

## Next Phase Readiness

Desbloqueado. `checklists/dvi.yaml` está completo, tipado, roteável e consistente com `normas/vigencia.yaml`; `sysdoc_dvi.checklist.carregar_checklist` carrega sem erro estrutural; a suíte completa está verde (376 testes). Os planos 05-14/05-15 e qualquer plano futuro que consuma o checklist completo (ex.: orquestrador ponta a ponta) podem prosseguir.

---
*Phase: 05-motor-analise-checklist*
*Completed: 2026-08-26*

## Self-Check: PASSED

All claimed files and commit hashes verified present in the worktree and git log.
