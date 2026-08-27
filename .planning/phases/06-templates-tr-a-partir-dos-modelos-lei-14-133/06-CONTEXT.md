# Phase 6: Templates de documentos institucionais - Context

**Gathered:** 2026-08-26
**Status:** Ready for planning

<domain>
## Phase Boundary

**A fase foi repactuada pelo usuário durante esta discussão.** O ROADMAP descreve Phase 6 como "4 templates DOCX de TR derivados dos modelos Lei 14.133". O usuário redefiniu:

> "O template nesta fase contemplará apenas o Despacho de Verificação Inicial. Depois vamos criar o TR e o ETP. Vai ficar a fase aberta."

**Esta rodada entrega:** o template DOCX do **Despacho de Verificação Inicial (DVI)** em `templates/dvi/`, fiel ao modelo institucional real, alimentado pelo `dados_consolidados.json` produzido por `sysdoc-dvi run`, mais o builder determinístico que monta o corpo dos apontamentos e a seleção de template correspondente em `sysdoc create <pasta> dvi`.

**Rodadas seguintes desta mesma fase (fase fica aberta):** templates de TR (escopo original, 4 categorias Lei 14.133) e depois de ETP.

**Fora do escopo desta rodada:** qualquer template de TR ou ETP; mudança no motor de análise (`sysdoc_dvi/`) além do necessário para alimentar o documento; interface web (Phase 7).

### Natureza do documento (regra que governa todo o template)

> "O Despacho na verdade é um documento que aponta para a UO a necessidade de correção. Então é importante ter um check-list para o modelo compreender o que deve ser visto. **No DVI deve conter TÃO SOMENTE o que tem de ser ajustado.**"

O checklist (`checklists/dvi.yaml`) existe para o modelo saber o que olhar. O despacho materializa apenas o que a Unidade Demandante precisa corrigir — não é relatório de cobertura nem prestação de contas da análise.

</domain>

<decisions>
## Implementation Decisions

### Terminologia (correção de repo)

- **D-01:** DVI = **Despacho de Verificação Inicial**, não "Documento de Verificação Inicial". Confirmado pelo usuário e pelo modelo institucional real (`processo-teste/referencias/dvi.md`, linha 1: `DESPACHO DE VERIFICAÇÃO INICIAL - dvi`).
- **D-02:** A expansão errada está hoje em 9 pontos do repo e precisa ser corrigida nesta fase: `CLAUDE.md:42`, `AGENTS.md:33`, `README.md:360`, `README.md:450`, `checklists/dvi.yaml:3`, `skills/sysdoc/SKILL.md:45`, `.claude/skills/sysdoc-analise/SKILL.md:41`, `.opencode/skills/sysdoc-analise/SKILL.md:43`, `templates/build_dvi_base.py:50` (título do documento gerado). Também `tests/test_dvi_template_base.py:26` e `tests/test_dvi_autocorrecao.py:40` usam a expansão errada como fixture. Registrar no CHANGELOG referenciando a entrada `[1.5.x]` anterior, que fixou a expansão errada.

### Conteúdo do despacho

- **D-03:** Entram no corpo **apenas** itens `classificação ∈ {ajuste_necessário, risco}`, agrupados em seções por peça. `classificação=conforme` **nunca** aparece.
- **D-04:** Pendências por documento ausente/ilegível (`classificação=pendente`) **não** se misturam às alíneas: viram uma **seção própria ao final** (padrão do modelo real: *"3) CRONOGRAMA FÍSICO-FINANCEIRO: a) O ETP e o TR fazem menção ao Cronograma Físico-Financeiro, porém o documento não foi localizado nos autos."*).
- **D-05:** Seções por peça são **dinâmicas**: só entram peças com apontamento, renumeradas `1)`, `2)`, `3)` na ordem canônica das peças. Peça sem achado simplesmente não aparece.
- **D-06:** Texto de cada alínea = **`parecer` + `fundamento`**, em prosa contínua, no padrão do modelo real. O campo **`para` (redação sugerida) não entra no despacho** — o documento aponta a necessidade de correção, não redige pela UO.
- **D-07:** Apontamento repetido entre peças vira **referência cruzada automática**: *"b) Subitem 4.2: Vide apontamento constante na alínea 'a' do item 1 do presente documento."* Exige detectar itens equivalentes entre peças e resolver o rótulo (`item N`, `alínea x`) da alínea de destino em tempo de montagem — portanto a numeração precisa ser resolvida **antes** de renderizar o texto.

### Montagem do DOCX

- **D-08:** *(escolha delegada a Claude)* O corpo é montado por um **builder que emite XML de parágrafo**: gera `<w:p>` completos com estilos nomeados (título de peça, alínea recuada) injetados num **placeholder raw, sem escape**. Motivo: preserva formatação por parágrafo sem introduzir mecanismo de clonagem/loop em `render_docx_template()`, que é compartilhado com o fluxo do TR.
- **D-09:** **Segurança do placeholder raw:** `render_docx_template()` hoje aplica `xml_escape()` a todo valor (sysdoc.py:1271). O bypass deve ser uma allowlist explícita (ex.: chaves com sufixo `_xml`), e **só** XML gerado pelo builder pode passar por ele — texto vindo do JSON continua escapado, sempre.
- **D-10:** O template DOCX é **gerado por script** (padrão já estabelecido por `templates/build_dvi_base.py`): um parágrafo = um `<w:r><w:t>` para nenhum placeholder quebrar entre runs, `ZipInfo.date_time` fixo para regeração byte-estável.

### Local, precedência e variantes

- **D-11:** *(escolha delegada a Claude)* Templates vivem em **`templates/dvi/`** — pasta própria. Com dois arquivos por tipo, é a única opção que não polui a raiz de `templates/` e já estabelece o padrão que `templates/tr/` seguirá na rodada seguinte.
- **D-12:** **Um template por tipo de verificação:** `templates/dvi/despacho_geral.docx` e `templates/dvi/despacho_tic.docx`.
- **D-13:** `sysdoc create <pasta> dvi` resolve qual usar lendo **`tipo: geral|tic` de `.sysdoc/config.yaml`** — a mesma fonte que `pipeline.py:284` já usa (`tipo_efetivo = --tipo or config_projeto["tipo"]`), com mensagem de erro equivalente se ausente. Sem flag nova, sem mudança de contrato do JSON.
- **D-14:** **Precedência: o projeto ganha.** `<projeto>/referencias/dvi.docx` continua vencendo o template do repo — preserva a decisão da Phase 2 ("templates DOCX ficam em `referencias/`", PROJECT.md § Key Decisions) e mantém a customização por órgão sem tocar no repo. `seed_dvi_template()` (sysdoc.py:330) continua semeando só quando não há nenhum `.docx` com "dvi" no nome, mas agora precisa semear **a variante correspondente ao `tipo`** do projeto.

### Claude's Discretion

- **Ordem das alíneas dentro da peça:** ordem do documento analisado (subitem 4.20, 4.23, 4.24, 4.26.1, 4.30…), como no modelo real — não por severidade.
- **Nome do módulo builder:** **não** usar `despacho` — `sysdoc_dvi/despacho.py` já existe e significa *dispatch por tipo de verificação*, não o Despacho de Verificação Inicial. Colisão de nomes é armadilha real aqui.
- **Nome do script gerador:** `templates/build_dvi_base.py` evolui ou é substituído por `templates/build_despacho_templates.py`, a critério do planner, desde que o CHANGELOG registre.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Modelo institucional (fonte da verdade do formato)
- `processo-teste/referencias/dvi.md` — **o despacho real, completo**, referenciado pelo usuário. Define título, vocativo, parágrafo de contextualização, seções numeradas por peça com nº SEI, alíneas `a)` `b)` `c)`, referências cruzadas entre peças, bloco "Observações:", assinatura e o "De acordo" da autoridade. Todo o template deriva daqui.
- `processo-teste/01_processo-teste_dvi_2026-08-26.docx` e `02_…docx` — saídas atuais do `sysdoc create dvi`, para comparar formato antigo × novo.

### Motor DVI e contrato de dados
- `checklists/dvi.yaml` — fonte canônica dos itens, com aplicabilidade `geral|tic|ambos`. Nunca duplicar IDs, perguntas ou base legal fora dele.
- `templates/schema_sysdoc.json` — contrato do `dados_consolidados.json`. Campos que o template consome: `projeto.*`, `secao_etp.numero` / `secao_tr.numero` (nº SEI por peça, já obrigatórios), `itens[].{seção,parecer,fundamento,classificação,documento}`.
- `sysdoc_dvi/pipeline.py:284` — resolução canônica de `tipo geral|tic` a partir de `--tipo` ou `.sysdoc/config.yaml`.
- `sysdoc_dvi/despacho.py` — **dispatch por tipo de verificação, NÃO o documento**. Ler o docstring antes de nomear qualquer módulo novo.
- `sysdoc_dvi/pecas.py` — mapeamento de peças por âncoras; verificar se captura número SEI por peça.

### CLI e geração DOCX
- `sysdoc.py:1214` `build_tabela_itens()` — hoje despeja **todos** os itens, inclusive `conforme`; contraria D-03 e será substituído.
- `sysdoc.py:1271` `render_docx_template()` — substituição literal `{{chave}}` sobre `word/*.xml` com `xml_escape` + `\n → <w:br/>`; ponto do bypass de D-09.
- `sysdoc.py:1300` `_select_reference_template()` e `sysdoc.py:38` `RESERVED_TEMPLATE_NAMES` — seleção de template e nomes reservados de DVI.
- `sysdoc.py:330` `seed_dvi_template()` — semeadura no `init`; precisa virar consciente de `tipo` (D-14).
- `sysdoc.py:1383` — ramo `tipo == "dvi"` do `create()`, onde `{{tabela_itens}}`, `{{total_itens}}`, `{{total_bloqueantes}}`, `{{total_pendentes}}` são preenchidos hoje.
- `templates/build_dvi_base.py` — padrão do gerador determinístico (um run por parágrafo, ZIP byte-estável). Seu `_PARAGRAFOS` é o formato relatório a ser aposentado.

### Regras do projeto
- `CLAUDE.md` — regras-chave, imutabilidade de `templates/render_analise.py` e `templates/analise_template.html`, padrão de nomes `xx_nome_tipo_data.extensao`.
- `AGENTS.md` e `skills/sysdoc/SKILL.md` — fluxo canônico IA-agnóstico; ambos carregam a expansão errada de DVI (D-02).
- `tests/test_dvi_template_base.py`, `tests/test_dvi_autocorrecao.py`, `tests/test_cli.py` — padrão de testes a seguir e fixtures a corrigir.
- `.planning/ROADMAP.md` § Phase 6 — **desatualizado**: descreve só o escopo TR. Precisa ser reescrito para refletir esta repactuação.
- `.planning/codebase/CONVENTIONS.md` — ruff, line-length 100, docstrings em português, `SystemExit` para erros de CLI.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`templates/build_dvi_base.py`** — esqueleto pronto do gerador determinístico de DOCX: `[Content_Types].xml`, rels, `word/document.xml`, `ZipInfo` com data fixa. O novo gerador herda a estrutura e troca `_PARAGRAFOS` por uma moldura de despacho com estilos.
- **`flatten_json()`** (sysdoc.py:1141) — já achata o JSON em chaves pontuadas (`projeto.objeto`, `secao_etp.numero`), que viram placeholders sem código novo.
- **`build_tabela_itens()`** (sysdoc.py:1214) — padrão "builder Python que devolve string para um placeholder"; o novo `build_corpo_despacho()` segue o mesmo formato de assinatura, devolvendo XML em vez de texto.
- **`proximo_nome_artefato()`** — naming `xx_nome_tipo_data.extensao` já implementado; nada a fazer.

### Established Patterns
- **CLI 100% determinística:** `sysdoc create` nunca chama modelo. Todo conteúdo do despacho vem do JSON já produzido pelo `sysdoc-dvi run`.
- **Nunca inventar:** artigo, nº SEI, acórdão, valor ou data ausente vira `pendente` ou fica em branco — nunca é preenchido por inferência. Vale para os campos institucionais.
- **Um parágrafo = um run XML** — regra explícita no docstring de `build_dvi_base.py` para placeholders não quebrarem.
- **Português culto validado** — `PT_BR_ACCENT_TERMS` em `validate_sysdoc.py` reprova acentuação incorreta.

### Integration Points
- `create()` ramo `dvi` (sysdoc.py:1383) — onde o novo builder e a resolução de `tipo` entram.
- `seed_dvi_template()` (sysdoc.py:330) chamada por `init_command()` (sysdoc.py:1466) — semeadura por variante.
- `_select_reference_template()` (sysdoc.py:1300) — fallback do repo para `templates/dvi/` mantendo `referencias/` do projeto com precedência.

</code_context>

<specifics>
## Specific Ideas

O usuário apontou `processo-teste/referencias/dvi.md` como o formato-alvo. Anatomia a reproduzir:

```
DESPACHO DE VERIFICAÇÃO INICIAL - dvi
Processo SEI n.º 90796110000007.000039/2025-14

Senhora Coordenadora Administrativa,                    ← vocativo

Trata o presente processo de [objeto da contratação]…   ← contextualização
O processo foi protocolado no DELIC e após triagem inicial de sua
composição, faço as seguintes considerações:

1) ESTUDO TÉCNICO PRELIMINAR - ETP (SEI 1343011)        ← seção por peça, dinâmica
   a) subitem 4.20: [parecer + fundamento]              ← alíneas
   b) subitem 4.23: …
2) TERMO DE REFERÊNCIA - TR (SEI 1343014)
   b) Subitem 4.2: Vide apontamento constante na alínea "a" do item 1…
3) CRONOGRAMA FÍSICO-FINANCEIRO                          ← peça ausente dos autos
4) MAPA COMPARATIVO DE PREÇOS - MCP (SEI 1342887)

Observações:                                             ← boilerplate institucional
1) A presente verificação não abordou as particularidades da execução…
2) No que tange ao ETP, a análise limitou-se à verificação da presença…
3) Visando preservar o histórico do processo, nenhum documento…

[Signatário]
Gerente do DELIC - substituto

De acordo,
À COLOG, para análise e manifestação acerca dos apontamentos acima.
[Autoridade]
Coordenadora Administrativa
```

Observar: a alínea cita o subitem do documento analisado (`subitem 4.20`), o que mapeia para o campo `seção` do item; e o nº SEI aparece no cabeçalho de cada peça.

</specifics>

<open_decisions>
## Open Decisions for Planning

Áreas que o usuário optou por não discutir, com recomendação explícita. O planner decide e volta ao usuário só se houver tradeoff relevante.

### Origem dos campos institucionais

O despacho exige dados que **não existem no `dados_consolidados.json`**: vocativo (*"Senhora Coordenadora Administrativa,"*), signatário + cargo, unidade (*DELIC*), destinatário (*"À COLOG, para análise e manifestação…"*), autoridade do "De acordo" + cargo.

- **Recomendação:** um bloco `despacho:` em `.sysdoc/config.yaml` — mesmo arquivo que já guarda `tipo`, `vps_host`/`vps_path` e o override `pecas:`. São dados institucionais estáveis por órgão, não por processo; o JSON permanece sobre a análise. Campo ausente vira marcador visível para o humano preencher no Word (nunca inventado, conforme regra do projeto).
- **Alternativa:** contrato 1.2 do JSON, se o usuário quiser que o DOCX seja reproduzível a partir do JSON sozinho.
- **Nº SEI por peça:** `secao_etp.numero` e `secao_tr.numero` já são obrigatórios no schema. Verificar em `sysdoc_dvi/pecas.py` se o mapeamento captura o SEI das demais peças (Cronograma, MCP); se não capturar, decidir entre estender o mapeamento ou deixar o cabeçalho da peça sem SEI.
- **Bloco "Observações":** os 3 itens são boilerplate institucional fixo no modelo real. Recomendação: fixos no DOCX (editáveis no Word), não gerados.

### Destino do formato relatório atual

`templates/dvi_base.docx` gera hoje `{{parecer_executivo}}`, `{{secao_*.parecer_documento}}`, `{{tabela_itens}}`, `{{nota_integridade}}` — nada disso existe no despacho real.

- **Recomendação:** o despacho não os inclui; esse conteúdo já vive no HTML de análise (`render_analise.py`) e no JSON. Aposentar `templates/dvi_base.docx` quando `templates/dvi/` estiver verificado, com nota no CHANGELOG. Confirmar com o usuário antes de remover, porque `sysdoc init` semeia esse arquivo hoje.

</open_decisions>

<deferred>
## Deferred Ideas

- **Templates de TR (4 categorias Lei 14.133)** — escopo original desta fase, adiado para a rodada seguinte **dentro desta mesma fase aberta**. Achados do scout que valem para quando ela vier:
  - Existem **3 modelos distintos**, não 4: `…servicos-e-obras…(1).docx` é byte-idêntico ao `…servicos-e-obras….docx` (md5 `a226e3c7b43485df18e7358153792131`). E o terceiro modelo é um **Termo de Contrato**, não um TR.
  - `_detect_procurement_category()` (sysdoc.py:1287) devolve 4 categorias (`compras`, `servicos_com_dedicacao`, `servicos_sem_dedicacao`, `obras`) contra 3 modelos reais — descasamento 4×3 a resolver.
  - Os modelos oficiais são densos em blanks próprios (`[INSERIR OBJETO]`, `[indicar o prazo]`, alternativas `OU`, notas explicativas) e trazem `word/comments.xml`; decidir o que o SysDoc preenche e o que preserva literal.
- **Template de ETP** — depois do TR, conforme o usuário.
- **Interface web para pregoeiros** — Phase 7, já no ROADMAP.

### Reviewed Todos (not folded)
- *"Revisar a pasta não rastreada `Referencias/` antes de qualquer publicação ampla; ela parece conter modelos reais do usuário"* (STATE.md § Pending Todos) — não entra nesta rodada porque `Referencias/` só importa para os templates de TR. Reabrir quando a rodada de TR começar.

</deferred>

---

*Phase: 6-Templates de documentos institucionais (rodada 1: Despacho de Verificação Inicial)*
*Context gathered: 2026-08-26*
