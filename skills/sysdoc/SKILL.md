# SysDoc — Fluxo Operacional (IA-agnóstico)

Este é o **fluxo canônico** do SysDoc. Qualquer IA (Claude, GPT, Gemini, outras) que analise documentos nesta pasta deve seguir este arquivo. Nenhuma instrução aqui depende de uma IA específica.

## Objetivo

Produzir análise técnica, jurídica ou documental dos arquivos em `documentos/`, considerando apoios em `referencias/`, com saída em JSON validável e HTML/DOCX renderizados por rotinas determinísticas.

Prioridades: inteligência, precisão, rastreabilidade, economia de contexto. **Não simule handoffs entre agentes.** Quando a análise envolver TR/ETP, aplique também as lentes técnica, jurídica, Delic/referências e consistência ETP x TR dentro de uma única análise.

## Macros de Acionamento (Comandos de Prompt)

O usuário acionará você (o Agente de IA) através de "Macro Comandos". Quando o usuário digitar um desses comandos, você deve executar as ações associadas usando a CLI determinística local do SysDoc:

- **`/sysdoc init [pasta]`** (ou `sysdoc init [pasta]`):
  - Rode `sysdoc init [pasta]` (cria estrutura base + `.sysdoc/config.yaml`).
  - Solicite ao usuário que coloque os arquivos a analisar em `documentos/` e referências/templates em `referencias/`.
  - Após a confirmação do usuário, rode `sysdoc analyze [pasta]`.

- **`/sysdoc analyze [pasta] [prompt]`** (ou `sysdoc analyze [pasta] -i "prompt"`):
  - Rode `sysdoc analyze [pasta]` no shell (roda `prepare` automaticamente se ainda não houver cache).
  - Leia os caminhos impressos: `contexto_sysdoc.md` e `.sysdoc/cache/textos/`.
  - Aplique a instrução adicional, se fornecida (foco em garantia, sanções, etc.).
  - Gere `[pasta]/dados_consolidados.json` seguindo este `SKILL.md` + `schema_sysdoc.json`.

- **`/sysdoc all [pasta]`** (orquestração completa):
  - **Fase 1 (Preparação)**: Rode `sysdoc analyze [pasta]` via shell.
  - **Fase 2 (Análise)**: Leia `[pasta]/.sysdoc/cache/contexto_sysdoc.md` + arquivos em `.sysdoc/cache/textos/`.
  - **Fase 3 (Geração)**: Gere `[pasta]/dados_consolidados.json` usando SUA inteligência, respeitando este `SKILL.md` e `templates/schema_sysdoc.json`.
  - **Fase 4 (Publicação)**: Rode `sysdoc publish [pasta]` via shell (valida, versiona JSON, gera HTML). Corrija se o validador falhar.
  - **Fase 5 (Deploy)**: Rode `sysdoc deploy [pasta]` via shell (envia HTML para VPS por SSH).

- **`/sysdoc render [pasta]`**: Rode `sysdoc render [pasta]` para gerar HTML a partir do JSON existente (sem validar nem versionar).

- **`/sysdoc deploy [pasta]`**: Rode `sysdoc deploy [pasta]` para enviar o HTML mais recente para a VPS configurada em `.sysdoc/config.yaml`.

- **`/sysdoc create [pasta] [tipo]`**:
  - Rode `sysdoc create [pasta] [tipo]` para gerar `.docx` em `output/`.
  - O comando usa `dados_consolidados.json` ou o JSON mais recente e preenche placeholders `{{campo}}` de um template `.docx` em `referencias/` ou passado por `--template`.

## Ferramentas de CLI (Apenas para o Agente)

Você executará estes comandos via shell para orquestrar o processo:

```bash
sysdoc status
sysdoc init [pasta]
sysdoc prepare [pasta]
sysdoc analyze [pasta] [-i "instrução"]
sysdoc config -vps <usuario@host> -path <caminho-remoto> [pasta]
sysdoc validate [pasta]
sysdoc render [pasta]
sysdoc publish [pasta]
sysdoc deploy [pasta]
sysdoc create [pasta] [tipo] [--template arquivo.docx] [--json arquivo.json]
sysdoc compare [pasta]
```

Onde `sysdoc` for entry point (instalado via `pip install -e .`), substitua por `python sysdoc.py` se rodar a partir do código fonte.

## Entradas obrigatórias

- arquivos suportados em `[pasta]/documentos/` (PDF, DOCX, TXT ou MD)
- arquivos de apoio em `[pasta]/referencias/` (PDF, DOCX, TXT, MD ou templates DOCX)

Se `documentos/` não tiver nenhum arquivo suportado, interrompa e peça os documentos a analisar.

## Saídas

- `[pasta]/dados_consolidados.json`
- `[pasta]/output/dados_consolidados_[modelo_ia]_[data].json` quando publicado por `python sysdoc.py publish [pasta]`
- `[pasta]/output/analise_[modelo_ia]_[data].html` (ex.: `analise_gpt-5_2026-04-24.html`)
- `[pasta]/output/[tipo]_[modelo_ia]_[data].docx` quando gerado por `sysdoc create`

O renderizador auto-incrementa `_2`, `_3`, ... quando já existe arquivo para o mesmo modelo/data.

### Identificação do modelo de IA (obrigatório)

O campo `modelo_ia` no JSON deve ser **o identificador real do modelo que produziu a análise**, em slug. Exemplos: `claude-opus-4-7`, `claude-sonnet-4-6`, `gpt-5`, `gpt-5-mini`, `gemini-2-5-pro`, `llama-3-3-70b`.

O renderizador usa esse valor para compor o nome do arquivo. **Nunca** use um valor genérico como `ia`, `modelo`, `default` ou o nome do rodízio — sempre o identificador real. Isso garante rastreabilidade quando múltiplas IAs operam o mesmo fluxo.

## Fluxo de Análise (`sysdoc all`)

Quando executando o macro `sysdoc all`, siga rigidamente estes passos:

1. Verificar se `documentos/` contém ao menos um arquivo suportado. Se não, interrompa e peça os documentos a analisar.
2. Executar a ferramenta de shell:
   ```bash
   sysdoc analyze [pasta]
   ```
   `analyze` roda `prepare` automaticamente se o cache não existir e imprime os caminhos do contexto e dos textos extraídos.
3. Ler o arquivo gerado: `[pasta]/.sysdoc/cache/contexto_sysdoc.md`. Use-o como mapa. Ele não substitui a conferência dos textos integrais extraídos em `.sysdoc/cache/textos/`.
4. Triar achados pelas lentes obrigatórias aplicáveis (Técnica, Jurídica, Delic/referências, Consistência entre documentos).
5. Selecionar entre 5 e 10 achados relevantes.
6. Gerar o JSON da análise usando seu conhecimento, garantindo aderência absoluta ao `templates/schema_sysdoc.json`. Preencha `modelo_ia` com seu slug real (ex: `claude-sonnet-4-6`, `gpt-5`, `gemini-2-5-pro`).
7. Escrever o JSON em `[pasta]/dados_consolidados.json`.
8. Executar a publicação (que embutirá validação rigorosa):
   ```bash
   sysdoc publish [pasta]
   ```
9. Se a etapa 8 falhar (código de erro no validador), LEIA os erros, corrija o arquivo JSON iterativamente e tente publicar novamente.
10. Com a publicação concluída e o HTML gerado, faça o deploy via SSH para a VPS:
   ```bash
   sysdoc deploy [pasta]
   ```

## Preparação determinística

`sysdoc prepare [pasta]` (ou `sysdoc analyze [pasta]`, que inclui prepare) gera:

- `[pasta]/.sysdoc/cache/textos/documentos/*.txt`
- `[pasta]/.sysdoc/cache/textos/referencias/*.txt`
- `[pasta]/.sysdoc/cache/manifest.json`
- `[pasta]/.sysdoc/cache/contexto_sysdoc.md`

Use esse contexto para orientar a análise e reduzir leitura repetida. Se houver dúvida, volte ao texto extraído ou ao PDF original.

## Lentes obrigatórias

**Técnica:** clareza do objeto; escopo, entregáveis, critérios de aceite e execução; preço, quantidades e metodologia de pesquisa; coerência ETP x TR.

**Jurídica:** Lei 14.133/2021; normas e regulamentos vinculantes do projeto; competitividade, habilitação, sanções, garantia, fiscalização, recebimento, pagamento; coerência entre classificação, severidade e risco jurídico.

**Delic/referências:** `confirmado` (achado corrobora referência); `novo` (não constava); `divergente` (documento caminhou em sentido diferente); `null` (sem referência aplicável).

**Consistência ETP x TR:** toda decisão técnica do TR precisa ter lastro no ETP; toda justificativa do ETP precisa refletir-se no TR.

## Idioma e redação

Todos os campos gerados pelo modelo devem estar em norma culta do português brasileiro, com acentuação correta. Isso inclui `titulo`, `subtitulo`, `parecer_executivo`, `parecer_documento`, `item`, `para`, `parecer`, `fundamento`, `metadados`, `projeto.objeto` e `nota_integridade`.

O campo `de` é exceção: preserve a literalidade do documento original, inclusive se o documento tiver erro de digitação, ausência de acento ou quebra estranha de extração.

## Hierarquia normativa

```text
lei/norma aplicável > regulamento vinculante > modelo oficial > referência técnica confiável > texto atual
```

Não invente artigo, acórdão, número SEI, valor, data ou cláusula. Quando a base for insuficiente, classifique como `pendente`.

## Critério de seleção de achados

Inclua quando houver: risco jurídico ou técnico relevante; contradição interna; divergência ETP x TR; apontamento Delic confirmado, divergente ou pendente; lacuna de preço, prazo, medição, garantia, habilitação, sanção, recebimento, subcontratação; redação que restrinja competitividade ou prejudique execução.

Evite itens meramente descritivos. `conforme` só entra quando comprovar saneamento de ponto relevante.

Limites:

- análise normal: 5 a 10 itens;
- análise profunda, quando solicitada: até 15 itens.

## Regras de redação dos itens

- `de`: trecho literal suficiente para rastreabilidade. Use o item inteiro quando curto. Em omissões, use `[OMISSÃO] seção onde deveria constar`.
- `para`: redação completa, pronta para colar, sem placeholders, reticências ou instruções genéricas.
- `parecer`: divergência, impacto e orientação, nessa ordem.
- `fundamento`: norma, item, modelo, reunião, e-mail ou documento específico, com citação exata.
- Preserve separação entre ETP e TR. IDs sequenciais por documento (`ETP-001`, `ETP-002`, ..., `TR-001`, `TR-002`, ...).

### Exemplo bom

```json
{
  "id": "TR-003",
  "número": 3,
  "item": "Garantia contratual",
  "documento": "TR",
  "seção": "11.2",
  "de": "O contratado apresentará garantia em até 10 dias úteis.",
  "para": "O contratado apresentará garantia no percentual de 5% do valor do contrato, na forma do art. 96, §1º, da Lei 14.133/2021, em até 10 (dez) dias úteis contados da assinatura, prorrogáveis por igual período mediante justificativa aceita pela fiscalização.",
  "parecer": "O TR exige garantia sem fixar percentual nem modalidades admitidas, deixando a exigência inexequível e vulnerável a impugnação. Impacto: ausência de base objetiva para glosa. Orientação: fixar percentual, modalidades e prazo prorrogável.",
  "fundamento": "Lei 14.133/2021, art. 96, §1º; Modelo Delic de TR para serviços continuados, item 11.",
  "classificação": "risco",
  "severidade": "alta",
  "risco_jurídico": "relevante",
  "status_delic": "divergente",
  "alterado_pelo_jurídico": false
}
```

### Exemplo ruim (não faça)

- `de` parafraseado ("o TR fala sobre garantia") em vez de literal.
- `para` com placeholder ("fixar percentual de [X]%").
- `fundamento` genérico ("Lei 14.133").
- `parecer` descritivo sem divergência/impacto/orientação.

## Schema canônico

Definido em `templates/schema_sysdoc.json`.

Campos de topo obrigatórios: `titulo`, `subtitulo`, `modelo_ia`, `data_análise`, `projeto`, `metadados`, `documentos_analisados`, `parecer_executivo`, `secao_etp`, `secao_tr`, `itens`, `nota_integridade`.

Cada item: `id`, `número`, `item`, `documento`, `seção`, `de`, `para`, `parecer`, `fundamento`, `classificação`, `severidade`, `risco_jurídico`, `status_delic`, `alterado_pelo_jurídico`.

## Enums

- `documento`: `ETP`, `TR`
- `classificação`: `conforme`, `ajuste_necessário`, `risco`, `pendente`
- `severidade`: `crítica`, `alta`, `média`, `baixa`, `informativa`
- `risco_jurídico`: `bloqueante`, `relevante`, `menor`, `informativo`
- `status_delic`: `confirmado`, `novo`, `divergente`, `null`
- `classificação_documento`: `aprovado`, `aprovado_com_ressalvas`, `reprovado`, `pendente_de_complementação`

## Regras de coerência (o validador rejeita se violar)

- `classificação = risco` → `risco_jurídico` ∈ {`relevante`, `bloqueante`}.
- `classificação = conforme` → `risco_jurídico` = `informativo`.
- `risco_jurídico = bloqueante` → `severidade` ∈ {`crítica`, `alta`}.
- `alterado_pelo_jurídico = true` → `de` ≠ `para`.
- `modelo_ia` deve ser slug real do modelo, não valor genérico.
- Campos gerados devem passar na checagem determinística de acentuação em português brasileiro.
- Quando houver cache preparado, `de` deve ser rastreável no texto extraído do documento indicado.
- `parecer_executivo`: mínimo 450 palavras.
- `parecer_documento` (ETP e TR): mínimo 120 palavras.

## Determinismo

- `templates/analise_template.html` e `templates/render_analise.py` **não podem ser alterados** pela análise.
- Nenhum HTML é escrito manualmente — apenas pelo renderizador.
- Mesmo JSON validado produz exatamente o mesmo HTML.

## Checklist final

Antes de renderizar:

- ETP e TR separados; IDs sequenciais por documento.
- `modelo_ia` preenchido com o identificador real do modelo.
- Todo item com `de`, `para`, `parecer`, `fundamento` não-vazios e não-placeholder.
- Campos gerados em português brasileiro com acentuação correta.
- Coerência classificação × severidade × risco jurídico.
- `parecer_executivo` ≥ 450 palavras.
- `python templates/validate_sysdoc.py [pasta]/dados_consolidados.json` retorna "SysDoc JSON válido."
- Preferencialmente, `python sysdoc.py publish [pasta]` conclui validação, versionamento do JSON e renderização.
