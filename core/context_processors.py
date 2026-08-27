from django.conf import settings

from core.tema import COR_PAGE_ESCURO, css_da_marca


def usuario_atual(request):
    """Expõe o usuário autenticado ao template — usado no layout base (ex.:
    nome/e-mail no cabeçalho) sem cada view precisar passá-lo explicitamente."""
    return {"usuario_atual": getattr(request, "user", None)}


def identidade(request):
    """Expõe a identidade parametrizada do sistema (D-16) a todo template —
    shell, login, admin e PWA consomem nome/sigla/cor daqui, para que a
    identidade tenha uma única fonte (`.env` → settings) em vez de valores
    espalhados pelos templates.

    Desde a Fase 7, a família de marca inteira também tem uma única fonte de
    runtime: `.env` → `settings.COR_PRIMARIA` → `core.tema.css_da_marca()` →
    `tema_css`, injetado num `<style>` em `base.html` que sobrescreve os
    defaults de `core/static/src/input.css` nos dois temas.

    `cor_page_escuro` existe para o script de tema do `base.html` (plano
    07-05): ele roda ANTES de qualquer CSS (D-99), então não pode ler o
    valor com `getComputedStyle` — e escrever o hex literal no template
    seria a única ocorrência de hex em `core/templates`, reprovando o gate
    do critério 3 (`! grep -rnE "#[0-9a-fA-F]{6}" core/templates apps`)."""
    return {
        "sistema_nome": settings.SISTEMA_NOME,
        "sistema_sigla": settings.SISTEMA_SIGLA,
        "cor_primaria": settings.COR_PRIMARIA,
        "tema_css": css_da_marca(settings.COR_PRIMARIA),
        "cor_page_escuro": COR_PAGE_ESCURO,
    }
