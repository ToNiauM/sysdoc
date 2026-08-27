import simple_history
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from core.models import Usuario

# User model customizado NÃO pode declarar `HistoricalRecords()` no próprio
# modelo: a FK de `history_user` da tabela histórica aponta para o user model,
# criando dependência circular num model swappable. A forma oficial documentada
# pelo django-simple-history é registrar via `register()` (D-22). Os modelos de
# domínio comuns seguem a convenção normal — `history = HistoricalRecords()`
# declarado no modelo (D-23, ver core/README.md).
#
# `excluded_fields` (WR-01): sem a exclusão, TODO save snapshotaria o hash
# Argon2 em `core_historicalusuario` — inclusive o `update_last_login` que o
# signal `user_logged_in` dispara a cada login. Um dump do banco exporia o
# histórico completo de hashes do usuário (senhas antigas, possivelmente mais
# fracas/reutilizadas, atacáveis offline mesmo depois de rotacionadas). O
# evento "senha trocada" continua auditável pelo próprio registro `~` do
# save; o que nunca pode existir é o hash em si na tabela histórica.
# Nota: o simple-history ainda grava um registro por save (o `post_save` não
# olha `update_fields`), então cada login segue gerando uma linha `~` — mas
# sem hash nem last_login, ela não retém nenhum dado sensível.
simple_history.register(Usuario, excluded_fields=["password", "last_login"])


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """`UserAdmin` padrão do Django adaptado para login por e-mail.

    Os `fieldsets`/`add_fieldsets` herdados referenciam o campo de login
    padrão do Django, que `core.Usuario` não tem — por isso são reescritos
    aqui. Sem ações em massa (D-15); se alguma entrar no futuro, deve
    persistir via `bulk_update_with_history` (queryset.update() não gera
    histórico).
    """

    ordering = ("email",)
    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "last_login",
    )
    search_fields = ("email", "first_name", "last_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informações pessoais", {"fields": ("first_name", "last_name")}),
        (
            "Permissões",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Datas importantes", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )
