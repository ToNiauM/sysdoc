from django.urls import path

from . import views

app_name = "processos"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("processos/novo/", views.novo_processo, name="novo"),
    path("processos/<slug:slug>/verificacao/", views.verificacao, name="verificacao"),
    path("processos/<slug:slug>/analise/", views.analise, name="analise"),
    path(
        "processos/<slug:slug>/analise/iniciar/",
        views.iniciar_analise,
        name="iniciar_analise",
    ),
    path(
        "processos/<slug:slug>/analise/situacao/",
        views.situacao_analise,
        name="situacao_analise",
    ),
]
