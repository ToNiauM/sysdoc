---
phase: 05-motor-analise-checklist
plan: 10
subsystem: motor-dvi/sintese
tags: [sintese, pareceres, rf6, jinja2, tdd, agente-falso]
dependency-graph:
  requires: ["05-01", "05-08"]
  provides:
    - "sysdoc_dvi/sintese.py: sintetizar, classificar_documento, ErroSintese, Pareceres, AgenteSintese, word_count, SCHEMA_PARECER_EXECUTIVO, SCHEMA_PARECER_DOCUMENTO"
    - "sysdoc_dvi/prompts/sintese_executivo.jinja, sintese_documento.jinja"
  affects:
    - "05-12 (montagem.py consome Pareceres para montar dados_consolidados.json)"
    - "05-14 (pipeline.py precisa fornecer um `agente` compatível com AgenteSintese.chamar ao alvo forte)"
tech-stack:
  added: []
  patterns:
    - "Retry único local (não o retry de JSON malformado de provedores.chamar_modelo) contando palavras com o mesmo regex de templates/validate_sysdoc.py.word_count"
    - "Classificação de documento 100% determinística, nunca pedida ao modelo (RF6)"
    - "Itens reduzidos a 7 campos estruturados antes de entrar em qualquer prompt de síntese — nunca o texto das peças"
key-files:
  created:
    - sysdoc_dvi/sintese.py
    - sysdoc_dvi/prompts/sintese_executivo.jinja
    - sysdoc_dvi/prompts/sintese_documento.jinja
    - tests/test_dvi_sintese.py
  modified: []
decisions:
  - "agente: AgenteSintese (Protocol local, não sysdoc_dvi.tipos.AnalysisAgent) exigindo .chamar(alvo, prompt, *, schema=None) -> RespostaModelo — ver 'Deviations from Plan' abaixo"
  - "Campo 'item' (título) listado no <action> da Task 1 para a redução de itens foi omitido: ResultadoItem (tipos.py, frozen) não tem esse campo — apenas ItemChecklist.pergunta o teria, e sintetizar() só recebe list[ResultadoItem]"
  - "nota_integridade é sempre construída localmente por _nota_integridade(itens), nunca delegada ao modelo, citando total de itens, partição por origem_verificacao (ordenada alfabeticamente) e contagem de pendentes por falha_grounding/falha_estruturada"
metrics:
  duration: "~50 min"
  completed: "2026-08-26"
  tasks_completed: 3
  tasks_total: 3
  files_created: 4
  tests_added: 14
  tests_total_suite: 271
---

# Phase 5 Plan 10: Síntese dedicada dos pareceres (RF6) Summary

Uma chamada final ao modelo forte, alimentada apenas por itens já validados e reduzidos a 7 campos estruturados, produz `parecer_executivo` e os dois `parecer_documento` com retry único garantindo os mínimos de palavras (450/120) do validador; `classificação_documento` é sempre calculada localmente, nunca pedida ao modelo.

## What Was Built

**Task 1 — Templates e classificação determinística (`sysdoc_dvi/prompts/sintese_executivo.jinja`, `sintese_documento.jinja`, `sysdoc_dvi/sintese.py`):** os dois templates recebem apenas `projeto` (órgão, processo, objeto, valor_estimado) e `itens` reduzidos a `checklist_id`, `documento`, `seção`, `classificação`, `severidade`, `risco_jurídico`, `parecer` — nunca o campo `de`/`para`/`fundamento` nem o texto das peças. Ambos exigem português do Brasil em norma culta, proíbem reticências/placeholders e proíbem citar norma, acórdão, valor ou data ausente dos itens recebidos; o executivo exige cobertura de itens bloqueantes/críticos e mínimo de 450 palavras, o de documento exige 120. Um bloco condicional `nota_retry` injeta a contagem obtida/exigida na segunda tentativa. `classificar_documento(itens, documento)` é 100% determinística: `risco_jurídico == "bloqueante"` em qualquer item da peça → `reprovado`; senão item `pendente` → `pendente_de_complementação`; senão `ajuste_necessário` ou (`risco` com `risco_jurídico == "relevante"`) → `aprovado_com_ressalvas`; caso contrário `aprovado`.

**Task 2 (TDD) — `sintetizar()` com retry único:** RED (`test(05-10)`, commit `c184e49`) — suíte completa criada antes da implementação, falhando com `ImportError: cannot import name 'sintetizar'`. GREEN (`feat(05-10)`, commit `e0c4df0`) — `sintetizar(itens, projeto, agente, numero_etp, numero_tr)` reduz os itens uma vez, chama o agente no alvo `"forte"` para o executivo e, em seguida, uma vez por documento (ETP, TR) para o parecer de peça. Cada chamada usa `_chamar_com_retry`: conta palavras com exatamente o mesmo regex de `templates/validate_sysdoc.py.word_count` (`\b\w+\b`, `re.UNICODE`); abaixo do mínimo, monta um segundo prompt com `nota_retry={"obtido":..., "minimo":...}` e chama novamente; ainda abaixo, levanta `ErroSintese` citando a contagem. `Pareceres.uso` acumula um `UsoModelo` por chamada real ao agente (2 a 4 chamadas totais, dependendo de quantos pareceres precisaram do retry). `nota_integridade` é montada localmente por `_nota_integridade`, citando o total de itens, a partição por `origem_verificacao` e quantos itens `pendente` carregam `falha_grounding`/`falha_estruturada`.

**Task 3 — Suíte `tests/test_dvi_sintese.py`:** a suíte completa (14 testes: `TestClassificacao` ×5, `TestTemplate` ×2, `TestMinimos` ×4, `TestNotaIntegridade` ×1, `TestUso` ×2) já nasceu no commit RED da Task 2, porque o `<verify>` da Task 1 do próprio plano referenciava `pytest tests/test_dvi_sintese.py -k "Classificacao or Template"` antes de o arquivo existir — a mesma classe de inconsistência de sequenciamento já documentada no SUMMARY do plano 05-01 ("problema no comando de verificação do plano, não no artefato produzido"). Nenhuma mudança de arquivo adicional foi necessária nesta task; apenas a reverificação abaixo.

`AgenteFalso` (em `tests/test_dvi_sintese.py`) implementa `.chamar(alvo, prompt, *, schema=None) -> RespostaModelo` com uma fila de respostas programadas consumida em ordem e um registro `.chamadas` de `(alvo, prompt, schema)` para contagem/inspeção.

## Verification

- `python -m pytest tests/test_dvi_sintese.py -q` → **14 passed** (Task 1 + Task 2 + Task 3, mesma suíte).
- `python -m pytest tests/ -q` → **271 passed** (257 preexistentes + 14 novos, 0 regressões).
- `grep -c "450" sysdoc_dvi/prompts/sintese_executivo.jinja` → 1; `grep -c "120" sysdoc_dvi/prompts/sintese_documento.jinja` → 1.
- `grep -c "def classificar_documento" sysdoc_dvi/sintese.py` → 1.
- `python -c "from sysdoc_dvi.sintese import classificar_documento as c;print(c([],'ETP'))"` → `aprovado` (valor do enum `classificação_documento`).
- `grep -c "trecho_peca\|texto_peca" sysdoc_dvi/prompts/sintese_*.jinja` → 0 em ambos os arquivos.
- `grep -c "450" sysdoc_dvi/sintese.py` → 2; `grep -c "120" sysdoc_dvi/sintese.py` → 2; `grep -c "class ErroSintese" sysdoc_dvi/sintese.py` → 1.
- Verificação ponta a ponta do bullet do plano ("Um JSON montado com os pareceres da síntese passa nos mínimos de `templates/validate_sysdoc.py`"): script standalone chamou `sintetizar()` com um `AgenteFalso`, montou um `dados_consolidados.json` sintético com `parecer_executivo`/`secao_etp`/`secao_tr`/`nota_integridade` vindos da síntese, e rodou `templates/validate_sysdoc.py` sobre ele — nenhum erro relativo a `parecer_executivo`, `secao_etp`, `secao_tr`, `classificação_documento` ou `nota_integridade` (as duas únicas falhas reportadas foram `itens[1]/itens[2]: campo 'para' está curto demais`, sobre os itens de teste do checklist — responsabilidade de `montagem.py`, plano 05-12, fora do escopo deste plano).

## Deviations from Plan

### Auto-fixed / Documented Issues

**1. [Rule 4-adjacent, documented via discretion] `agente: AnalysisAgent` do bloco `<interfaces>` não cobre a chamada de síntese**
- **Encontrado em:** Task 2, ao desenhar a assinatura real de `sintetizar`.
- **Problema:** o `<interfaces>` do plano tipa `agente: AnalysisAgent`, mas `sysdoc_dvi.tipos.AnalysisAgent` (frozen, `Protocol` com `executar_item(item: ItemChecklist, contexto: str)`/`executar_lote`) só expressa chamadas amarradas a um `ItemChecklist` real do checklist. A síntese não tem um `ItemChecklist` associado (é uma chamada de prompt livre, no alvo `"forte"`, sobre a lista inteira de itens já resolvidos) — não há como satisfazer "chama o agente no alvo forte" (Task 2, `<behavior>`) através de `executar_item`/`executar_lote` sem inventar um `ItemChecklist` fictício, o que none dos `tipo` mapeados por `AgenteLLM.TEMPLATE_POR_TIPO` (`presenca`/`julgamento`/`calculo`) cobriria de forma correta.
- **Decisão:** `sintese.py` define localmente um `Protocol AgenteSintese` com `.chamar(alvo: str, prompt: str, *, schema: dict | None = None) -> RespostaModelo` — mesma forma de retorno (`RespostaModelo`) e mesmo `alvo`/`prompt`/`schema` que `provedores.chamar_modelo` já usa, mas sem a amarração a `ItemChecklist`. `sysdoc_dvi.tipos.AnalysisAgent` **não foi tocado** (segue frozen, conforme instruído em `tipos.py`).
- **Impacto adiante:** o plano 05-14 (pipeline), que monta `agente = AgenteLLM(config, schemas_por_tipo=...)` e precisa passá-lo tanto para `despacho.executar_checklist` (que usa `AnalysisAgent.executar_item`) quanto para `sintese.sintetizar` (que usa `AgenteSintese.chamar`), vai precisar ou estender `AgenteLLM` com um método `.chamar` (chamando `provedores.chamar_modelo(alvo, prompt, schema=schema, timeout_s=self._config.timeout_s, max_retries=self._config.max_retries)`), ou envolvê-lo num adaptador fino. Isso é responsabilidade do plano 05-14, não deste plano (`agente.py` não está em `files_modified` de 05-10). Sinalizado aqui para visibilidade do próximo executor.

**2. [Rule 1 - plan bug documentado, não corrigido no artefato] Campo `item` da lista de campos reduzidos não existe em `ResultadoItem`**
- **Encontrado em:** Task 1, ao implementar a redução de itens descrita no `<action>` ("reduzida aos campos checklist_id, documento, seção, item, classificação, severidade, risco_jurídico, parecer").
- **Problema:** `sysdoc_dvi.tipos.ResultadoItem` (frozen, "não redefinir em outro módulo") não tem um campo `item` (título); esse campo só existe em `ItemChecklist.pergunta`, indisponível dentro de `sintetizar(itens: list[ResultadoItem], ...)`.
- **Ação:** o campo foi simplesmente omitido da redução — os 7 campos restantes (`checklist_id`, `documento`, `seção`, `classificação`, `severidade`, `risco_jurídico`, `parecer`) já identificam o item de forma suficiente para o modelo redigir o parecer. Nenhuma alteração em `tipos.py`.

**3. [Sequenciamento do plano, documentado, não corrigido no artefato] `<verify>` da Task 1 referenciava `tests/test_dvi_sintese.py` antes de o arquivo existir**
- Ver "Task 3" em "What Was Built" acima — mesma classe de problema já registrada no SUMMARY do plano 05-01. A suíte completa (14 testes, todas as classes exigidas por Task 3) foi criada no commit RED da Task 2 (tdd="true") e cobre integralmente o que as Tasks 1 e 3 pediam; a Task 1 foi verificada por seus critérios de aceitação literais (greps + smoke test Python) em vez do comando `pytest` prematuro.

### Nenhuma outra alteração fora do escopo do plano.

## Known Stubs

Nenhum. `sintese.py` é funcional ponta a ponta contra os testes com `AgenteFalso` e contra uma verificação manual com `templates/validate_sysdoc.py`. A integração real com `AgenteLLM` (produção) depende do plano 05-14 conforme documentado no Desvio 1.

## Threat Flags

Nenhuma superfície nova fora do `<threat_model>` do plano. As três mitigações registradas (T-05-33, T-05-34, T-05-35) estão implementadas: itens reduzidos a campos estruturados antes de qualquer prompt de síntese, sem `de`/`para`/`fundamento`/texto de peça (T-05-33); `classificação_documento` sempre calculada localmente por `classificar_documento`, nunca aceita do modelo, e os templates proíbem explicitamente citar norma/valor/data fora dos itens recebidos (T-05-34); verificação local de palavras com o mesmo regex do validador, um retry, e `ErroSintese` — nenhum parecer abaixo do mínimo é devolvido ao chamador (T-05-35).

## Self-Check: PASSED

- FOUND: sysdoc_dvi/sintese.py
- FOUND: sysdoc_dvi/prompts/sintese_executivo.jinja
- FOUND: sysdoc_dvi/prompts/sintese_documento.jinja
- FOUND: tests/test_dvi_sintese.py
- FOUND commit: 9663e0e (feat(05-10): add sintese templates and deterministic document classification)
- FOUND commit: c184e49 (test(05-10): add failing test suite for sintetizar() RF6 behavior)
- FOUND commit: e0c4df0 (feat(05-10): implement sintetizar() with retry-once minimum enforcement)

## TDD Gate Compliance

Task 2 (`tdd="true"`): RED confirmado (`ImportError: cannot import name 'sintetizar' from 'sysdoc_dvi.sintese'` antes da implementação, commit `c184e49`) → GREEN confirmado (14/14 testes passando após a implementação, commit `e0c4df0`). Nenhum commit `refactor` necessário — implementação não exigiu limpeza adicional após o GREEN.
