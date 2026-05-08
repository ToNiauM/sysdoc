# Workflow GSD para o SysDoc CLI

Este guia explica como usar o GSD neste projeto especificamente. O SysDoc tem uma regra central: a CLI é determinística, prepara artefatos, valida JSON, renderiza HTML e faz deploy; a análise jurídica e técnica é feita pelo agente de IA lendo os artefatos gerados.

No Codex, use os comandos GSD como skills com prefixo `$`, por exemplo `$gsd-progress`, `$gsd-plan-phase 2` e `$gsd-execute-phase 2`. O menu de slash commands do harness pode não listar GSD, porque aqui ele está disponível como skill, não como comando visual da UI.

## Quando Usar GSD

Use GSD para evoluir o produto SysDoc: mudar `sysdoc.py`, testes, documentação, roadmap, validadores e wrappers de harness.

Não use GSD para executar uma análise concreta de ETP/TR. Para isso, use o fluxo do SysDoc:

```text
/sysdoc analyze <pasta>
/sysdoc all <pasta>
/sysdoc render <pasta>
/sysdoc deploy <pasta>
```

Em outras palavras:

- GSD organiza o desenvolvimento do produto.
- SysDoc organiza a análise de documentos de contratação.

## Fluxo Padrão Para Desenvolvimento

Use este ciclo para qualquer melhoria planejada do CLI:

```text
$gsd-progress
$gsd-discuss-phase <número>
$gsd-plan-phase <número>
$gsd-execute-phase <número>
$gsd-code-review
$gsd-verify-work
```

### 1. Ver Estado Atual

Comece com:

```text
$gsd-progress
```

Objetivo: descobrir a fase atual, o que já foi entregue e qual é a próxima ação recomendada. Neste projeto, a fonte GSD fica em `.planning/`, especialmente:

- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `.planning/phases/`

Use também o `ROADMAP.md` da raiz quando quiser ver o backlog histórico/manual do projeto.

### 2. Discutir a Fase Antes de Planejar

Use quando a fase ainda tiver ambiguidade:

```text
$gsd-discuss-phase 2
```

Para o SysDoc, isso é útil quando a fase envolve decisão de produto, por exemplo:

- como deve funcionar `sysdoc create`;
- quais documentos Word devem ser gerados;
- quais campos do JSON alimentam cada template;
- como manter a CLI offline e determinística;
- como o agente deve receber o handoff sem a CLI chamar LLM.

Resultado esperado: um `CONTEXT.md` na pasta da fase, registrando decisões antes do plano.

### 3. Planejar a Fase

Use:

```text
$gsd-plan-phase 2
```

Para este projeto, o plano deve respeitar estas restrições:

- ler `skills/sysdoc/SKILL.md` antes de qualquer ação;
- não editar `templates/analise_template.html`, `templates/render_analise.py` ou `templates/validate_sysdoc.py` durante uma análise;
- nunca escrever HTML manualmente;
- manter a CLI determinística e sem chamadas LLM;
- rodar `python -m pytest tests/ -v` antes e depois das edições;
- atualizar `CHANGELOG.md`;
- preservar português culto nos textos gerados.

Quando a mudança envolver código, o plano deve indicar arquivos, testes e critério de aceite. Para o SysDoc, bons critérios de aceite normalmente são comandos reais:

```text
python -m pytest tests/ -v
python sysdoc.py analyze <pasta> --dry-run
python sysdoc.py validate <pasta>
python sysdoc.py render <pasta>
```

### 4. Executar a Fase

Use:

```text
$gsd-execute-phase 2
```

Durante a execução, mantenha o escopo fechado na fase planejada. O padrão desejado no SysDoc é:

1. editar o mínimo necessário;
2. adicionar ou ajustar testes junto com o comportamento;
3. validar localmente com pytest;
4. atualizar `CHANGELOG.md`;
5. registrar no GSD o que foi entregue.

Se a fase for grande, use waves do GSD:

```text
$gsd-execute-phase 2 --wave 1
$gsd-execute-phase 2 --wave 2
```

## Fluxo Para Tarefas Pequenas

Para alterações pequenas e isoladas, prefira GSD leve:

```text
$gsd-quick
```

Use para:

- adicionar um teste de regressão;
- ajustar texto de README;
- documentar uma decisão;
- melhorar uma mensagem de erro;
- corrigir comportamento pequeno do argparse.

Para tarefas triviais de até poucos arquivos:

```text
$gsd-fast "corrigir typo no README"
```

Evite `$gsd-fast` quando houver risco de contrato público do CLI, schema, renderização, deploy ou fluxo de análise. Nesses casos, use `$gsd-quick --validate` ou uma fase completa.

## Fluxo Para Nova Funcionalidade

Exemplo: implementar `sysdoc create`.

1. Ver estado:

```text
$gsd-progress
```

2. Discutir comportamento esperado:

```text
$gsd-discuss-phase 2
```

3. Planejar com testes:

```text
$gsd-plan-phase 2 --tdd
```

4. Executar:

```text
$gsd-execute-phase 2 --tdd
```

5. Revisar:

```text
$gsd-code-review
```

6. Validar com UAT:

```text
$gsd-verify-work
```

Para o SysDoc, uma nova funcionalidade só deve ser considerada pronta quando:

- pytest passa;
- comando de CLI tem help coerente;
- README e CHANGELOG refletem o comportamento;
- o fluxo continua offline;
- o agente ainda consegue operar pelo `AGENTS.md` e `skills/sysdoc/SKILL.md`.

## Fluxo Para Análise Real de ETP/TR

Este fluxo não é GSD. Ele usa o SysDoc.

1. Criar projeto:

```text
/sysdoc init <pasta>
```

2. Colocar arquivos:

```text
<pasta>/ETP.pdf
<pasta>/TR.pdf
<pasta>/modelos/
```

3. Preparar handoff:

```text
/sysdoc analyze <pasta>
```

4. O agente lê:

```text
<pasta>/.sysdoc/cache/contexto_sysdoc.md
<pasta>/.sysdoc/cache/textos/
templates/schema_sysdoc.json
skills/sysdoc/SKILL.md
```

5. O agente gera:

```text
<pasta>/dados_consolidados.json
```

6. Publicar:

```text
/sysdoc publish <pasta>
```

7. Deploy, se configurado:

```text
/sysdoc deploy <pasta>
```

Use GSD apenas se, durante uma análise real, for descoberto um defeito do produto que precise virar melhoria do CLI.

## Comandos GSD Mais Úteis Neste Projeto

```text
$gsd-help
```

Mostra a referência geral de comandos.

```text
$gsd-progress
```

Mostra onde o projeto está e qual ação vem em seguida.

```text
$gsd-progress --do "implementar comando create para gerar Word"
```

Roteia uma intenção em linguagem natural para o comando GSD adequado.

```text
$gsd-map-codebase --fast
```

Atualiza o mapa do código quando o projeto mudou bastante.

```text
$gsd-plan-phase <número> --tdd
```

Planeja uma fase em ordem orientada a testes.

```text
$gsd-execute-phase <número>
```

Executa os planos da fase.

```text
$gsd-code-review
```

Revisa bugs, riscos, segurança e qualidade antes de fechar a fase.

```text
$gsd-verify-work
```

Valida se a entrega cumpre o objetivo, não apenas se os testes passam.

## Regra Prática de Escolha

Use este critério:

```text
Vou mudar o produto SysDoc?       Use GSD.
Vou analisar ETP/TR de uma pasta? Use /sysdoc.
Vou corrigir algo minúsculo?      Use $gsd-fast ou edição direta.
Vou mexer em contrato de CLI?     Use $gsd-quick --validate ou fase completa.
Vou alterar render/schema?        Planeje com cuidado e rode a suíte inteira.
```

O melhor uso do GSD aqui é manter a evolução do SysDoc rastreável, testada e coerente com a decisão arquitetural principal: ferramenta local, determinística, com a inteligência concentrada no agente que lê os artefatos.
