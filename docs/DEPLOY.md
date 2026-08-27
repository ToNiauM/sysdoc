# Publicar a interface web num servidor

Runbook para colocar a interface web dos pregoeiros no ar num subdomínio,
atrás de proxy reverso. Escrito para ser executado de cima para baixo.

O caso local (`docker compose up`) está no README e não precisa de nada
disto — este documento é só para a operação em servidor.

> **Escopo.** A Phase 7 entregou a aplicação containerizada; a operação em
> produção (TLS, domínio, backup do volume) estava explicitamente adiada no
> `07-CONTEXT.md`. Este runbook cobre essa lacuna. Backup do volume continua
> pendente — veja "O que ainda não está resolvido" no fim.

---

## 0. Antes de começar

Tenha em mãos:

| Item | Como confirmar |
|------|----------------|
| Hostname escolhido | Um subdomínio **livre**. Confira que não há nada servindo nele: `curl -sI https://SEU.DOMINIO` |
| Acesso SSH ao servidor | `ssh usuario@host 'echo ok'` |
| Docker + plugin compose | `docker --version && docker compose version` |
| Porta local livre | `ss -ltn \| grep 8010` deve sair vazio |
| Chaves de API do motor | `sysdoc-dvi config --listar` no servidor |

> **Não reaproveite um hostname que já serve outra coisa.** Apontar o proxy
> para esta aplicação num nome já em uso derruba o que estava lá.

---

## 1. DNS

No Cloudflare, crie um registro para o subdomínio apontando para o IP do
servidor:

- Tipo `A` (ou `AAAA` se o servidor for IPv6), nome `sysdoc`, conteúdo = IP do servidor
- Proxy **ativado** (nuvem laranja) para o Cloudflare terminar TLS e esconder a origem
- SSL/TLS em **Full (strict)** — veja a seção de TLS em
  `docker/nginx-sysdoc.conf.exemplo` sobre por que evitar "Flexible"

Confirme a propagação antes de seguir:

```bash
getent hosts sysdoc.sistemascfc.org
```

---

## 2. Código no servidor

```bash
git clone <url-do-repo> /opt/sysdoc
cd /opt/sysdoc
```

Se já existir, atualize em vez de clonar: `git -C /opt/sysdoc pull`.

---

## 3. Configuração do motor de análise

As chaves de API ficam **só no servidor** e nunca chegam ao navegador.

```bash
mkdir -p /opt/sysdoc-config
cp ~/.sysdoc/config.json /opt/sysdoc-config/        # ou crie do zero
```

Dê leitura ao usuário do container (UID 10001) — sem isto a aplicação sobe
mas nenhuma análise roda:

```bash
chown -R 10001:10001 /opt/sysdoc-config
```

Confira que o arquivo tem a seção `dvi` com `economico`/`forte` e a chave do
provedor.

---

## 4. Variáveis de ambiente

```bash
cd /opt/sysdoc
cp .env.producao.exemplo .env
python3 -c "import secrets; print(secrets.token_urlsafe(50))"   # cole em DJANGO_SECRET_KEY
${EDITOR:-nano} .env
```

Ajuste `SYSDOC_WEB_ALLOWED_HOSTS`, `SYSDOC_WEB_CSRF_ORIGINS`,
`SYSDOC_CONFIG_DIR` e `SYSDOC_WEB_PORTA_LOCAL`. O compose de produção
**falha na subida** se algum deles faltar — de propósito, para não subir
com configuração pela metade.

---

## 5. Subir a aplicação

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose logs -f web
```

Você deve ver, nesta ordem: migrações aplicadas, arquivos estáticos
copiados, `N análise(s) órfã(s) marcada(s) como interrompida(s)` e o
gunicorn subindo. Confirme que responde localmente:

```bash
curl -sI http://127.0.0.1:8010/ | head -1     # espera-se 302
```

Um `302` para `/entrar/` é o certo — significa que a autenticação
obrigatória está ativa.

---

## 6. Proxy reverso

```bash
cp docker/nginx-sysdoc.conf.exemplo /etc/nginx/sites-available/sysdoc
${EDITOR:-nano} /etc/nginx/sites-available/sysdoc      # ajuste server_name e porta
ln -s /etc/nginx/sites-available/sysdoc /etc/nginx/sites-enabled/sysdoc
nginx -t && systemctl reload nginx
```

Emita o certificado (topologia Full (strict)):

```bash
certbot --nginx -d sysdoc.sistemascfc.org
```

---

> ### Armadilha: vhost sem TLS serve o site errado, em silêncio
>
> Se o Cloudflare estiver em modo **Full**, ele conversa com a origem por
> **HTTPS na 443** — mesmo quando o visitante chega por HTTP. Um vhost novo
> que só tenha `listen 80` nunca é alcançado: o nginx cai no **primeiro
> bloco `listen 443` em ordem alfabética de `conf.d/`**, que passa a agir
> como default server, e entrega **o site de outro domínio** com status 200.
> Não há erro em log nenhum.
>
> Foi exatamente o que aconteceu na primeira subida de
> `sysdoc.sistemascfc.org`: o domínio respondia com o conteúdo de
> `analisedados.conf`. O passo 6 (certbot criando o bloco 443) é o que
> corrige. Sintoma para reconhecer: `curl -I https://SEU.DOMINIO` devolve
> 200 com um `last-modified` que não é seu.
>
> Diagnóstico rápido, comparando as duas portas da origem:
>
> ```bash
> curl -sS -o /dev/null -w "80:  %{http_code}\n" -H "Host: SEU.DOMINIO" http://127.0.0.1:80/
> curl -sSk -o /dev/null -w "443: %{http_code}\n" --resolve SEU.DOMINIO:443:127.0.0.1 https://SEU.DOMINIO/
> ```
>
> Respostas diferentes entre as duas = o bloco 443 do seu vhost não existe.

## 7. Contas dos pregoeiros

Não existe auto-cadastro — as contas são criadas pelo administrador, de
propósito: cada análise gasta crédito real de API.

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  exec web python manage.py createsuperuser
```

O comando acima é interativo e exige um terminal de verdade. Em canal sem
TTY (execução por agente, CI, `ssh host 'comando'`) ele não lê as respostas
e **não cria nada** — sem mensagem de erro clara. Nesse caso, use a forma
não-interativa, que mantém a senha fora do histórico do shell:

```bash
read -p "Usuário: " USUARIO
read -s -p "Senha: " SENHA; echo
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T \
  -e DJANGO_SUPERUSER_USERNAME="$USUARIO" \
  -e DJANGO_SUPERUSER_EMAIL="$USUARIO@sistemascfc.org" \
  -e DJANGO_SUPERUSER_PASSWORD="$SENHA" \
  web python manage.py createsuperuser --noinput
unset SENHA
```

Confira depois que a conta existe mesmo:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T web \
  python manage.py shell -c "
from django.contrib.auth import get_user_model
print(get_user_model().objects.count(), 'usuário(s)')"
```

Para os demais pregoeiros, use o Django admin em `/admin/` (contas comuns,
sem marcar "superusuário") ou repita o comando acima.

---

## 8. Verificação

Percorra o roteiro de 13 passos do plano `07-08` no domínio real. Os quatro
que mais importam:

1. Entrar pelo domínio, sem link de cadastro nem recuperação de senha
2. Enviar o PDF único de um processo e iniciar a análise
3. Com uma análise rodando, tentar iniciar outra → aviso de fila ocupada, **nunca** erro 500
4. `docker compose ... restart` → nenhuma análise fica eternamente "em andamento"

---

## Operação

**Ver o que está acontecendo**

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f web
```

**Atualizar para uma versão nova**

```bash
cd /opt/sysdoc && git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

As migrações rodam sozinhas na subida. O volume `sysdoc-dados` preserva
banco, processos e arquivos estáticos entre atualizações.

**Backup do volume**

```bash
docker run --rm -v sysdoc_sysdoc-dados:/dados -v "$PWD":/backup alpine \
  tar czf /backup/sysdoc-dados-$(date +%F).tar.gz -C /dados .
```

Guarde fora do servidor. O volume contém o banco, os documentos enviados e
os despachos gerados.

---

## O que ainda não está resolvido

Honestidade sobre os limites desta entrega:

- **Backup automático** — o comando acima é manual. Não há rotina agendada.
- **Retenção** — nada apaga processos antigos. O volume cresce sem limite;
  acompanhe com `docker system df -v`.
- **Uma análise por vez** é global, não por usuário. Com vários pregoeiros
  simultâneos, o segundo espera. Foi decisão deliberada (custo de API), mas
  se incomodar na prática, é o primeiro ponto a revisitar.
- **Sem painel de custo** — o consumo de API não aparece na interface. O
  dado existe no relatório do motor (`sysdoc-dvi relatorio`).
- **`docker compose up` nunca foi exercitado ponta a ponta num host limpo** —
  a verificação da Phase 7 rodou com a porta remapeada, num host com o pool
  de redes Docker esgotado. A primeira subida real é esta.
