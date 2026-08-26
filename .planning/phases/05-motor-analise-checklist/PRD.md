# PRD — Fase 05: Motor de análise por checklist com agentes plugáveis

> Destino: `.planning/phases/05-motor-analise-checklist/`
> Status: rascunho para aprovação
> Data: 2026-08-26
> Release alvo: a definir (ver Decisões em aberto, D1)

---

## 1. Contexto e problema

O SysDoc já resolve extração determinística, contrato de dados (`schema_sysdoc.json`), validação com rastreabilidade literal (campo `de`), renderização imutável e deploy. A camada de análise (camada 2), porém, tem quatro limitações estruturais:

1. A análise depende de um harness agêntico operado manualmente (Claude Code, OpenCode etc.), que lê o cache inteiro e produz o `dados_consolidados.json` completo em uma única sessão. Esse formato exige modelo forte, não é reprodutível em lote e não cabe em um fluxo web futuro.
2. O conhecimento de negócio da análise DVI vive em dois prompts monolíticos externos ao repositório (processos gerais e TIC), com ~50 verificações heterogêneas misturadas. Manutenção significa editar texto corrido; não há tipagem, roteamento nem reuso entre os dois.
3. Verificações que não deveriam passar por LLM passam: auditoria aritmética de médias/medianas, vigência de normativos e checagens mecânicas (numeração sequencial, presença de CATMAT/CATSER). São os pontos de maior taxa de erro do fluxo atual.
4. A saída DVI em DOCX não existe; `sysdoc create` cobre apenas TR revisado.

Requisitos do dono do produto para esta fase: **fácil manutenção** (regras de negócio como dados versionados, nunca como prompt ou código espalhado) e **fácil acoplamento de agentes** (qualquer modelo ou harness deve conseguir executar a análise e produzir o mesmo artefato validável).

## 2. Objetivo da fase

Entregar um motor de análise dirigido por checklist tipado e data-driven, executável por um orquestrador via API (modelos econômicos onde couber) ou por qualquer harness agêntico, com verificações determinísticas em Python para tudo que não exige julgamento, produzindo o mesmo `dados_consolidados.json` validado de hoje e, ao final, o DVI em DOCX via `sysdoc create dvi`. A CLI determinística preserva integralmente o contrato atual: nenhum comando dela chama modelo de linguagem.

## 3. Requisitos funcionais

**RF1 — Checklist tipado e data-driven.** Os dois prompts DVI são convertidos em arquivos `checklists/*.yaml` versionados no repositório. Cada item declara: `id`, `aplicabilidade` (`geral` | `tic` | `ambos`), `peca` (`ETP` | `TR` | `MCP` | `RISCOS` | `PROCESSO`), `tipo` (`presenca` | `julgamento` | `calculo` | `vigencia` | `mecanica`), `pergunta`, `base_legal_texto` (transcrição literal do dispositivo aplicável), `referencia` (identificação da norma/acórdão), `severidade_default`, `modelo_alvo` (`economico` | `forte`) e `ativo`. Adicionar, editar ou desativar um item não exige alteração de código.

**RF2 — Roteamento geral/TIC.** A aplicabilidade da análise (geral ou TIC) é declarada no `.sysdoc/config.yaml` do projeto ou por argumento de linha de comando. O motor filtra os itens por `aplicabilidade` e `ativo`.

**RF3 — Mapeamento de peças.** O motor localiza ETP, TR, MCP e Mapa de Riscos nos textos extraídos por âncoras textuais registradas no `manifest.json`, com override manual no config (`pecas: {etp: arquivo.pdf, ...}`). Peça obrigatória não localizada e sem override aborta a execução com mensagem explícita — nunca análise em contexto errado.

**RF4 — Despacho por tipo de verificação.**
- `presenca` e `julgamento`: chamadas a LLM com saída estruturada (JSON parcial conforme schema), temperatura 0, contexto restrito à peça relevante (nunca o processo inteiro). Itens de `julgamento` só podem fundamentar em `base_legal_texto` fornecido no prompt; citação de norma ou acórdão fora da base fornecida é violação e reclassifica o item como `pendente`.
- `calculo`: a LLM apenas extrai a tabela de dados (fontes, valores unitários, quantidades, valor declarado) em schema fechado; funções Python puras recalculam média, mediana e unitário × quantidade e comparam com o declarado, com tolerância configurável. Divergência gera apontamento com memória de cálculo produzida pelo próprio motor.
- `vigencia`: lookup determinístico na tabela curada de normas (RF7). O modelo nunca responde vigência de memória.
- `mecanica`: funções Python puras sobre o texto extraído (numeração sequencial por peça, presença de códigos CATMAT/CATSER, menção × presença de cronograma físico-financeiro). Verificações de formatação visual (margens, fonte, espaçamento) ficam fora do escopo do texto extraído; item opcional futuro sobre o DOCX original.

**RF5 — Grounding check.** Todo item produzido por LLM com veredicto diferente de `pendente` deve trazer o campo `de` com trecho literal. O motor valida a existência do trecho no texto extraído da peça indicada (normalização leve + correspondência aproximada com limiar configurável) antes de aceitar. Falha de grounding reclassifica o item como `pendente` e registra o evento no relatório de execução. O marcador `[OMISSÃO]` segue a convenção já existente do schema.

**RF6 — Síntese dedicada.** `parecer_executivo` e `parecer_documento` não são redigidos item a item: uma chamada final de síntese (modelo forte) recebe exclusivamente os itens já validados e produz os pareceres. Isso preserva os mínimos de palavras do validador (450/120) sem induzir enchimento nos modelos econômicos que executam os itens.

**RF7 — Tabela de vigência de normativos.** Arquivo `normas/vigencia.yaml` versionado no repositório (override por projeto em `referencias/`), com entradas `{norma, status, substituida_por, conferida_em}`, mantido manualmente. Norma citada no documento e ausente da tabela gera item `pendente` com a mensagem "norma não catalogada" — nunca consulta ao modelo. Regras institucionais pontuais (ex.: substituição da Portaria PRES CFC 266/2025 pela Resolução CFC 1.799/26) entram nesta tabela ou como item de checklist, nunca em prompt.

**RF8 — Acoplamento de agentes em dois níveis.**
- *Nível artefato (já existente, formalizado):* qualquer agente que leia `.sysdoc/cache/` + `checklists/*.yaml` e escreva `dados_consolidados.json` aprovado pelo `sysdoc validate` está acoplado. O fluxo harness atual permanece válido; `skills/sysdoc/SKILL.md` passa a declarar o YAML como fonte canônica dos itens de análise.
- *Nível código:* protocolo Python `AnalysisAgent` com contrato mínimo (`executar_item(item, contexto) -> ResultadoItem`, opcionalmente `executar_lote`). Implementação de referência: cliente da API Anthropic com seleção de modelo por `modelo_alvo`. Adicionar um provedor = um módulo novo + uma entrada de configuração. O orquestrador em si é um agente de nível artefato: produz o mesmo JSON que um harness produziria.

**RF9 — Relatório de execução.** Cada análise gera relatório com: itens por status e por tipo, falhas de grounding, tokens e custo estimado por modelo, duração, hash do checklist utilizado. O hash do checklist e a `schema_version` entram nos `metadados` do JSON consolidado para auditoria.

**RF10 — Saída DVI.** Novo tipo em `sysdoc create dvi`: gera DOCX a partir de template institucional em `referencias/`, preenchido com os itens consolidados e pareceres, seguindo o padrão de nomenclatura existente (`dvi_[modelo]_[data].docx`). A revisão humana ocorre sobre o JSON/HTML antes do `create`; o DOCX é minuta para assinatura, nunca documento final automático.

## 4. Fora de escopo desta fase

Interface web de upload e revisão (fase seguinte, consumirá o motor como biblioteca). Segmentação automática sofisticada de peças (âncoras + override manual bastam). Base ampla de jurisprudência ou RAG (apenas os entendimentos já curados nos checklists, ex.: Acórdão TCU 1.872/2018-Plenário). Autenticação, multiusuário e fila de processamento. Verificação de formatação visual de documentos.

## 5. Arquitetura da fase

```
checklists/*.yaml ──┐
normas/vigencia.yaml┤
.sysdoc/cache/ ─────┴─> ORQUESTRADOR (novo entry point, ver D2)
                          ├─ mapeia peças (manifest + âncoras + override)
                          ├─ despacha itens por tipo:
                          │    presenca/julgamento -> AnalysisAgent (LLM, temp 0, schema parcial)
                          │    calculo  -> extração LLM + funções puras
                          │    vigencia -> lookup vigencia.yaml
                          │    mecanica -> funções puras
                          ├─ grounding check (campo `de`)
                          ├─ síntese (pareceres, modelo forte)
                          └─ monta dados_consolidados.json + relatório
                                   │
                 CLI determinística (inalterada, sem LLM)
                 sysdoc validate -> publish/render -> create dvi -> deploy
```

Princípio preservado: a CLI `sysdoc` continua sem qualquer chamada a modelo de linguagem. O orquestrador é um binário/entry point próprio que pertence à camada 2 e usa a CLI existente como biblioteca para validação e renderização.

## 6. Requisitos não funcionais

**RNF1 — Manutenção.** Nenhuma regra de negócio em prompt hardcoded ou código de aplicação: itens no YAML, dispositivos legais como texto literal dentro dos itens, vigência na tabela curada. Prompts são templates curtos (Jinja) que recebem item + contexto. Trocar uma norma = editar YAML + rodar testes.

**RNF2 — Reprodutibilidade.** Temperatura 0 em todas as chamadas; versionamento de JSON por modelo + data (existente); hash do checklist nos metadados; `sysdoc compare` permite confrontar execuções de agentes distintos sobre o mesmo processo.

**RNF3 — Custo.** Itens `presenca` e a extração de `calculo` executáveis em modelo econômico (Haiku); `julgamento` e síntese em modelo forte. Contexto por chamada restrito à peça. Prompt caching para checklist e base legal quando o provedor suportar. Custo por processo é medido e registrado no relatório desde a primeira execução (baseline da fase, sem meta numérica a priori).

**RNF4 — Testabilidade.** Pytest cobrindo: funções de cálculo e comparação, lookup de vigência, verificações mecânicas, grounding check e validação de coerência dos novos campos. Fixture com processo sintético contendo erros plantados. Integra-se à suíte existente (`tests/`).

**RNF5 — Compatibilidade.** `dados_consolidados.json` gerado pelo motor passa no `sysdoc validate` vigente. Campos novos por item (`origem_verificacao: llm|deterministico|lookup`, `checklist_id`) e de metadados (`checklist_hash`, `schema_version`) entram como evolução retrocompatível do schema, com testes atualizados. `templates/validate_sysdoc.py` e `render_analise.py` permanecem imutáveis durante uma análise; evoluem apenas entre versões, com CHANGELOG.

## 7. Critérios de aceite

1. Um processo real de contratação geral e um de TIC analisados de ponta a ponta pelo orquestrador; ambos os JSONs aprovados pelo `sysdoc validate` sem edição manual.
2. Bateria de erros plantados em MCP sintético (média incorreta, mediana incorreta, unitário × quantidade divergente): detecção de 100% dos erros, zero falso negativo, com memória de cálculo no apontamento.
3. Item com trecho `de` fabricado em teste controlado é rejeitado pelo grounding check e reclassificado como `pendente`, com registro no relatório.
4. Editar um item do YAML (texto, severidade, desativação) altera o resultado da análise sem qualquer mudança de código.
5. O mesmo processo analisado por dois agentes distintos (orquestrador via API + harness Claude Code lendo o mesmo checklist) produz JSONs válidos comparáveis via `sysdoc compare`.
6. Itens de vigência respondem exclusivamente pela tabela; norma não catalogada resulta em `pendente`, comprovado por teste.
7. `sysdoc create dvi` gera DOCX válido a partir de template institucional em `referencias/`.
8. Relatório de execução emitido com custo, tokens, duração e contagens por status/tipo; taxa de falha de grounding do modelo econômico registrada como baseline.

## 8. Riscos e mitigações

1. **Mapeamento de peça incorreto** → análise no contexto errado. Mitigação: abort obrigatório quando peça esperada não é localizada (RF3) + override manual + teste de âncoras.
2. **Latência e custo de N chamadas pequenas.** Mitigação: contexto mínimo por chamada, lotes por peça quando itens compartilham contexto, prompt caching, medição desde a primeira execução (CA8) antes de otimizar.
3. **Drift entre checklist YAML e SKILL.md.** Mitigação: SKILL.md referencia o YAML como fonte canônica; wrappers não duplicam itens.
4. **Mínimos de palavras do validador induzindo enchimento.** Mitigação principal: síntese dedicada (RF6). Alternativa registrada: relaxar mínimos por configuração em versão futura do validador.
5. **Tabela de vigência desatualizada** (humano no loop por design). Mitigação: campo `conferida_em` exibido no relatório; item de rotina operacional, não de software.

## 9. Decisões em aberto (aprovação do dono)

**D1 — Versionamento.** A CLI está em 1.4.0 e as discussões chamam esta entrega de "v0.2.0". Definir se v0.2.0 nomeia o produto de análise DVI ou se a fase sai como SysDoc 1.5.0.

**D2 — Entry point do orquestrador.** Recomendado: executável separado (`sysdoc-agent run [pasta]`), preservando à letra o contrato "nenhum comando da CLI chama LLM". Alternativa: subcomando `sysdoc analyze --run`, que exigiria reescrever essa restrição na documentação.

**D3 — Local da tabela de vigência.** Recomendado: global no repositório (`normas/vigencia.yaml`) com override por projeto em `referencias/`. Alternativa: exclusivamente por projeto.

**D4 — Nomenclatura.** Confirmar nomes dos tipos de verificação e dos campos novos do schema antes da implementação, pois congelam no contrato de dados.

## 10. Impacto nos artefatos existentes

| Artefato | Impacto |
|---|---|
| CLI `sysdoc` (todos os comandos) | Inalterada; ganha `create dvi` |
| `templates/schema_sysdoc.json` | Evolução retrocompatível (campos novos + `schema_version`) |
| `templates/validate_sysdoc.py` | Evolução entre versões, com testes; imutável durante análise |
| `templates/render_analise.py` | Sem alteração prevista |
| `skills/sysdoc/SKILL.md` | Atualizado: checklist YAML como fonte canônica dos itens |
| `AGENTS.md` / wrappers | Atualizados para apontar o checklist e o fluxo por itens |
| Novos | `checklists/*.yaml`, `normas/vigencia.yaml`, pacote do orquestrador, template DVI, testes |
