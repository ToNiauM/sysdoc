# `core/` — convenções não-óbvias

Este documento registra 5 convenções do kernel `core/` que não são óbvias a
partir da leitura do código sozinho — quebrá-las produz bugs silenciosos.

## 1. "Hoje" sempre via `timezone.localdate()`

Toda lógica que precisar da data atual **deve** usar
`django.utils.timezone.localdate()` — nunca `timezone.now().date()` nem
`datetime.date.today()`.

Com `USE_TZ=True`, `timezone.now()` sempre retorna um datetime em UTC,
independente de `TIME_ZONE`. Às 21h de um dia em Brasília (UTC−3),
`timezone.now().date()` já retorna o dia seguinte. `datetime.date.today()`
tem o problema oposto: usa o fuso horário do sistema operacional, e dentro
do container Docker o SO está em UTC mesmo com
`TIME_ZONE="America/Sao_Paulo"` configurado no settings. `localdate()` é o
único caminho que converte corretamente para o fuso configurado antes de
extrair a data.

## 2. `AXES_USERNAME_FORM_FIELD = "username"` é proposital

Em `config/settings/base.py`, `AXES_USERNAME_FORM_FIELD` está fixado como
`"username"` — mesmo o projeto usando login por e-mail
(`USERNAME_FIELD = "email"` em `core.Usuario`). **Não "corrigir" para
`"email"`.**

Django sempre usa o kwarg literal `username=` ao chamar `authenticate()`,
independente do `USERNAME_FIELD` do model customizado. Se
`AXES_USERNAME_FORM_FIELD` fosse `"email"`, o django-axes procuraria a
chave `"email"` no dicionário de credenciais — chave que nunca existe nesse
dicionário — e gravaria toda tentativa de login com `username=None`,
quebrando o lockout por usuário+IP sem levantar nenhum erro visível.

## 3. `AUTH_USER_MODEL` nunca muda depois da migração `0001`

`AUTH_USER_MODEL = "core.Usuario"` está definido desde antes de qualquer
migração existir (Plan 01-01), e `core.Usuario` é o próprio modelo migrado
na `0001` (Plan 01-03). Trocar `AUTH_USER_MODEL` depois disso é uma
operação destrutiva no Django — não há caminho suportado de migração
in-place para outro modelo de usuário num banco com dados reais.

Essa é justamente a razão de o `Usuario` customizado existir desde o
primeiro momento do template: preserva a viabilidade de SSO futuro entre os
sistemas da família sem exigir uma reescrita de banco mais adiante.

## 4. Auditoria de modelos com django-simple-history

Modelos de domínio (em `apps/`) que precisam de auditoria optam por ela
declarando o histórico **no próprio modelo**:

```python
from simple_history.models import HistoricalRecords


class MeuModelo(models.Model):
    ...
    history = HistoricalRecords()
```

Depois, `makemigrations` gera a tabela `Historical<Modelo>` automaticamente.
Toda mudança feita através de uma request registra o autor (`history_user`)
sem código extra — o `HistoryRequestMiddleware` (posicionado depois do
`AuthenticationMiddleware` em `config/settings/base.py`) captura
`request.user` em cada escrita. O `apps/exemplo` da Fase 3 exercita esse
padrão.

**Exceção documentada — o user model:** `core.Usuario` é auditado via
`simple_history.register(Usuario)` em `core/admin.py`, **não** com
`HistoricalRecords()` no modelo. Num user model swappable, a FK de
`history_user` da tabela histórica aponta para o próprio user model, criando
dependência circular na carga — `register()` é a forma oficial do
django-simple-history para esse caso. Não "padronizar" movendo o histórico
para dentro de `core/models.py`.

**Armadilha:** `queryset.update()` (e qualquer escrita em massa que não passe
por `save()`) **não gera histórico** — o simple-history só intercepta os
sinais de save/delete por instância. Para operações em massa auditadas, usar
`simple_history.utils.bulk_update_with_history(objetos, Modelo, campos,
default_user=..., default_change_reason=...)`, que grava uma linha de
histórico por objeto.

## 5. Pontos de customização de marca — arquivos de nome fixo

Os logos do core são arquivos estáticos de caminho fixo —
`core/static/img/logo-entidade.svg` e `core/static/img/logo-subsistema.svg`
— e os ícones PWA idem: `core/static/img/icon-192.png`, `icon-512.png` e
`icon-512-maskable.png`. Customizar = **substituir o arquivo mantendo nome e
extensão**. Nunca criar variável de caminho no `.env` nem embutir SVG inline
em template: o nome fixo É o contrato, e `{% static %}` resolve o hashing do
WhiteNoise automaticamente — qualquer indireção quebraria a garantia de
"trocar a marca sem editar código". O nome do PWA vem de
`SISTEMA_NOME`/`SISTEMA_SIGLA` no `.env`.

O admin deliberadamente **não** exibe logo — a identidade dele é nome + cor
via o override cirúrgico existente. Não "completar" o admin com logo.

A lista canônica de todos os pontos de customização (logos, ícones, nome,
cor) vive na seção "Customização de marca" do README do sistema.
