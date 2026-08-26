---
phase: 05-motor-analise-checklist
plan: 08
subsystem: motor-dvi/provedores
tags: [llm, multi-provedor, requests, agente, structured-output, prompt-caching]
dependency-graph:
  requires: ["05-01"]
  provides:
    - "sysdoc_dvi/config.py: carregar_config_dvi, chave_do_provedor, carregar_precos_dvi, ConfigDvi, ErroConfiguracaoModelos"
    - "sysdoc_dvi/provedores.py: chamar_modelo, RespostaModelo, ErroProvedor, PROVEDORES, REGISTRO_CHAMADAS"
    - "sysdoc_dvi/agente.py: AgenteLLM, TEMPLATE_POR_TIPO"
  affects:
    - "sysdoc_dvi/cli.py (plano futuro liga `config`/`run` a esta camada)"
    - "05-11 (relatório de execução consome REGISTRO_CHAMADAS)"
    - "05-14 (despacho injeta schemas_por_tipo em AgenteLLM)"
tech-stack:
  added: ["requests (já era dependência do projeto)"]
  patterns:
    - "Um adaptador por provedor em um dicionário (PROVEDORES); acrescentar provedor = uma entrada + uma função, sem tocar em chamar_modelo"
    - "Chave de API lida só no momento da chamada (chave_do_provedor), nunca em dataclass nem em mensagem de erro"
    - "Degradação para pendente em vez de exceção propagada (D-17)"
key-files:
  created:
    - sysdoc_dvi/config.py
    - sysdoc_dvi/provedores.py
    - sysdoc_dvi/agente.py
    - tests/test_dvi_provedores.py
  modified: []
decisions:
  - "Cache tokens (tokens_cache_leitura/tokens_cache_escrita) vivem em RespostaModelo, não em UsoModelo — tipos.py é contrato estável do plano e não foi tocado"
  - "Tabela de preços (dvi.precos) é lida diretamente do config.json por provedores.py via config.carregar_precos_dvi, já que ConfigDvi (interface travada do plano) não carrega preços"
  - "prefixo_cacheavel para providers sem suporte a cache é concatenado como texto simples ao prompt (sem mensagem system extra), evitando qualquer campo novo no payload"
  - "Autenticação Gemini via header x-goog-api-key em vez de query string ?key=, para nunca expor a chave em URL/logs"
  - "REGISTRO_CHAMADAS é uma lista module-level acumulada a cada chamar_modelo bem-sucedida, servindo de insumo bruto para o relatório do plano 05-11 (formato interno é discrição do executor, plano não travou nomes de campo)"
metrics:
  duration: "~35 min"
  completed: "2026-08-26"
  tasks_completed: 3
  tasks_total: 3
  files_created: 4
  tests_added: 31
  tests_total_suite: 147
---

# Phase 5 Plan 08: Camada de provedores multi-modelo e AgenteLLM Summary

Cliente HTTP multi-provedor (OpenRouter/OpenAI/Gemini/Anthropic) com saída estruturada, retry único, medição de uso e prompt caching seletivo, mais o `AgenteLLM` de referência do protocolo `AnalysisAgent` — 31 testes novos com HTTP inteiramente simulado.

## What Was Built

**Task 1 — `sysdoc_dvi/config.py`:** `carregar_config_dvi(economico=None, forte=None, config_path=None)` lê `~/.sysdoc/config.json` (resolvido via `Path.home()` a cada chamada, para respeitar `HOME` monkeypatchado em teste). Sem arquivo, sem `economico`/`forte`, alvo fora do formato `provedor/modelo`, provedor não suportado, ou chave de API ausente — todos levantam `ErroConfiguracaoModelos` com o remédio embutido na mensagem (o JSON de exemplo completo e/ou a variável de ambiente aceita como alternativa). `chave_do_provedor(provedor)` é a única função que lê credenciais, com fallback para `OPENROUTER_API_KEY`/`OPENAI_API_KEY`/`GEMINI_API_KEY`/`ANTHROPIC_API_KEY`; nunca aparece em `ConfigDvi`, `__repr__` ou mensagem de erro. `carregar_precos_dvi()` expõe a seção `dvi.precos` para `provedores.py`.

**Task 2 — `sysdoc_dvi/provedores.py`:** `PROVEDORES` mapeia `openrouter`/`openai`/`gemini`/`anthropic` a um `AdaptadorProvedor(suporta_cache, executar)`. Cada `_executar_<provedor>` monta URL/headers/payload, chama `requests.post(..., timeout=timeout_s)` (sem `verify=False`, nunca), e extrai `(conteudo_bruto, tokens_entrada, tokens_saida, tokens_cache_leitura, tokens_cache_escrita)`. OpenRouter e OpenAI usam `response_format: json_schema`; Anthropic usa `system` como lista de blocos com instrução JSON (sem `response_format`); Gemini usa `generateContent` com `responseMimeType`/`responseSchema`. `chamar_modelo` faz o dispatch por `provedor/modelo`, tenta uma vez, e — se o JSON vier inválido — repete exatamente uma vez com o erro de parsing anexado ao prompt; falha persistente levanta `ErroProvedor` sem cabeçalhos de auth na mensagem. Cache de prompt: `prefixo_cacheavel` chega intacto a todo adaptador; só o Anthropic marca o bloco com `cache_control: {"type": "ephemeral"}` e lê `cache_read_input_tokens`/`cache_creation_input_tokens`; os demais concatenam o prefixo ao prompt como texto comum, sem exceção e sem campo extra. Cada chamada bem-sucedida é registrada em `REGISTRO_CHAMADAS` (provedor, modelo, tokens, tokens de cache, custo, duração — sem prompt, sem resposta bruta) para o relatório do plano 05-11.

**Task 3 — `sysdoc_dvi/agente.py` + `tests/test_dvi_provedores.py`:** `AgenteLLM` é dono de `TEMPLATE_POR_TIPO` (`presenca→item_presenca`, `julgamento→item_julgamento`, `calculo→extracao_precos`). `executar_item` resolve o template pelo `item.tipo`, seleciona `config.economico`/`config.forte` por `item.modelo_alvo`, monta o prompt via `montar_prompt` injetável (default tardio para `sysdoc_dvi.prompts.montar_prompt`, ainda não criado — chega no plano 05-09) e chama `provedores.chamar_modelo` com `prefixo_cacheavel` = instrução fixa do agente + `item.base_legal_texto` (nunca o `contexto`/peça analisada). `item.tipo` fora do mapa (`vigencia`, `mecanica`) e falha de provedor após o retry embutido ambos degradam para `ResultadoItem` `pendente` com `falha_estruturada`, nunca uma exceção propagada. `executar_lote` itera `executar_item` reaproveitando o mesmo contexto. A suíte de testes cobre `TestConfig`, `TestAdaptadores`, `TestRetry`, `TestSegredo`, `TestUso`, `TestCache` e `TestAgente` (31 testes), com um fixture `autouse` que faz `requests.post` levantar `AssertionError` a menos que o próprio teste injete seu substituto.

## Verification

- `python -m pytest tests/ -q` → **147 passed** (31 novos em `test_dvi_provedores.py`, 0 regressões).
- `python -m pytest tests/test_dvi_provedores.py -k Config -q` → 10 passed (Task 1 verify).
- Acceptance greps: `verify=False` → 0; `timeout=` → 4; `print(...chave|api_key)` → 0; `PROVEDORES` → `['anthropic', 'gemini', 'openai', 'openrouter']`; `cache_control` → 1; `suporta_cache` → 5; `temperature` → 4; `class AgenteLLM` → 1; `TEMPLATE_POR_TIPO` mapping asserted via `python -c`.
- `grep -rn "api_key|API_KEY" sysdoc_dvi/ | grep -i "print|log"` → vazio.
- `grep -rn "requests" sysdoc.py` → vazio (CLI determinística segue sem cliente HTTP).
- `HOME` apontando para pasta vazia → `carregar_config_dvi()` levanta erro citando `economico` e `config.json`.

## Deviations from Plan

None — plan executed exactly as written. Two implementation choices were left to discretion (explicitly granted by the plan's "Claude's Discretion" / internal field naming):

1. Cache token counts (`tokens_cache_leitura`/`tokens_cache_escrita`) were added as extra fields on `RespostaModelo` (created fresh in this plan) instead of on `UsoModelo` (the phase's stable, cross-plan contract in `tipos.py`, explicitly marked "não redefinir" and out of this plan's `files_modified`).
2. The per-call serializable record for the future 05-11 execution report is accumulated automatically in a module-level `REGISTRO_CHAMADAS` list inside `chamar_modelo`, rather than requiring the caller to build it manually — matches the plan's "Registrar em cada chamada" wording literally.

## Known Stubs

None. All three modules are fully functional against their documented interfaces; no hardcoded empty values or "coming soon" placeholders. `AgenteLLM`'s default `montar_prompt` does a **lazy import** of `sysdoc_dvi.prompts.montar_prompt`, which does not exist yet (arrives in plan 05-09) — this is intentional per the plan's own text ("os templates só existem a partir do plano 05-09... os testes desta task injetam um duplo") and is exercised only via the injectable `montar_prompt` parameter in all current tests, never via the lazy-import default path. Not a stub in the sense of hiding missing behavior — it is the documented seam for a not-yet-built downstream plan.

## Threat Flags

None. All new network/auth surface (4 provider HTTP adapters, API key handling) was explicitly anticipated and dispositioned in the plan's own `<threat_model>` (T-05-24 through T-05-28) and mitigated as specified: keys read only at call time and never logged/repr'd/exceptioned (T-05-24); fixed URLs per adapter, default TLS verification, no `verify=False` (T-05-25); strict JSON parsing with one retry then graceful `pendente` degradation, no `eval`/`exec` (T-05-26); explicit `timeout_s` on every adapter call, `max_retries` capped (T-05-27); cacheable prefix restricted to fixed instructions + public `base_legal_texto`, verified by `test_prefixo_cacheavel_nao_inclui_contexto_da_peca` (T-05-28, accept-disposition already covers the send-to-provider surface itself).

## Self-Check: PASSED

- FOUND: sysdoc_dvi/config.py
- FOUND: sysdoc_dvi/provedores.py
- FOUND: sysdoc_dvi/agente.py
- FOUND: tests/test_dvi_provedores.py
- FOUND commit: ece0d14 (feat(05-08): add DVI model config loader with instructive abort)
- FOUND commit: ed368cf (feat(05-08): add multi-provider HTTP client with structured output and usage metering)
- FOUND commit: 33409ba (feat(05-08): add AgenteLLM reference AnalysisAgent and mocked-HTTP test suite)
