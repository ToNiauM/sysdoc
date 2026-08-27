# Import aliased de propósito (nunca `from ... import AdminConfig`): o Django
# enumera as classes acessíveis como atributo deste módulo ao resolver o
# AppConfig default do app "core"; com o alias, só SistemaAdminConfig (a
# subclasse) fica visível — a AdminConfig original não vira candidata.
import django.contrib.admin.apps as _django_admin_apps
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"


class SistemaAdminConfig(_django_admin_apps.AdminConfig):
    """Troca o `AdminSite` padrão do Django pelo `SistemaAdminSite` (D-13).

    Não redeclara `name` — herda `"django.contrib.admin"` de `AdminConfig`,
    o que é obrigatório para o Django reconhecer esta subclasse como a
    configuração do app admin. `config/urls.py` não muda: `admin.site` é um
    `LazyObject` que lê o site configurado aqui na primeira resolução.
    """

    # "core.admin_site" (não "core.admin"): o site vive num módulo sem nenhum
    # register próprio — ver docstring de core/admin_site.py (reentrância do
    # LazyObject apaga registros em silêncio).
    default_site = "core.admin_site.SistemaAdminSite"
    # Fora da lista de candidatos automáticos da entrada "core" de
    # INSTALLED_APPS; esta config é referenciada de forma explícita
    # ("core.apps.SistemaAdminConfig"), então não depende de autodiscovery.
    default = False
