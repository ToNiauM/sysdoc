# SysDoc — Fluxo Operacional (IA-agnóstico)

Este é o **fluxo canônico** do SysDoc. Qualquer IA (Claude, GPT, Gemini, outras) que analise documentos nesta pasta deve seguir este arquivo. Nenhuma instrução aqui depende de uma IA específica.

## Objetivo

Produzir análise comparativa técnica e jurídica de `ETP.pdf` e `TR.pdf`, considerando referências em `modelos/`, com saída em JSON validável e HTML renderizado por script determinístico.

Prioridades: inteligência, precisão, rastreabilidade, economia de contexto. **Não simule handoffs entre agentes.** Aplique as lentes técnica, jurídica, Delic/modelos e consistência ETP x TR dentro de uma única análise.

## Acionamento

```text
sysdoc [pasta]
sysdoc [pasta] - [instrução extra]
sysdoc render [pasta]
```

CLI determinístico local:

```bash
python sysdoc.py status
python sysdoc.py prepare [pasta]
python sysdoc.py validate [pasta]
python sysdoc.py render [pasta]
python sysdoc.py publish [pasta]
```

- `sysdoc render [pasta]` apenas reexecuta o renderizador sobre `[pasta]/dados_consolidados.json`. Não refaça a análise.

## Entradas obrigatórias

- `[pasta]/ETP.pdf`
- `[pasta]/TR.pdf`
- arquivos em `[pasta]/modelos/` ou `[pasta]/Modelos/` (PDF, DOCX ou TXT)

Se `ETP.pdf` ou `TR.pdf` não existir, interrompa e peça o arquivo faltante.

## Saídas

- `[pasta]/dados_consolidados.json`
- `[pasta]/dados_consolidados_[modelo_ia]_[data].json` quando publicado por `python sysdoc.py publish [pasta]`
- `[pasta]/analise_[modelo_ia]_[data].html` (ex.: `analise_gpt-5_2026-04-24.html`, `analise_claude-opus-4-7_2026-04-24.html`, `analise_gemini-2-5-pro_2026-04-24.html`)

O renderizador auto-incrementa `_2`, `_3`, ... quando já existe arquivo para o mesmo modelo/data.

### Identificação do modelo de IA (obrigatório)

O campo `modelo_ia` no JSON deve ser **o identificador real do modelo que produziu a análise**, em slug. Exemplos: `claude-opus-4-7`, `claude-sonnet-4-6`, `gpt-5`, `gpt-5-mini`, `gemini-2-5-pro`, `llama-3-3-70b`.

O renderizador usa esse valor para compor o nome do arquivo. **Nunca** use um valor genérico como `ia`, `modelo`, `default` ou o nome do rodízio — sempre o identificador real. Isso garante rastreabilidade quando múltiplas IAs operam o mesmo fluxo.

## Fluxo

1. Verificar entradas obrigatórias.
2. Preparar contexto determinístico, sempre que a ferramenta estiver disponível:
   ```bash
   python sysdoc.py prepare [pasta]
   ```
3. Usar `[pasta]/.sysdoc/cache/contexto_sysdoc.md` como mapa de leitura para economizar tokens. Ele não substitui a conferência dos trechos relevantes nos textos extraídos.
4. Extrair ou consultar texto de ETP, TR e referências (prefira texto literal a OCR quando o PDF tiver camada de texto).
5. Montar briefing curto: objeto, órgão, processo, valor, normas aplicáveis, apontamentos Delic/modelos.
6. Triar achados candidatos pelas lentes obrigatórias.
7. Selecionar apenas achados relevantes (ver "Critério de seleção").
8. Gerar `[pasta]/dados_consolidados.json` no schema canônico, preenchendo `modelo_ia` com o identificador real.
9. Validar:
   ```bash
   python templates/validate_sysdoc.py [pasta]/dados_consolidados.json
   python sysdoc.py validate [pasta]
   ```
10. Corrigir o JSON até o validador passar sem erros.
11. Publicar:
   ```bash
   python sysdoc.py publish [pasta]
   ```
   ou renderizar sem versionar:
   ```bash
   python templates/render_analise.py [pasta]/dados_consolidados.json [pasta]
   ```

## Preparação determinística

`python sysdoc.py prepare [pasta]` gera:

- `[pasta]/.sysdoc/cache/textos/ETP.txt`
- `[pasta]/.sysdoc/cache/textos/TR.txt`
- textos das referências suportadas (`PDF`, `DOCX`, `TXT`, `MD`)
- `[pasta]/.sysdoc/cache/manifest.json`
- `[pasta]/.sysdoc/cache/contexto_sysdoc.md`

Use esse contexto para orientar a análise e reduzir leitura repetida. Se houver dúvida, volte ao texto extraído ou ao PDF original.

## Lentes obrigatórias

**Técnica:** clareza do objeto; escopo, entregáveis, critérios de aceite e execução; preço, quantidades e metodologia de pesquisa; coerência ETP x TR.

**Jurídica:** Lei 14.133/2021; normas e regulamentos vinculantes do projeto; competitividade, habilitação, sanções, garantia, fiscalização, recebimento, pagamento; coerência entre classificação, severidade e risco jurídico.

**Delic/modelos:** `confirmado` (achado corrobora referência); `novo` (não constava); `divergente` (documento caminhou em sentido diferente); `null` (sem referência aplicável).

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
