"""`SistemaAdminSite` num módulo próprio, sem NENHUM ModelAdmin registrado
aqui (D-13).

`SistemaAdminConfig.default_site` (core/apps.py) aponta para
`"core.admin_site.SistemaAdminSite"`. A resolução de `admin.site`
(LazyObject) é preguiçosa e NÃO é reentrante: se este site vivesse em
`core/admin.py` — que registra ModelAdmin via `admin.site` no próprio
import — o import disparado de dentro de `DefaultAdminSite._setup()`
reacessaria `admin.site` antes de `_setup()` terminar, e a instância mais
externa a concluir sobrescreveria `_wrapped` com um `_registry` vazio,
apagando os registros em silêncio. Isolar o site num módulo sem registro
elimina o problema: `admin.site` resolve de uma vez e só depois o
autodiscovery registra os ModelAdmin contra o site já pronto.
"""

from django.conf import settings
from django.contrib import admin


class SistemaAdminSite(admin.AdminSite):
    """`AdminSite` do template com identidade via settings (CORE-03).

    Substitui `admin.site` globalmente através de `default_site` em
    `SistemaAdminConfig` (core/apps.py) — `config/urls.py` não muda (D-13).

    `has_permission` NÃO é sobrescrito: o gate padrão do Django
    (`is_active and is_staff`) é mantido deliberadamente (A1) — um template
    genérico não deve mudar a semântica de acesso ao admin em silêncio;
    quem gerar um sistema e quiser gate mais restritivo faz a mudança
    explícita (e o teste em test_admin.py trava esse comportamento).
    """

    def __init__(self, name="admin"):
        super().__init__(name)
        # Identidade vem dos settings (D-16) — nenhum nome/sigla literal aqui.
        self.site_header = f"{settings.SISTEMA_NOME} — Administração"
        self.site_title = settings.SISTEMA_SIGLA
        self.index_title = "Painel do administrador"

    def each_context(self, request):
        contexto = super().each_context(request)
        cor = settings.COR_PRIMARIA
        # Sobrescreve só os 3 tokens de cor confirmados no base.css do
        # Django 5.2 (--primary, --header-bg, --link-fg); nenhum outro
        # aspecto do tema do admin é tocado (D-14). O valor é seguro para o
        # |safe do template porque COR_PRIMARIA é validada como #RRGGBB no
        # boot (config/settings/base.py — T-02-01/T-02-06).
        contexto["admin_tema_css"] = (
            f":root {{ --primary: {cor}; --header-bg: {cor}; --link-fg: {cor}; }}"
        )
        return contexto
