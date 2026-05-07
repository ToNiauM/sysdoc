# SysDoc: Assistente de Inteligência Artificial para Contratações

O **SysDoc** é uma ferramenta de linha de comando (CLI) que automatiza a conferência técnica e jurídica entre o **Estudo Técnico Preliminar (ETP)** e o **Termo de Referência (TR)** em processos de licitação.

Utilizando Inteligência Artificial (compatível com OpenAI, Claude, Gemini, etc.), ele lê seus documentos em PDF ou Word, identifica omissões, aponta riscos jurídicos (com classificação de gravidade) e gera um relatório HTML amigável detalhando o que precisa ser corrigido.

---

## 🚀 Instalação Rápida

Abra o seu terminal (na pasta raiz onde baixou o SysDoc) e rode:

```bash
pip install -e .
```

A partir de agora, o comando `sysdoc` estará disponível em qualquer pasta do seu computador!


---

## 📂 Como Analisar um Projeto (Passo a Passo)

O SysDoc foi construído para ser o "cinto de utilidades" do seu Agente de IA favorito (Claude Code, Gemini CLI, Cursor, etc). 

Para realizar uma análise, **abra o chat do seu Agente de IA na pasta dos seus documentos** e dê os seguintes comandos:

### Comando 1: Iniciar o Projeto
Digite para a IA:
> **`sysdoc init MeuProjeto`**

Ela criará a pasta correta. Coloque seus arquivos `ETP.pdf` e `TR.pdf` dentro da pasta que foi criada.

### Comando 2: Fazer Tudo (Análise Completa)
Com os PDFs na pasta, digite para a IA:
> **`sysdoc all MeuProjeto`**

Ao ler esse "Macro", a IA vai magicamente:
1. Extrair os textos dos PDFs usando a ferramenta do SysDoc.
2. Usar o próprio cérebro genial dela para ler os contratos e encontrar riscos e inconsistências.
3. Gerar o JSON da análise e usar o SysDoc para validar e renderizar um HTML lindo.
4. Fazer o upload automático do seu relatório para a VPS!

---

## 🛠️ Comandos Manuais (Offline)

Se você for um usuário avançado e quiser rodar as ferramentas do SysDoc no terminal *sem* a IA, estes são os utilitários puramente offline disponíveis:

| Comando | O que faz? |
|---------|------------|
| `sysdoc status` | Lista todas as pastas ao seu redor e mostra se falta ETP, TR ou Modelos. |
| `sysdoc init [pasta]` | Cria uma pasta vazia com a estrutura correta. |
| `sysdoc prepare [pasta]` | Extrai o texto dos PDFs/DOCXs. |
| `sysdoc publish [pasta]` | Valida o JSON da análise e gera o relatório final em HTML. |
| `sysdoc deploy [pasta]` | Pega o último relatório HTML gerado e envia por SSH/SCP para o servidor. |
| `sysdoc compare [pasta]` | Mostra um comparativo rápido na tela. |
| `sysdoc analyze [pasta] [-i "foco"]` | Prepara o cache e imprime os caminhos para o Agente de IA gerar a análise. |

---

## 💡 Dicas Importantes

- Se o seu PDF for um **documento escaneado** (imagem), a IA não conseguirá ler. O SysDoc te avisará sobre isso durante a etapa de `prepare`.
- O SysDoc não sobrescreve análises antigas. Cada vez que você roda, ele cria um arquivo HTML novo, com a data e o nome da IA, garantindo um histórico completo das suas revisões!
