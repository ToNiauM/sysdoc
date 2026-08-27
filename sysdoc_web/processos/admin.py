"""
Admin somente leitura (D-14/D-15 — o admin serve para o administrador
inspecionar o estado da fila, não para operar o fluxo de análise).
"""

from django.contrib import admin

from .models import AnaliseJob, Processo


class SomenteLeituraAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Processo)
class ProcessoAdmin(SomenteLeituraAdmin):
    list_display = ("nome", "slug", "tipo_verificacao", "criado_por", "criado_em")
    search_fields = ("nome", "slug")


@admin.register(AnaliseJob)
class AnaliseJobAdmin(SomenteLeituraAdmin):
    list_display = ("processo", "status", "etapa", "itens_concluidos", "itens_total", "criado_em")
    list_filter = ("status",)
