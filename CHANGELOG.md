# CHANGELOG — SysDoc

Todas as mudanças notáveis são documentadas aqui seguindo [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [Não publicado]

### Adicionado

- **P5 — preços de modelos configuráveis por alvo** (`sysdoc_dvi/cli.py`, `sysdoc_dvi/config.py`, `sysdoc_dvi/relatorio.py`, `tests/test_dvi_precos.py`): `sysdoc-dvi config --preco <alvo> <entrada_usd_1M> <saida_usd_1M>` grava `dvi.precos["<alvo>"] = {"entrada": ..., "saida": ...}` em `~/.sysdoc/config.json` (repetível, mescla com preços já registrados, preserva `economico`/`forte`/`api_keys`, arquivo em modo 0600). `--listar` exibe o bloco `preços (USD por 1M tokens)` sem nunca ecoar chave de API. Alvo fora do formato `provedor/modelo`, provedor não suportado ou valor não numérico/negativo devolve código 1 sem gravar nada. `carregar_precos_dvi` agora ignora silenciosamente qualquer entrada malformada e coage os valores válidos para `float`. Preço configurado tem precedência sobre `PRECOS_PADRAO` (vazio de propósito) e passa a produzir custo estimado diferente de zero em `provedores._preco_estimado`; alvo sem preço continua com custo zerado, e o aviso do relatório de execução agora termina com o comando `sysdoc-dvi config --preco <alvo> <entrada_usd_1M> <saida_usd_1M>` já preenchido com o alvo real.
- **P1 — fatiador determinístico de peças no `prepare`** (`sysdoc.py`, `sysdoc_dvi/pecas.py`, `sysdoc_dvi/pipeline.py`, `sysdoc_dvi/relatorio.py`, `tests/test_dvi_fatiador.py`): o caminho canônico do motor DVI — um único PDF do processo inteiro em `documentos/` — agora roda `sysdoc-dvi run` sem exigir bloco `pecas:` em `.sysdoc/config.yaml`. `sysdoc prepare`, ao encontrar exatamente um documento fora do layout legado `ETP.txt`/`TR.txt`, detecta cabeçalhos inequívocos em linha própria (`detectar_fronteiras_pecas`) e grava fatias virtuais por peça (`escrever_fatias_virtuais`) em `.sysdoc/cache/textos/documentos/{PECA}.txt`, com entrada correspondente no manifest (`virtual`, `peca`, `origem`, `offset_inicio`, `offset_fim`). Fatia menor que 2000 caracteres ou ambígua (duas candidatas de tamanho comparável) é descartada. `sysdoc_dvi.pecas.mapear_pecas` ganhou o resultado `fatiamento` para peças fatiadas e o fallback `arquivo-inteiro` — quando existe exatamente um documento real, qualquer peça ainda não resolvida (inclusive PROCESSO) mapeia para esse documento em vez de abortar; override em `.sysdoc/config.yaml` continua com precedência absoluta e sempre aponta para o arquivo inteiro. A origem de cada peça aparece no passo 4 de `sysdoc-dvi run` e num novo bloco `6) Peças mapeadas:` do relatório de execução. Projetos multi-arquivo continuam produzindo exatamente o mesmo mapeamento de antes (sem entradas virtuais).
- **P6 — `sysdoc init` semeia template DVI base em `referencias/`** (`templates/build_dvi_base.py`, `templates/dvi_base.docx`, `sysdoc.py`, `tests/test_dvi_template_base.py`): `sysdoc create <pasta> dvi` exigia um template institucional manual em `referencias/`, que ninguém tem na primeira execução. `templates/build_dvi_base.py` gera deterministicamente (byte-estável) `templates/dvi_base.docx`, com os 12 placeholders de `tipo=dvi` íntegros e sem placeholder órfão (`{{projeto}}` não é usado). `sysdoc init <pasta>` agora copia esse template para `<pasta>/referencias/dvi.docx` via `seed_dvi_template`, sem sobrescrever um template DVI já existente (`dvi.docx`, `modelo_dvi.docx`, `template_dvi.docx` ou qualquer `.docx` com "dvi" no nome). `_select_reference_template` ganhou `RESERVED_TEMPLATE_NAMES` para que o fallback de `create tr` nunca escolha por engano um nome reservado a `dvi`.
- **P4 — progresso por item no passo 5 do `sysdoc-dvi run`** (`sysdoc_dvi/pipeline.py`, `tests/test_dvi_progresso.py`): o passo 5 (execução do checklist) ficava mudo por toda a duração da análise; agora cada item concluído imprime `   [n/total] ID: classificação`, com `total` igual ao número de itens pendentes do run atual (numa retomada por checkpoint, reflete só os itens ainda não resolvidos). O checkpoint continua sendo gravado como primeira ação do callback de conclusão.
- **README — seção "Exemplo didático: do zero ao deploy nos dois fluxos"**: passo a passo comentado de um mesmo projeto fictício percorrendo o fluxo original (agente de IA via `sysdoc analyze` → `publish` → `create tr` → `deploy`) e o novo fluxo DVI (`sysdoc-dvi config` → `run --tipo tic` → `relatorio` → `create dvi` → `deploy`), com tabela comparativa de quando usar cada um.

### Corrigido

- **Sigla DVI — expansão correta** (`CLAUDE.md`, `AGENTS.md`, `README.md`, `checklists/dvi.yaml`, `skills/sysdoc/SKILL.md`, `.claude/skills/sysdoc-analise/SKILL.md`, `.opencode/skills/sysdoc-analise/SKILL.md`, `templates/build_dvi_base.py`, `templates/dvi_base.docx`, `tests/test_dvi_template_base.py`, `tests/test_dvi_autocorrecao.py`, `tests/test_sigla_dvi.py`): DVI significa **Despacho de Verificação Inicial**, confirmado pela linha 1 do modelo institucional real (`processo-teste/referencias/dvi.md`: `DESPACHO DE VERIFICAÇÃO INICIAL - dvi`) e pelo dono do produto (D-01 de `06-CONTEXT.md`). A entrada anterior desta mesma seção corrigiu "Diligência de Verificação de Instrução" para "Documento de Verificação Inicial", que também estava errado — a segunda expansão errada se espalhou pela documentação e por prompts consumidos por agentes de IA. `templates/dvi_base.docx` foi regerado com o título correto, e `tests/test_sigla_dvi.py` agora varre todo arquivo versionado (via `git ls-files`, excluindo `.planning/` e o histórico deste `CHANGELOG.md`) e trava qualquer regressão futura das duas expansões erradas.
- **P3 — grounding com segunda chance elimina falsos pendentes de espaçamento/hifenização/pontuação** (`sysdoc_dvi/grounding.py`, `sysdoc_dvi/tipos.py`, `sysdoc_dvi/relatorio.py`, `tests/test_dvi_reancoragem.py`): uma citação do modelo que divergia do texto-fonte só por espaçamento, hifenização de fim de linha ou pontuação tipográfica (aspas “ ” ‘ ’ ou travessão – —) era rejeitada pelo grounding check e o item inteiro degradava para `pendente`, mesmo com parecer afirmativo correto. `normalizar_texto` ganhou `_normalizar_pontuacao` (aspas e travessões tipográficos → retos/hífen), beneficiando tanto `verificar_trecho` quanto a nova `reancorar_trecho`, que — antes da degradação — tenta localizar o trecho no texto-fonte via a mesma varredura de janelas (`_melhor_janela`, extraída de `verificar_trecho`) sobre uma normalização com mapa de offsets (`_normalizar_com_mapa`) e, havendo casamento acima do limiar, reescreve `de` com o trecho LITERAL do texto-fonte (nunca sintetizado), revalidando antes de aceitar. `ResultadoItem` ganhou o campo `reancorado`; citação fabricada continua degradando exatamente como antes. O relatório de execução ganhou o bloco `6) Re-ancoragens determinísticas: {total}` (chave `reancoragens`), com `7) Peças mapeadas:` (P1) renumerado na sequência.
- **P2 — mensagem determinística em norma culta e autocorreção de acentuação no passo 8** (`sysdoc_dvi/despacho.py`, `sysdoc_dvi/autocorrecao.py`, `sysdoc_dvi/pipeline.py`, `tests/test_dvi_autocorrecao.py`): a mensagem de reclassificação por fundamentação fora da base legal citava literalmente os nomes de campo `base_legal_texto`/`referencia` sem acentuação, quebrando o próprio validador imutável (`itens[N].parecer: termo sem acentuação`); corrigida para "não consta na base legal nem na referência deste item". Novo módulo `sysdoc_dvi/autocorrecao.py` (`coletar_erros_validacao`, `parsear_erros_acentuacao`, `aplicar_correcoes_acentuacao`, `autocorrigir_json`) aplica, numa única passada, a correção apontada pelo próprio erro estruturado do validador (`--json`) sempre que a única falha é acentuação — nunca reescreve o campo `de` — e o passo 8 do pipeline revalida uma única vez antes de declarar falha; falhas por qualquer outro motivo preservam o comportamento atual (JSON e relatório mantidos, saída não-zero). As correções aplicadas ficam registradas em `avisos` no relatório de execução.
- **Docs — significado da sigla DVI**: a documentação expandia DVI incorretamente como "Diligência de Verificação de Instrução"; corrigido para **Documento de Verificação Inicial** em `README.md`, `checklists/dvi.yaml`, `skills/sysdoc/SKILL.md`, `.claude/skills/sysdoc-analise/SKILL.md` e `.opencode/skills/sysdoc-analise/SKILL.md`, e definição adicionada em `CLAUDE.md` e `AGENTS.md`.
- **WR-05 — próximo passo impresso pelo relatório de execução** (`sysdoc_dvi/relatorio.py`): o comando sugerido estava com os argumentos invertidos (`sysdoc create dvi <pasta>`, que o argparse interpreta como projeto "dvi"); corrigido para a ordem real `sysdoc create <pasta> dvi`.
- **WR-01 — falha de provedor na síntese não escapa mais como traceback** (`sysdoc_dvi/pipeline.py`, `sysdoc_dvi/sintese.py`): um `ErroProvedor` (ex.: HTTP 429/500) na fase de síntese agora é capturado pelo orquestrador com mensagem de uma linha e remédio (checkpoint preservado, `sysdoc-dvi run` retoma), saindo com código 1; conteúdo estruturado que não é objeto na resposta de síntese é tratado como parecer vazio e cai no fluxo normal de retry/`ErroSintese`, sem `AttributeError`.
- **WR-02 — item incoerente do modelo não aborta mais a montagem** (`sysdoc_dvi/pipeline.py`): combinações permitidas pelo schema mas rejeitadas pelo validador (ex.: `classificação: risco` + `risco_jurídico: menor`; `bloqueante` com severidade fora de crítica/alta) eram um beco sem saída determinístico (`ErroMontagem` reproduzível a cada retomada). Agora degradam deterministicamente para `pendente` com `falha_estruturada` registrada no relatório de execução, antes da montagem.
- **WR-04 — derivação de `modelo_ia` para alvos com prefixo de fornecedor** (`sysdoc_dvi/pipeline.py`): `config.forte.partition("/")[2]` mantinha tudo após a primeira barra, e alvos reais de OpenRouter como `openrouter/z-ai/glm-5.2:free` geravam um `modelo_ia` com `/` e `:` rejeitado pela montagem e pelo validador, abortando o run no passo 7. A nova `derivar_modelo_ia` usa o último segmento do caminho e substitui caracteres fora do domínio do slug por hífen (`glm-5.2-free`).
- **CR-04 — rastreabilidade de citações de MCP/RISCOS/PROCESSO** (`templates/validate_sysdoc.py`): itens do checklist cuja peça de origem é MCP, Mapa de Riscos ou peça processual produzem `de` citado dessas peças, mas `validate_traceability` só conferia contra ETP/TR — uma citação corretamente ancorada falhava a validação. Quando o cache contém outros textos extraídos em `.sysdoc/cache/textos/documentos/`, o campo `de` agora é conferido também contra a união de todos os textos de documentos do cache; com apenas ETP/TR no cache, o comportamento anterior é mantido integralmente.
- **CR-03 — rejeição de grounding não derruba mais o run** (`sysdoc_dvi/grounding.py`, `sysdoc_dvi/tipos.py`, `sysdoc_dvi/relatorio.py`): o `de` alucinado de um item rejeitado pelo grounding era preservado no JSON final, onde a checagem de rastreabilidade do validador imutável derrubava a análise inteira (violação de RF9). Agora o `de` é reescrito com o marcador `[OMISSÃO]` reconhecido pelo validador, o item degrada para `pendente` e o trecho original rejeitado fica registrado apenas no relatório de execução (`falhas_grounding.trechos_rejeitados`).
- **CR-02 — vigência nunca certifica o que a tabela não afirma** (`sysdoc_dvi/normas.py`): entradas com status `suspensa` ou `pendente_de_conferencia` eram reportadas como "norma vigente conforme tabela curada" (`classificação: conforme`). Agora somente `status: vigente` produz `conforme`; os demais status degradam para `pendente` com mensagem honesta pedindo conferência manual da vigência.
- **CR-01 — itens `calculo` no `AgenteLLM`** (`sysdoc_dvi/agente.py`): a resposta estruturada da extração de preços é uma lista (`SCHEMA_TABELA_PRECOS`) e derrubava `executar_item` (`'list' object has no attribute 'get'`), degradando todo item `calculo` para `pendente`. O agente agora serializa a lista extraída em JSON no campo `para`, cumprindo o contrato documentado em `despacho.py`; conteúdo estruturado que não é lista vira `pendente` com `falha_estruturada` explícita.

---

## [1.5.0] — 2026-08-26

### Adicionado

- **Motor de análise por checklist** (`sysdoc_dvi/`, `checklists/dvi.yaml`, RF1): os itens de análise DVI passam a ser dados versionados em YAML — `id`, `aplicabilidade` (`geral`/`tic`/`ambos`), `peca`, `tipo` (`presenca`/`julgamento`/`calculo`/`vigencia`/`mecanica`), `pergunta`, `base_legal_texto`, `referencia`, `severidade_default`, `modelo_alvo` e `ativo`. Adicionar, editar ou desativar um item nunca exige alteração de código.
- **`sysdoc-dvi run/relatorio/config`** (`sysdoc_dvi/pipeline.py`, `sysdoc_dvi/cli.py`, `tests/test_dvi_run.py`, D-01/D-03/D-04/D-16, RF9): `sysdoc-dvi run [pasta]` executa o pipeline completo — config de modelos → checklist filtrado por `--tipo`/`.sysdoc/config.yaml` → `sysdoc prepare` (se necessário) → mapeamento de peças → checklist por item com retomada via checkpoint → síntese pelo modelo forte → `dados_consolidados.json` → `sysdoc validate` → `sysdoc render` → relatório de execução em `output/`. Aborta antes de qualquer escrita quando falta configuração de modelos (`~/.sysdoc/config.json`), e com mensagem citando a peça e o remédio quando uma peça obrigatória não é localizada. `sysdoc-dvi relatorio [pasta]` reimprime o último relatório sem reexecutar a análise. `sysdoc-dvi config` grava o mapeamento econômico/forte em `~/.sysdoc/config.json` com permissão restrita (diretório 0700, arquivo 0600) e `--listar` nunca ecoa uma chave de API.
- **`normas/vigencia.yaml`** (RF7): tabela curada de normativos (`norma`, `status`, `substituida_por`, `conferida_em`), com override por projeto em `referencias/`. Itens do tipo `vigencia` fazem lookup determinístico nessa tabela — norma citada e ausente da tabela vira item `pendente` com a mensagem "norma não catalogada", nunca consulta ao modelo.
- **Verificações determinísticas de `calculo`, `vigencia` e `mecanica`** (`sysdoc_dvi/`): itens `calculo` extraem a tabela de dados via LLM em schema fechado e recalculam média, mediana e unitário × quantidade em Python puro, comparando com o valor declarado dentro de uma tolerância configurável; itens `vigencia` usam o lookup acima; itens `mecanica` rodam funções Python puras sobre o texto extraído (numeração sequencial por peça, presença de CATMAT/CATSER, menção × presença de cronograma físico-financeiro) — nenhum desses três tipos chama modelo para o julgamento final.
- **Grounding check** (`sysdoc_dvi/grounding.py`): confere que o campo `de` de cada item é rastreável no texto extraído da peça antes de aceitar o resultado do modelo, sinalizando falha de grounding no relatório de execução.
- **Síntese dedicada** (`sysdoc_dvi/sintese.py`, RF6): `parecer_executivo` e `parecer_documento` não são redigidos item a item — uma chamada final no modelo forte recebe exclusivamente os itens já validados e produz os pareceres, preservando os mínimos de palavras do validador (450/120) sem induzir enchimento nos modelos econômicos que executam os itens.
- **Checkpoint de retomada** (`sysdoc_dvi/checkpoint.py`): `sysdoc-dvi run` grava progresso em `.sysdoc/cache/` e retoma por padrão (`--resume`) de onde parou; `--no-resume` reinicia do zero.
- **Relatório de execução** (`sysdoc_dvi/relatorio.py`, RF9): cada análise DVI gera relatório com itens por status e por tipo, falhas de grounding, tokens e custo estimado por modelo, duração e hash do checklist utilizado.
- **`sysdoc create dvi`** (`sysdoc.py`, `tests/test_dvi_create.py`, RF10): novo tipo `dvi` no comando `create`, gerando o DVI em DOCX a partir de template institucional em `referencias/` (busca por `dvi.docx`, `modelo_dvi.docx`, `template_dvi.docx` ou qualquer `.docx` com "dvi" no nome; `--template` explícito é respeitado). Preenche `{{parecer_executivo}}`, `{{secao_etp.parecer_documento}}`, `{{secao_tr.parecer_documento}}` e demais campos achatados do JSON consolidado, além das chaves derivadas `tabela_itens` (uma linha por item: `ID — documento/seção — classificação (severidade, risco): parecer`), `total_itens`, `total_bloqueantes` e `total_pendentes`. Saída no padrão `xx_projeto_dvi_data.docx`. Sem template disponível, falha com mensagem citando `dvi.docx` em `referencias/`. Nenhuma chamada de LLM; geração 100% offline a partir do JSON revisado.
- **Validação de entradas ZIP do template DOCX** (`sysdoc.py`, mitigação T-05-41): `render_docx_template` agora recusa templates `.docx` cujo `infolist` contenha caminho absoluto ou segmento `..`, antes de reescrever o ZIP.

### Alterado

- **Padrão de nomes de artefatos `xx_nome_tipo_data.extensao`** (`sysdoc.py`, `templates/render_analise.py`, `tests/test_nomes_artefatos.py`, decisões D-08/D-09 da Fase 5): `publish` (JSON versionado), `render` (HTML) e `create` (DOCX) agora nomeiam a saída com um contador de produção por (projeto, tipo) — `01_processo-042_dvi_2026-08-26.docx`, regerar produz `02_...`, nunca sobrescreve nem reutiliza número. `modelo_ia` sai do nome do arquivo e permanece apenas nos metadados do JSON. `status`, `deploy` e `compare` continuam reconhecendo artefatos com nome legado (`analise_[modelo]_[data].html`, `dados_consolidados_[modelo]_[data].json`, `tr_[modelo]_[data].docx`) junto dos novos — **arquivos antigos não são renomeados**. Funções órfãs `resolve_next_json_archive`, `resolve_next_output` e `resolve_next_docx_output` removidas de `sysdoc.py`; `resolve_next_filename` removida de `templates/render_analise.py` em favor de `proximo_nome_artefato` replicada nos dois módulos (o renderer roda isolado como subprocesso, sem importar `sysdoc.py`).
- **Âncoras de peça no `manifest.json`** (`sysdoc.py`, `sysdoc_dvi/pecas.py`): `sysdoc prepare` passa a gravar `detectar_ancoras`/`peca_sugerida` por arquivo extraído no manifest; `sysdoc_dvi.pecas.mapear_pecas` usa essas âncoras textuais (com override manual em `.sysdoc/config.yaml`) para resolver ETP/TR/MCP/Mapa de Riscos automaticamente.
- **Schema 1.1** (`templates/schema_sysdoc.json`, `templates/validate_sysdoc.py`): campos opcionais `origem_verificacao` (`llm`/`deterministico`/`lookup`) e `checklist_id` por item; `schema_version` e `checklist_hash` na raiz do JSON, para auditoria de qual checklist produziu a análise. Nenhum campo novo é obrigatório — JSONs 1.0 continuam válidos.
- **Flags `config --vps` e `--path`** (`sysdoc.py`, `tests/test_cli.py`, `AGENTS.md`, `README.md`, `skills/sysdoc/SKILL.md`): substitui as flags antigas `-vps`/`-path` (sintaxe não-POSIX) por `--vps`/`--path`. `--vps-host` e `--vps-path` permanecem como aliases ocultos para retrocompatibilidade. Help do `sysdoc config` agora exibe apenas as formas canônicas.

### Corrigido

- **Rastreabilidade do campo `de`** (`templates/validate_sysdoc.py`): `load_source_texts` voltou a ler `.sysdoc/cache/textos/documentos/<DOC>.txt` primeiro, com fallback para o caminho legado `.sysdoc/cache/textos/<DOC>.txt`. A checagem `validate_traceability` estava silenciosamente inerte desde que a Fase 2 moveu a saída do `prepare` para a subpasta `documentos/`.
- **Caminho de cache duplicado no manifest** (`sysdoc.py`, descoberto em 05-14): `write_extracted_text` gravava o campo `cache` do manifest relativo ao diretório de trabalho (`rel()`), mas `sysdoc_dvi.pecas.mapear_pecas` sempre o resolve relativo à raiz do projeto. Ao rodar `sysdoc prepare Projeto` a partir do diretório pai (o padrão mais comum), isso produzia um caminho duplicado (`Projeto/Projeto/.sysdoc/...`) fora de `.sysdoc/cache`, e todo mapeamento de peça real falhava com `ErroMapeamentoPeca`. Agora `cache` é sempre relativo a `paths.root`.

---

## [1.4.0] — 2026-05-12

### Adicionado

- **Estrutura genérica de projeto** (`sysdoc.py`): `sysdoc init` agora cria `documentos/`, `referencias/` e `output/`, mantendo `.sysdoc/config.yaml`. Projetos antigos com `ETP.pdf`, `TR.pdf` e `modelos/` continuam aceitos como compatibilidade.
- **Prepare genérico** (`sysdoc.py`): `sysdoc prepare` extrai todos os arquivos suportados em `documentos/` e `referencias/`, preservando a origem no cache em `.sysdoc/cache/textos/documentos/` e `.sysdoc/cache/textos/referencias/`.
- **Saídas em `output/`** (`sysdoc.py`): `render`, `publish`, `deploy` e `compare` agora usam `output/` para HTML e JSON versionado, com fallback para artefatos antigos na raiz quando necessário.
- **`sysdoc create [pasta] [tipo]`** (`sysdoc.py`): novo gerador DOCX determinístico. Preenche placeholders `{{campo}}` em template `.docx` com valores achatados do JSON (`{{projeto.objeto}}`, `{{modelo_ia}}`, etc.). Para `tipo=tr`, aplica lógica de revisão ETP: substitui `de` por `para` em itens com `classificação ∈ {ajuste_necessário, risco}`, registra substituições pendentes quando `de` não é localizado, ignora marcadores de omissão. Seleção automática de template por categoria de contratação (compras, serviços com/sem dedicação, obras) a partir de `referencias/`. Saída na raiz do projeto como `tr_[modelo_ia]_[data].docx`. Aceita `--json` e `--template`.
- **`sysdoc create --tipo`** (`sysdoc.py`, `tests/test_cli.py`): `tr` passa a ser o tipo padrão quando omitido, com `--tipo` como alias explícito para scripts.
- **Testes CLI** (`tests/test_cli.py`): cobertura para extração separada de documentos/referências, render em `output/` e preenchimento DOCX.

### Atualizado

- **Fluxo operacional** (`README.md`, `AGENTS.md`, `skills/sysdoc/SKILL.md`): documentação atualizada para documentos gerais, `referencias/`, `output/` e `create`.
- **`VERSION` / pacote**: versão ajustada para `1.4.0`.

---

## [1.3.0] — 2026-05-08

### Adicionado

- **`GSD_WORKFLOW_SYSDOC.md`**: guia operacional para usar GSD especificamente no desenvolvimento do SysDoc CLI, separando o fluxo de evolução do produto (`$gsd-*`) do fluxo de análise documental (`/sysdoc ...`).
- **`sysdoc analyze` com handoff visual** (`sysdoc.py`): saída do comando reformulada como diagrama ASCII em caixa, deixando explícito que a CLI **não** executa análise — análise acontece dentro de um harness de IA. O diagrama lista os harnesses suportados (Claude Code, OpenCode, Codex CLI, Gemini CLI) e mostra o slash command exato (`/sysdoc analyze <pasta>`) para colar no chat do harness.
- **`sysdoc analyze --dry-run`** (`sysdoc.py`): reimprime o handoff sem reextrair PDFs. Útil para reler instruções quando o cache já existe. Falha com código 1 e mensagem clara se o cache estiver ausente.
- **`sysdoc guia [pasta]`** (`sysdoc.py`): novo comando de onboarding interativo. Verifica `ETP.pdf`, `TR.pdf` e `modelos/`, oferece configurar VPS no `.sysdoc/config.yaml`, pergunta qual harness o usuário usa e salva `.sysdoc/cache/roteiro.txt` com os comandos exatos para o projeto. Detecta `sys.stdin.isatty() is False` e sai com 1 + dica de `sysdoc analyze --dry-run` (proteção contra travar em pipe ou dentro de harness).
- **UTF-8 em stdout/stderr** (`sysdoc.py`): `main()` reconfigura ambos os streams para UTF-8 com `errors='replace'`, eliminando `UnicodeEncodeError` em consoles Windows que rodam em cp1252.
- **`tests/test_cli.py`**: 12 novos testes em `TestHandoffBox`, `TestAnalyzeDryRun` e `TestGuia`. Inclui regressão "no LLM mention" que falha se o handoff voltar a citar `--auto`, `OpenRouter`, `API key` ou `autônomo` — princípio permanente de CLI determinística.

### Atualizado

- **`VERSION`** (`sysdoc.py`): 1.2.0 → 1.3.0.
- **`README.md`**: descrição de `analyze` ajustada para refletir o handoff visual e o novo `--dry-run`; entrada de `sysdoc guia` adicionada à tabela de comandos.
- **`.planning/ROADMAP.md`**: Phase 4 reescrita alinhada ao princípio "CLI determinística, análise no harness". Os requisitos antigos que previam `--auto`/OpenRouter foram substituídos pelos efetivamente entregues (`SYSD-08` a `SYSD-12`).

---

## [1.2.0] — 2026-05-07

### Removido

- **`sysdoc_gui.py`**: GUI Tkinter removida. SysDoc passa a ser exclusivamente CLI + slash `/sysdoc` em harnesses de IA. Justificativa: agentes de IA (Claude Code, OpenCode, Codex, Antigravity, Cline, Gemini CLI) são a interface primária e não usam GUI; manter `tkinter` aumentava superfície de manutenção sem ganho prático.
- **`setup.py`**: removida referência a `sysdoc_gui` em `py_modules`.

### Adicionado

- **`sysdoc all [pasta]`** (`sysdoc.py`): novo atalho determinístico que inicializa a estrutura do projeto e recria o cache (`prepare`) para deixar `contexto_sysdoc.md`, `manifest.json` e textos extraídos prontos para o agente de IA gerar `dados_consolidados.json`.
- **`sysdoc config -vps root@ip -path /opt/web/... [pasta]`** (`sysdoc.py`): novo comando para mostrar ou atualizar `.sysdoc/config.yaml`, incluindo dados de deploy da VPS e pasta remota do HTML.
- **Phase 1 / GSD CLI-style** — SysDoc agora é invocável como sistema estilo GSD por agentes de IA via `/sysdoc [comando]`.
- **`sysdoc analyze [pasta] [-i instrução]`** (`sysdoc.py`): novo subcomando que roda `prepare` automaticamente quando o cache não existe e imprime os caminhos do contexto e dos textos extraídos. Aceita `--instruction` / `-i` para foco temático.
- **`.sysdoc/config.yaml`** (`sysdoc.py`): novo arquivo de configuração por projeto com `projeto`, `vps_host`, `vps_path` e `modelo_ia_padrao`. Criado automaticamente por `sysdoc init`.
- **`load_config()` e `init_config()`** (`sysdoc.py`): funções utilitárias para ler/criar configuração do projeto.
- **`ProjectPaths.config`** (`sysdoc.py`): dataclass agora inclui caminho para `.sysdoc/config.yaml`.
- **`deploy()` lê config.yaml** (`sysdoc.py`): `vps_host` e `vps_path` agora são lidos do config; valores hardcoded servem apenas como fallback.
- **`pyyaml>=6.0`** (`pyproject.toml`): adicionado às dependências.
- **`.opencode/skills/sysdoc-analise/SKILL.md`**: wrapper OpenCode equivalente ao Claude Code, sem MCP, prefere `sysdoc analyze` via Bash.
- **`AGENTS.md`**: arquivo genérico com instruções, comandos e regras-chave para todos os harnesses (Codex, Antigravity, Cline, Gemini CLI, etc.).
- **`tests/test_cli.py`**: 15 testes cobrindo `analyze`, `init`, `all`, `config`, `ProjectPaths.config`, formato YAML e `load_config`.

### Corrigido

- **`sysdoc init .` e pastas existentes** (`sysdoc.py`): inicialização agora é idempotente e não interativa; cria apenas `modelos/`, `.sysdoc/config.yaml` e README ausente, sem sobrescrever arquivos do usuário.

### Atualizado

- **`skills/sysdoc/SKILL.md`**: macros de acionamento incluem `/sysdoc analyze` e placeholder `/sysdoc create`. Fluxo `sysdoc all` agora começa por `sysdoc analyze`.
- **`README.md`**: fluxo principal reescrito em passos curtos do `init` ao `deploy`, com explicações mínimas entre comandos.
- **`README.md`**: exemplos de configuração de VPS agora usam placeholders genéricos, sem IP ou caminho de produção específico.
- **`.claude/skills/sysdoc-analise/SKILL.md`**: triggers atualizados para `/sysdoc`, `sysdoc analyze`, `sysdoc deploy`, `sysdoc create`. Exemplos usam `sysdoc` direto em vez de `python sysdoc.py`.
- **`CLAUDE.md`**: referência a `AGENTS.md` para outros agentes.

---

## [1.1.0] — 2026-05-06

### Adicionado
- **M1-B** (`sysdoc.py`): `extract_pdf()` avisa quando texto extraído < 100 chars (PDF provavelmente escaneado).
- **M1-C** (`sysdoc.py`): `extract_docx()` agora extrai tabelas (`w:tbl`) além de parágrafos, separando células com ` | `.
- **M2-A** (`sysdoc.py`): `analyze()` faz retry automático com erros da validação incluídos no prompt quando o JSON retornado falha na validação. Nova função auxiliar `run_validate_and_capture()`.
- **M2-B** (`sysdoc.py`): `call_openrouter_json()` usa `json_schema` formal para modelos `openai/` e `google/`; demais usam `json_object`.
- **M3-A** (`sysdoc.py`): `status()` renderiza tabela alinhada com colunas `ETP TR MODELOS JSON HTML PREP`.
- **M3-B** (`sysdoc_gui.py`): campo "Instrução extra" na GUI, passado como `--instruction` ao chamar `analyze`.
- **M3-C** (`sysdoc.py`): novo subcomando `sysdoc compare [pasta]` — lista JSONs versionados com resumo de itens, bloqueantes e relevantes por modelo.
- **M4-B** (`pyproject.toml`): configuração do linter `ruff>=0.4` em `[tool.ruff.lint]` com regras E/F/W/I.

### Corrigido
- **M1-A** (`sysdoc.py`, `pyproject.toml`): dependência `PyPDF2` (deprecada) substituída por `pypdf>=4.0.0`.

---

## [1.0.0] — 2026-05-06

### Adicionado
- **`sysdoc init [pasta]`** — cria estrutura básica de um novo projeto SysDoc via CLI, com ou sem template em `templates/projeto-padrao/`.
- **`sysdoc analyze --dry-run`** — prepara o contexto e exibe o prompt completo sem chamar a LLM. Útil para inspecionar o que seria enviado.
- **`sysdoc --version`** — exibe a versão instalada.
- **`sysdoc models` com filtro e paginação** — o usuário pode filtrar por texto e navegar com [P]róxima/[V]oltar entre páginas de 30 modelos.
- **`sysdoc connect` com validação de chave** — a chave de API é testada com uma chamada real antes de ser salva (✅ ou ⚠️).
- **`python templates/validate_sysdoc.py --json`** — output estruturado em JSON para integrações externas.
- **`tests/test_validate.py`** — 27 testes automatizados cobrindo validador, rastreabilidade, coerência de enums e funções utilitárias.
- **`ROADMAP.md`** — documento de próximas melhorias planejadas, legível por qualquer modelo de IA.
- **GUI: botões 🔑 Conectar API e 📝 Modelos** — abre terminal interativo para `sysdoc connect` e `sysdoc models`.
- **GUI: indicador de progresso pulsante** — label anima com `...` durante execução.
- **GUI: botão 📄 Abrir HTML** — habilitado automaticamente após render/publish, abre no navegador padrão.
- **`pyproject.toml`** completo com authors, license MIT, keywords e dependência dev `pytest`.

### Corrigido
- **B1** (`sysdoc_gui.py`): modelo padrão hardcoded `gpt-5.4-mini` (inexistente) substituído por leitura dinâmica do `~/.sysdoc/config.json`.
- **B3** (`sysdoc.py`): leitura dos textos extraídos após `prepare` usa path absoluto consistente, sem lógica frágil de `is_absolute()`.
- **B4** (`sysdoc.py`): chamadas LLM agora têm retry com backoff exponencial (5s → 10s → 20s) para erros 429, 500, 502, 503, 504.
- **B5** (`sysdoc_gui.py`): `create_project()` não trava mais com `iterdir()` quando a pasta não existe.
- **B7** (`validate_sysdoc.py`): entrada duplicada `"orgao"` removida do dicionário `PT_BR_ACCENT_TERMS`.
- **B8** (`sysdoc.py`): regex de detecção de processo corrigida para cobrir formato SEI `NNNNN.NNNNNN/AAAA-NN`.
- **C5** (`sysdoc.py`): mensagem de erro ao rodar sem API key citava `sysdoc config`; corrigido para `sysdoc connect`.
- **D4** (`sysdoc.py`): arquivos `ETP.pdf` e `TR.pdf` agora são encontrados de forma case-insensitive (`etp.pdf`, `Etp.pdf`, etc.).

### Refatorado
- **C1** (`sysdoc.py`): `call_openai_json` e `call_openrouter_json` (80% idênticos) unificados na função base `_call_openai_compatible_json`.
- **C2** (`sysdoc.py`): removida função `detect_provider()` (código morto, nunca chamada).
- **C3** (`sysdoc.py`): help text de `--model` corrigido de "Modelo OpenAI" para agnóstico.
- **C4** (`sysdoc_gui.py`): label "Modelo OpenAI" → "Modelo".
- **C7** (`pyproject.toml`): versão bumped de `0.1.0` para `1.0.0`; metadados completos.

---

## [0.1.0] — 2026-04-27

### Adicionado
- CLI inicial com subcomandos: `status`, `connect`, `models`, `prepare`, `analyze`, `validate`, `render`, `publish`.
- Fluxo IA-agnóstico com suporte a OpenRouter, OpenAI, Gemini e Anthropic.
- Extração determinística de PDFs e DOCX para cache em `.sysdoc/cache/`.
- Geração de `contexto_sysdoc.md` com briefing, mapa de seções e extratos por tema.
- Schema canônico `templates/schema_sysdoc.json` com validação de coerência.
- Validador determinístico `templates/validate_sysdoc.py` com verificação de acentuação PT-BR e rastreabilidade.
- Renderizador HTML `templates/render_analise.py` com template imutável.
- Versionamento de JSON por modelo/data (`dados_consolidados_[modelo]_[data].json`).
- GUI Tkinter básica (`sysdoc_gui.py`).
- Skill canônica em `skills/sysdoc/SKILL.md`.
