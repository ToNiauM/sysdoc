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
    path("processos/<slug:slug>/resultado/", views.resultado, name="resultado"),
    path("processos/<slug:slug>/despacho/", views.gerar_despacho, name="gerar_despacho"),
    path(
        "processos/<slug:slug>/baixar/analise/",
        views.baixar_analise,
        name="baixar_analise",
    ),
    path(
        "processos/<slug:slug>/baixar/despacho/",
        views.baixar_despacho,
        name="baixar_despacho",
    ),
]
