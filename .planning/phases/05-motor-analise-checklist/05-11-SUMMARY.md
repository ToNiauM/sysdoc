---
phase: 05-motor-analise-checklist
plan: 11
subsystem: motor-dvi
tags: [python, dataclasses, json, atomic-write, checkpoint, audit-trail]

requires:
  - phase: 05-motor-analise-checklist
    provides: "sysdoc_dvi.tipos (ResultadoItem/UsoModelo), templates/validate_sysdoc.py, checklist DVI id/hash (05-01, 05-03)"
provides:
  - "sysdoc_dvi.montagem.montar_json: converte ResultadoItem em dados_consolidados.json válido (RNF5)"
  - "sysdoc_dvi.relatorio.montar_relatorio/renderizar_relatorio: relatório de execução (RF9)"
  - "sysdoc_dvi.checkpoint: checkpoint incremental de retomada em .sysdoc/cache/dvi_checkpoint.json (D-04)"
affects: [05-09-despacho, 05-10-sintese, 05-14-pipeline, sysdoc-dvi-cli]

tech-stack:
  added: []
  patterns:
    - "Duck-typing de pareceres (dict ou objeto) em montagem para não acoplar a um tipo concreto de síntese ainda não publicado"
    - "Relatório lê tokens/custo de provedores.REGISTRO_CHAMADAS em vez de reagregar ResultadoItem.uso, cobrindo também tentativas de retry"
    - "Escrita atômica: tempfile.mkstemp no mesmo diretório + os.replace"
    - "Reuso direto de validate_item_coherence de templates/validate_sysdoc.py via sys.path, para não duplicar regra de coerência"

key-files:
  created:
    - sysdoc_dvi/montagem.py
    - sysdoc_dvi/relatorio.py
    - sysdoc_dvi/checkpoint.py
    - tests/test_dvi_montagem.py
  modified: []

key-decisions:
  - "'item' (título curto do item na saída) é derivado da primeira frase de parecer (fallback fundamento/checklist_id), truncada em 12 palavras, pois ResultadoItem não carrega um campo de título"
  - "itens_por_tipo no relatório agrupa por documento (ETP/TR); itens_por_status agrupa por classificação — ResultadoItem não carrega o tipo de verificação (presenca/julgamento/...), só o AnalysisAgent que o gerou sabe disso"
  - "pareceres aceita dict ou objeto com atributos parecer_executivo/secao_etp/secao_tr, para não acoplar montagem a sysdoc_dvi.sintese (05-10), que roda em paralelo nesta mesma onda e ainda não está mesclado"
  - "carregar_checkpoint reconstrói ResultadoItem/UsoModelo (não dicts crus) para ser diretamente reaproveitável pelo orquestrador de retomada"

requirements-completed: [RF9, RNF2, RNF5, RF5]

duration: 13min
completed: 2026-08-26
---

# Phase 5 Plan 11: Montagem, Relatório e Checkpoint do Motor DVI Summary

**`sysdoc_dvi.montagem`/`relatorio`/`checkpoint`: converte `ResultadoItem` em `dados_consolidados.json` aprovado pelo validador vigente, produz relatório de custo/tokens/falhas lido de `provedores.REGISTRO_CHAMADAS`, e mantém checkpoint incremental com escrita atômica em `.sysdoc/cache/dvi_checkpoint.json`.**

## Performance

- **Duration:** ~13 min (11:38–11:51 -03:00)
- **Tasks:** 3 completed (cada uma com ciclo RED → GREEN)
- **Files modified:** 4 (3 módulos novos + 1 suíte de testes)
- **Tests:** 47 novos em `tests/test_dvi_montagem.py`; suíte completa: 304 passed

## Accomplishments
- `montar_json` renumera itens por documento (`ETP-NNN`/`TR-NNN`), preserva `checklist_id`, corrige `risco_jurídico` para `informativo` quando `classificação=conforme`, reusa `validate_item_coherence` do validador vigente e falha cedo com `ErroMontagem` (modelo_ia genérico/maiúsculo, hash malformado, projeto incompleto, campos de texto curtos, coerência classificação/risco/severidade).
- `montar_relatorio`/`renderizar_relatorio` produzem contagens por status/documento/origem, falhas de grounding e estruturadas, tokens/custo por modelo (a partir de `provedores.REGISTRO_CHAMADAS`, cobrindo inclusive retries), avisos de norma desatualizada e de alvo sem preço registrado, e texto de handoff terminando em `sysdoc create dvi`.
- `checkpoint.py` grava/retoma execuções longas: escrita atômica por item, invalidação total quando o `checklist_hash` muda, tolerância a arquivo corrompido (aviso, sem exceção), e `limpar_checkpoint` idempotente.

## Task Commits

Cada task seguiu RED → GREEN (TDD):

1. **Task 1: montar_json com renumeração e metadados de auditoria**
   - `b671d4a` test(05-11): add failing tests for montagem do dados_consolidados.json
   - `83638ba` feat(05-11): implement montar_json com renumeração e auditoria (RNF5)
2. **Task 2: Relatório de execução**
   - `e21811d` test(05-11): add failing tests for relatório de execução (RF9)
   - `85d19b6` feat(05-11): implement relatório de execução do motor DVI (RF9)
3. **Task 3: Checkpoint incremental e suíte tests/test_dvi_montagem.py**
   - `15937d8` test(05-11): add failing tests for coerência e checkpoint incremental (D-04)
   - `10ddad5` feat(05-11): implement checkpoint incremental de retomada (D-04)

**Plan metadata:** (this commit)

## Files Created/Modified
- `sysdoc_dvi/montagem.py` - `montar_json`/`ErroMontagem`: converte `ResultadoItem` em `dados_consolidados.json`
- `sysdoc_dvi/relatorio.py` - `montar_relatorio`/`renderizar_relatorio`: relatório de execução JSON e texto
- `sysdoc_dvi/checkpoint.py` - `carregar_checkpoint`/`registrar_item`/`limpar_checkpoint`: retomada incremental
- `tests/test_dvi_montagem.py` - `TestMontagem`, `TestCoerencia`, `TestIds`, `TestRelatorio`, `TestCheckpoint` (47 testes)

## Decisions Made
- `pareceres` (parâmetro de `montar_json`) aceita `dict` ou objeto com os atributos esperados, em vez de importar um tipo `Pareceres` concreto — `sysdoc_dvi/sintese.py` (plano 05-10) roda na mesma onda e ainda não estava mesclado neste worktree no momento da execução. A leitura via `_campo`/`_montar_secao` (dict.get ou getattr) é compatível com o que quer que 05-10 publique, desde que exponha os mesmos nomes de campo.
- O título curto de cada item (chave `item` exigida pelo validador) é derivado da primeira frase de `parecer` (fallback `fundamento`, depois `checklist_id`), truncada em 12 palavras — `ResultadoItem` não carrega um campo de título dedicado.
- `itens_por_tipo` no relatório agrupa por `documento` (ETP/TR), não pelo tipo de verificação do checklist (`presenca`/`julgamento`/...), porque `ResultadoItem` não carrega esse dado — só o `ItemChecklist` original o tem, e `montar_relatorio` só recebe a lista de resultados.
- `carregar_checkpoint` reconstrói `ResultadoItem`/`UsoModelo` (não dicionários crus) para já sair pronto para o orquestrador de retomada comparar/reutilizar, mesmo que a assinatura das `<interfaces>` do plano anotasse `dict[str, dict]`.

## Deviations from Plan

None - plan executado exatamente como escrito. As decisões acima são preenchimento de lacunas de "Claude's Discretion" já autorizadas em `05-CONTEXT.md` (formato interno do checkpoint e do relatório), não desvios de comportamento especificado.

## Issues Encountered
- Bug próprio introduzido durante a implementação do Task 2 (não do plano): `montar_relatorio` chamou `normas_desatualizadas(..., limiar_dias_vigencia=...)`, mas a assinatura real em `sysdoc_dvi/normas.py` (produzida no plano 05-04) usa `limiar_dias`. Pego pela suíte GREEN do próprio ciclo TDD (`test_norma_desatualizada_gera_aviso`) antes do commit; corrigido trocando o nome do kwarg. Nenhum commit ficou com o bug.

## User Setup Required
None - nenhuma configuração de serviço externo requerida por este plano.

## Next Phase Readiness
- `montar_json`, `montar_relatorio`/`renderizar_relatorio` e o checkpoint estão prontos para serem chamados pelo orquestrador (plano 05-09/despacho) e pelo pipeline `sysdoc-dvi run` (plano 05-14): a assinatura de `montar_json` aceita qualquer `pareceres` dict-like, então a integração com a síntese real (05-10) não deve exigir mudança nesta camada.
- Ponto de atenção para 05-09/05-14: `montar_json` levanta `ErroMontagem` para qualquer `de`/`para`/`parecer`/`fundamento` vazio ou com menos de 3 palavras, **inclusive** em itens `pendente` por `falha_estruturada` (hoje `agente.AgenteLLM._resultado_pendente` produz esses campos vazios). O orquestrador precisa preencher texto mínimo determinístico para itens que falharam (ex.: "Item pendente: falha ao obter resposta do modelo.") antes de chamar `montar_json`, ou a montagem abortará a execução inteira por causa de um único item com falha — isso é intencional (RNF5 exige JSON que passa no validador sem edição manual) mas precisa ser resolvido no wiring, não nesta camada.
- Nenhum stub ou dado mockado deixado nos três módulos; toda a superfície pública tem cobertura de teste correspondente.

## TDD Gate Compliance

Cada task tem par `test(...)` (RED) → `feat(...)` (GREEN) confirmado no git log, nesta ordem:
`b671d4a`→`83638ba`, `e21811d`→`85d19b6`, `15937d8`→`10ddad5`. Todos os RED foram confirmados
por execução real (`ModuleNotFoundError`/`ImportError` antes da implementação existir), não
apenas por inspeção estática.

## Self-Check: PASSED

- FOUND: sysdoc_dvi/montagem.py
- FOUND: sysdoc_dvi/relatorio.py
- FOUND: sysdoc_dvi/checkpoint.py
- FOUND: tests/test_dvi_montagem.py
- FOUND: .planning/phases/05-motor-analise-checklist/05-11-SUMMARY.md
- FOUND commit: b671d4a, 83638ba, e21811d, 85d19b6, 15937d8, 10ddad5

---
*Phase: 05-motor-analise-checklist*
*Completed: 2026-08-26*
