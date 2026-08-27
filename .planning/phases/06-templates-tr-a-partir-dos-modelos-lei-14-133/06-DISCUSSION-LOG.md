# Phase 6: Templates de documentos institucionais - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-26
**Phase:** 6-Templates de documentos institucionais (rodada 1: Despacho de Verificação Inicial)
**Areas discussed:** Escopo da fase (repactuação), Corpo dos apontamentos, Local e precedência

---

## Escopo da fase — repactuação

Áreas apresentadas inicialmente, derivadas do escopo TR do ROADMAP:

| Opção | Descrição | Selecionada |
|--------|-------------|----------|
| Escopo dos templates | Quantos templates e quais categorias, dado que só há 3 modelos distintos contra 4 categorias em `_detect_procurement_category` | |
| Autoria dos placeholders | Script gerador × edição manual no Word × injeção em tempo de render | |
| Precedência de templates | `templates/tr/` antes de `referencias/` × decisão da Phase 2 | |
| O que o TR gerado contém | Blanks oficiais, corpo do ETP, itens da análise | |

**Escolha do usuário (texto livre):** *"O template nesta fase contemplará apenas o Despacho de Verificação Inicial. Depois vamos criar o TR e o ETP. Vai ficar a fase aberta."*

**Notas:** Redefinição de escopo pelo dono do produto, não scope creep — o ROADMAP Phase 6 ficou desatualizado e precisa ser reescrito. Os achados do scout sobre os modelos de TR (duplicata byte-idêntica, terceiro modelo é Termo de Contrato, descasamento 4×3) foram preservados em CONTEXT.md § Deferred Ideas para a rodada seguinte.

Segunda rodada de áreas, já sobre o DVI:

| Opção | Descrição | Selecionada |
|--------|-------------|----------|
| Corpo dos apontamentos | Como gerar `1) ETP (SEI xxx) / a) subitem 4.20: …` dentro do DOCX | ✓ |
| Campos institucionais | Vocativo, signatário, unidade, destinatário, nº SEI por peça | |
| Fidelidade ao despacho | Substituir, manter os dois formatos, ou anexar relatório | |
| Local e precedência | Onde vive o template e quem ganha o override | ✓ |

**Escolha do usuário:** Corpo dos apontamentos + Local e precedência, com a observação livre: *"O Despacho na verdade é um documento que aponta para a UO a necessidade de correção. Então é importante ter um check-list para o modelo compreender o que deve ser visto. No DVI deve conter TÃO SOMENTE que tem de ser ajustado."*

**Notas:** Essa observação virou regra governante do template (CONTEXT.md § Phase Boundary) e contradiz o `build_tabela_itens()` atual, que inclui itens `conforme`.

---

## Corpo dos apontamentos

### Quais itens entram no corpo do despacho?

| Opção | Descrição | Selecionada |
|--------|-------------|----------|
| Tudo que não é conforme | `ajuste_necessário` + `risco` + `pendente` na mesma numeração por peça | |
| Não-conformes + seção de ausências | `ajuste_necessário` + `risco` por peça; pendências por documento ausente/ilegível em seção própria ao final | ✓ |
| Só ajuste e risco | `pendente` fora do despacho por completo | |

**User's choice:** Não-conformes + seção de ausências.

### Como montar `1) ETP (SEI xxx) / a) subitem 4.20: …` dentro do DOCX?

| Opção | Descrição | Selecionada |
|--------|-------------|----------|
| Builder emitindo XML de parágrafo | `<w:p>` completos com estilos nomeados, injetados em placeholder raw sem escape | ✓ (Claude) |
| Texto plano num placeholder | `\n → <w:br/>`, zero mudança no renderer, mas estilo único | |
| Repetição de parágrafo-modelo | Clonagem de parágrafos marcados no DOCX; exige mecanismo de loop novo | |

**User's choice:** "Você escolhe" → Claude escolheu builder emitindo XML de parágrafo.
**Notas:** Critério: preservar negrito no título de peça e recuo das alíneas sem mexer na lógica de clonagem de `render_docx_template()`, que é compartilhada com o fluxo do TR. Consequência de segurança registrada como D-09 (allowlist explícita para o bypass de `xml_escape`).

### As seções numeradas por peça são dinâmicas ou fixas?

| Opção | Descrição | Selecionada |
|--------|-------------|----------|
| Dinâmicas, só com apontamento | Renumeradas 1), 2), 3) na ordem canônica das peças | ✓ |
| Fixas pelo checklist | Toda peça prevista ganha seção, com "Sem apontamentos." | |
| Dinâmicas + nota de cobertura | Só peças com achado, mas Observações listam o que foi verificado | |

**User's choice:** Dinâmicas, só com apontamento.

### O que entra no texto de cada alínea?

| Opção | Descrição | Selecionada |
|--------|-------------|----------|
| parecer + fundamento | Análise em prosa + base normativa, sem sugerir redação | ✓ |
| parecer + fundamento + redação sugerida | Acrescenta o campo `para` como "Sugere-se a seguinte redação:" | |
| Só parecer | `fundamento` fica só no HTML/JSON | |

**User's choice:** parecer + fundamento.

### Como tratar o mesmo apontamento repetido entre peças?

| Opção | Descrição | Selecionada |
|--------|-------------|----------|
| Referência cruzada automática | "Vide apontamento constante na alínea 'a' do item 1 do presente documento." | ✓ |
| Repetir o texto completo | Determinístico e simples, despacho mais longo | |
| Motor decide, template obedece | Dedup em `sysdoc_dvi`, texto já pronto no campo `parecer` | |

**User's choice:** Referência cruzada automática.
**Notas:** Implica resolver a numeração de peças e alíneas **antes** de renderizar o texto das alíneas.

---

## Local e precedência

### Onde vive o novo template do despacho?

| Opção | Descrição | Selecionada |
|--------|-------------|----------|
| `templates/dvi/` (pasta nova) | Abre espaço para variantes e prepara `templates/tr/` | ✓ (Claude) |
| Substituir `templates/dvi_base.docx` | Mesmo caminho, novo conteúdo | |
| Só no projeto, sem base no repo | Cada órgão traz o seu em `referencias/dvi.docx` | |

**User's choice:** "Você escolhe" → Claude escolheu `templates/dvi/`.
**Notas:** Decidido depois da resposta "um template por tipo" — com dois arquivos, pasta própria é a única opção que não polui a raiz de `templates/`.

### O projeto tem seu próprio `referencias/dvi.docx`. Quem ganha?

| Opção | Descrição | Selecionada |
|--------|-------------|----------|
| Projeto ganha (comportamento atual) | Preserva a decisão da Phase 2 e o override sem tocar no repo | ✓ |
| Repo ganha, projeto só via `--template` | Garante formato canônico, tira o override silencioso | |
| Projeto ganha, mas avisa | Mantém override e imprime aviso | |

**User's choice:** Projeto ganha (comportamento atual).

### O DOCX é versionado no git ou gerado por script?

| Opção | Descrição | Selecionada |
|--------|-------------|----------|
| Gerado por script (padrão atual) | Evoluir `build_dvi_base.py`; diff auditável, ZIP byte-estável | ✓ |
| DOCX commitado, editado no Word | Sem programar, mas diff opaco e placeholders quebráveis | |
| Script gera, DOCX commitado, teste guarda | Ambos, com teste de regeração byte a byte | |

**User's choice:** Gerado por script.

### O despacho muda por tipo (`geral`/`tic`)?

| Opção | Descrição | Selecionada |
|--------|-------------|----------|
| Um template só | O tipo já muda o checklist; a moldura é a mesma | |
| Um template por tipo | `despacho_geral.docx` + `despacho_tic.docx` | ✓ |
| Um template, observações por tipo | Moldura única, bloco "Observações" vindo do checklist | |

**User's choice:** Um template por tipo.

### Como `sysdoc create <pasta> dvi` decide qual variante usar?

| Opção | Descrição | Selecionada |
|--------|-------------|----------|
| Lê `.sysdoc/config.yaml` | Mesma fonte de `pipeline.py:284`; sem flag nova, sem mudança de contrato | ✓ |
| Registrar no `dados_consolidados.json` | Contrato 1.2; DOCX reproduzível do JSON sozinho | |
| Flag explícita no create | `--verificacao tic`, com config como fallback | |

**User's choice:** Lê `.sysdoc/config.yaml`.

---

## Claude's Discretion

- Mecanismo de montagem do corpo (D-08): builder emitindo XML de parágrafo.
- Local do template (D-11): `templates/dvi/`.
- Ordem das alíneas dentro da peça: ordem do documento analisado, como no modelo real.
- Nome do módulo builder: evitar `despacho` (colisão com `sysdoc_dvi/despacho.py`, que é dispatch por tipo de verificação).

## Áreas não discutidas (viraram Open Decisions)

Perguntado ao final se queria discutir agora ou deixar como recomendação — usuário escolheu **"Pronto para o CONTEXT.md"**.

- **Campos institucionais** — vocativo, signatário, unidade, destinatário, nº SEI por peça, boilerplate "Observações". Recomendação registrada: bloco `despacho:` em `.sysdoc/config.yaml`.
- **Destino do formato relatório atual** — `parecer_executivo`, `tabela_itens`, `nota_integridade`. Recomendação registrada: aposentar `templates/dvi_base.docx`, confirmando antes com o usuário porque o `init` o semeia.

## Deferred Ideas

- Templates de TR (4 categorias Lei 14.133) — rodada seguinte da mesma fase aberta, com os achados do scout preservados.
- Template de ETP — depois do TR.
- Revisão da pasta não rastreada `Referencias/` — reabrir quando a rodada de TR começar.
