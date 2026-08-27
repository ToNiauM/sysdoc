# Rodar só a linha de comando, na sua máquina

Este é o caminho mais simples do SysDoc, e o original: **sem Django, sem
Docker, sem Node**. Só Python. A análise roda no seu computador e o servidor
não é envolvido em nada.

Se você quer a interface visual para os colegas, veja `docs/RODAR_LOCAL.md`
(local) ou `docs/DEPLOY.md` (servidor). Para uso próprio, a linha de comando
faz o mesmo trabalho com menos peça móvel.

## 1. Instalar

```bash
cd /caminho/para/sysdoc
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
```

Repare que é `pip install -e .`, **sem** o `[web]` — o extra do Django não
entra aqui.

Isso deixa dois comandos disponíveis:

- `sysdoc` — determinístico e offline. Nunca chama modelo de IA.
- `sysdoc-dvi` — o motor de análise. Este sim chama modelo.

Opcional, mas melhora a extração de PDF: `pdftotext` (pacote
`poppler-utils` no Debian/Ubuntu).

## 2. Configurar o motor (uma vez)

As chaves e a escolha de modelo ficam em `~/.sysdoc/config.json`, fora do
repositório:

```bash
sysdoc-dvi config --economico openrouter/<modelo> --forte openrouter/<modelo>
```

A chave de API vai no mesmo arquivo, na seção `api_keys` (ou pela variável
de ambiente `OPENROUTER_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` /
`ANTHROPIC_API_KEY`).

Confira a qualquer momento — o comando mostra se a chave está presente, sem
imprimir o valor:

```bash
sysdoc-dvi config --listar
```

## 3. Criar o projeto

Uma pasta por processo:

```bash
sysdoc init processo-042
```

Isso monta a estrutura e já semeia o template do despacho:

```
processo-042/
├── documentos/     ← os arquivos a analisar entram aqui
├── referencias/    ← modelos e base legal (dvi.docx já vem semeado)
├── output/         ← o que for gerado
└── .sysdoc/config.yaml
```

## 4. Colocar os documentos

Copie o **PDF único do processo inteiro** para `documentos/`:

```bash
cp ~/Downloads/processo-042.pdf processo-042/documentos/
```

O `prepare` fatia o arquivo único em peças virtuais sozinho (identifica ETP,
TR e demais peças). Não precisa separar nada à mão. Peças em arquivos
separados também funcionam — é só colocar todas em `documentos/`.

## 5. Preencher os dados do despacho

Abra `processo-042/.sysdoc/config.yaml` e preencha o bloco `despacho:` —
unidade, destinatário, signatário, autoridade. É o único arquivo que você
edita à mão.

O que ficar em branco aparece como `[PREENCHER: <campo>]` no Word, visível.
Nada é inventado.

Aproveite e defina `tipo:` como `geral` ou `tic` — ou passe `--tipo` no
comando seguinte.

## 6. Analisar

```bash
sysdoc-dvi run processo-042 --tipo geral
```

É o passo demorado e o único que gasta crédito de API. Ele faz tudo:
prepara, analisa item a item pelo checklist, valida, renderiza o HTML e
imprime um relatório de execução ao final.

Interrompeu no meio? Rode de novo: ele retoma do checkpoint. Para começar
do zero, `--no-resume`.

Para rever o relatório da última execução:

```bash
sysdoc-dvi relatorio processo-042
```

## 7. Gerar o despacho em Word

```bash
sysdoc create processo-042 dvi
```

Sai um `.docx` no padrão `NN_processo-042_dvi_AAAA-MM-DD.docx`.

**Este passo é separado de propósito.** O despacho é ato de servidor, não
saída automática de máquina: você lê os apontamentos antes de gerar o
documento que vai para a unidade demandante.

## Resumo

```bash
sysdoc init processo-042
cp ~/Downloads/processo-042.pdf processo-042/documentos/
$EDITOR processo-042/.sysdoc/config.yaml     # bloco despacho: e tipo:
sysdoc-dvi run processo-042 --tipo geral
sysdoc create processo-042 dvi
```

## Comandos úteis

| Comando | Para quê |
|---------|----------|
| `sysdoc status` | Lista os projetos e o que cada um já tem |
| `sysdoc prepare <pasta>` | Só extrai o texto, sem analisar (não gasta API) |
| `sysdoc validate <pasta>` | Confere o JSON da análise |
| `sysdoc render <pasta>` | Regera o HTML a partir do JSON |
| `sysdoc create <pasta> tr` | Gera o TR em vez do despacho |
| `sysdoc-dvi relatorio <pasta>` | Relatório da última execução |

## Problemas comuns

**`sysdoc: command not found`.** O venv não está ativo. `source .venv/bin/activate`.

**Erro citando chave de API.** Rode `sysdoc-dvi config --listar` e confira
se o provedor aparece como "configurada".

**"tipo de verificação não definido".** Falta `tipo:` no
`.sysdoc/config.yaml` ou `--tipo geral|tic` no comando.

**O PDF não foi reconhecido em peças.** Se for um PDF digitalizado sem
camada de texto, a extração não tem o que ler. O SysDoc não faz OCR — passe
o arquivo por um OCR antes.
