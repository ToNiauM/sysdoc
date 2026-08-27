# Rodar na sua máquina, sem Docker

O `docker compose up` do `docs/DEPLOY.md` é o caminho de servidor. Este
documento é o outro caso: rodar o SysDoc **na sua própria máquina**, sem
Docker, quando a análise não deve consumir CPU e crédito do VPS.

A análise chama modelo de IA e lê PDFs grandes — é o passo mais pesado do
sistema. Rodando local, o processamento acontece no seu computador e o VPS
não é envolvido.

## O que precisa estar instalado

| Item | Confirmar com |
|------|---------------|
| Python 3.10 ou mais novo | `python3 --version` |
| Node (só para compilar o CSS uma vez) | `node --version` |
| `pdftotext` (opcional, melhora a extração) | `pdftotext -v` |

## 1. Ambiente isolado

Um ambiente virtual evita conflito com os pacotes do sistema — várias
distribuições recentes recusam `pip install` fora de um venv (PEP 668).

```bash
cd /caminho/para/sysdoc
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[web]"
```

## 2. Compilar o CSS (uma vez)

O Tailwind é compilado, nunca servido por CDN. No Docker isso acontece num
estágio de build; local, é um comando:

```bash
npx --yes tailwindcss@3.4.17 \
  -c ./tailwind.config.js \
  -i ./core/static/src/input.css \
  -o ./core/static/dist/tailwind.css \
  --minify
```

Repita se mudar template ou `dominio.css`. Se pular este passo, a aplicação
sobe **sem estilo nenhum** — não dá erro, só fica feia.

> Sem Node na máquina? Copie o arquivo já compilado de um ambiente que
> tenha: ele é um `.css` comum, sem dependência de runtime.

## 3. Configurar

```bash
export DJANGO_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')"
export SYSDOC_WEB_DEBUG=1
export SYSDOC_WEB_DATA_DIR="$HOME/.sysdoc-web"
```

No Windows (PowerShell), troque `export X=y` por `$env:X="y"`.

Com `SYSDOC_WEB_DEBUG=1` a chave secreta é gerada sozinha se você não
definir, e `localhost` já é host permitido. **Modo de depuração é só para a
sua máquina** — nunca exponha essa configuração na rede.

As chaves de API do motor continuam vindo de `~/.sysdoc/config.json`, o
mesmo arquivo do `sysdoc-dvi config`. Confira com `sysdoc-dvi config --listar`.

## 4. Banco e usuário

```bash
python3 manage.py migrate
python3 manage.py createsuperuser        # login é por E-MAIL
```

## 5. Subir

São **dois processos**, em terminais separados — os dois com o venv ativo e
as variáveis do passo 3 exportadas:

```bash
# Terminal 1 — a aplicação web
python3 manage.py runserver 8000
```

```bash
# Terminal 2 — o worker que executa as análises
python3 manage.py runworker
```

Abra <http://localhost:8000>.

> **O worker não é opcional.** Sem ele a interface funciona, aceita o
> upload e enfileira a análise — que fica parada em "na fila" para sempre,
> sem mensagem de erro. É o engano mais fácil de cometer neste modo: no
> Docker o entrypoint sobe os dois, aqui você sobe cada um.

## Diferenças em relação ao servidor

| | Local | Servidor |
|---|---|---|
| Processos | dois, à mão | um container, entrypoint cuida |
| Estáticos | `runserver` serve | whitenoise |
| Banco | SQLite em `SYSDOC_WEB_DATA_DIR` | SQLite no volume |
| HTTPS | não | nginx + Let's Encrypt |
| Fila | uma análise por vez | idem |

A trava de **uma análise por vez** vale aqui também: ela é uma constraint
do banco, não do container.

## Problemas comuns

**A análise não sai de "na fila".** O worker não está rodando — veja o
passo 5.

**A página sobe sem estilo.** Falta compilar o CSS (passo 2). Em modo de
depuração o `runserver` serve direto de `STATICFILES_DIRS`, então basta
rodar o comando do passo 2 — não precisa de `collectstatic`.

Confirme com:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/estatico/dist/tailwind.css
```

`200` é o certo. Um **`302`** aqui significa que o arquivo **não existe**:
sem encontrá-lo, o Django entrega a requisição à cadeia normal, o
`LoginRequiredMiddleware` assume e redireciona para a tela de entrada. É
enganoso — parece problema de permissão, e é só CSS que faltou compilar.

**`ModuleNotFoundError: whitenoise`.** O venv não está ativo, ou faltou o
`pip install -e ".[web]"`.

**`ImproperlyConfigured: DJANGO_SECRET_KEY`.** Você está sem
`SYSDOC_WEB_DEBUG=1` e sem a variável. Exporte uma das duas.

**A análise falha citando chave de API.** `~/.sysdoc/config.json` não tem o
provedor configurado — rode `sysdoc-dvi config --listar` para conferir.
