"""Ponto de extensão da navegação principal (NAV-01/NAV-02/NAV-03).

`{% item_nav rota rotulo icone prefixo excecoes %}` monta uma linha do menu com
o tratamento visual do padrão de referência por construção. `rota` é o NOME da
rota (`app:nome`), nunca a URL. Se `reverse(rota)` falhar — porque o app foi
removido pelo `copier update` — o item some em silêncio (sem
`NoReverseMatch`, T-07-08): é o mesmo contrato documentado do
`{% url 'x' as var %}` do Django, aplicado do lado Python (D-89, critério 6).

`icone` é o NOME de um ícone do dicionário fechado `ICONES` abaixo — a tag
NUNCA aceita markup SVG como argumento (T-07-06). Um nome desconhecido
renderiza o item sem ícone, nunca quebra a página (D-90).

`item_nav` NÃO é mecanismo de autorização: ela não checa permissão nenhuma.
Esconder um item de menu não protege a rota correspondente — a proteção
continua sendo o `LoginRequiredMiddleware` e a permissão da própria view
(T-07-07).

`{% nav_dominio %}` insere o arquivo de itens do sistema derivado e degrada
para menu vazio quando ele não existe — ver a docstring da própria tag.
"""

from django import template
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.urls import NoReverseMatch, reverse
from django.utils.safestring import mark_safe

register = template.Library()

# Ícones por nome — o markup interno do <svg> 24x24, stroke="currentColor".
# Dicionário FECHADO: só os nomes aqui existem; qualquer outro nome devolve
# ícone vazio (D-90), nunca levanta erro.
ICONES = {
    "casa": mark_safe(
        '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/>'
    ),
    "grafico": mark_safe(
        '<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>'
    ),
    "lista": mark_safe(
        '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="m9 12 2 2 4-4"/>'
    ),
}


@register.inclusion_tag("core/_item_nav.html", takes_context=True)
def item_nav(context, rota, rotulo, icone="", prefixo="", excecoes=""):
    """Um item da navegação principal, com o estado ativo por construção.

    `prefixo` marca o item ativo também nas rotas-filhas (ex.: "/exemplo/"),
    além da correspondência exata de `request.path` com a URL revertida.

    `excecoes` lista, separados por espaço, os caminhos sob `prefixo` que NÃO
    devem acender este item — as rotas-irmãs que já têm item próprio no menu.
    Sem ela, um item com `prefixo="/exemplo/"` acende junto com o item de
    `/exemplo/dashboard/`, e a página passa a ter dois `aria-current="page"`
    (G-01).

    Por que a exceção é DECLARADA no sítio da chamada e não inferida: uma
    `inclusion_tag` renderiza um item por vez, sem estado compartilhado e sem
    enxergar os irmãos. Qualquer desempate automático dependeria da ORDEM em
    que os itens aparecem no arquivo — frágil exatamente no arquivo que
    pertence ao derivado. Declarada, a exceção é lida junto com o item que ela
    governa.

    A correspondência EXATA nunca é anulada por `excecoes`: um item continua
    ativo na própria URL, aconteça o que acontecer. É o que impede que uma
    exceção mal escrita apague o estado ativo do item dono da rota.

    Sem `request` no contexto (`render_to_string()` sem `request=`, template de
    e-mail, geração de PDF, comando de management) não há caminho atual: o item
    renderiza inativo em vez de derrubar o render.
    """
    try:
        url = reverse(rota)
    except NoReverseMatch:
        return {"url": ""}

    request = context.get("request")
    caminho = request.path if request is not None else ""

    sob_prefixo = bool(prefixo) and caminho.startswith(prefixo)
    excluido = any(caminho.startswith(p) for p in excecoes.split() if p)
    ativo = caminho == url or (sob_prefixo and not excluido)

    return {
        "url": url,
        "rotulo": rotulo,
        "icone": ICONES.get(icone, ""),
        "ativo": ativo,
    }


@register.simple_tag(takes_context=True)
def nav_dominio(context):
    """Insere `core/_nav_dominio.html` — o arquivo de itens do derivado.

    Não é `{% include %}` porque o `{% include %}` do Django com string
    literal levanta `TemplateDoesNotExist` quando o arquivo some: não existe
    `ignore missing` (isso é Jinja2). E o arquivo PERTENCE ao derivado
    (`_skip_if_exists` no copier.yml, e o próprio stub anuncia isso em letras
    maiúsculas), então apagá-lo é um estado previsto — o resultado tem que ser
    menu sem itens de domínio, nunca 500 em toda página que estende
    `shell.html` (WR-10).

    `mark_safe` aqui não é atalho: o conteúdo é um template renderizado pelo
    próprio motor do Django, com autoescape já aplicado dentro do render — não
    é string vinda de request (T-07-27). `context.flatten()` é o que faz
    `request` e o resto do contexto chegarem aos `{% item_nav %}` de dentro do
    arquivo incluído.
    """
    try:
        tpl = get_template("core/_nav_dominio.html")
    except TemplateDoesNotExist:
        return ""
    return mark_safe(tpl.render(context.flatten()))
