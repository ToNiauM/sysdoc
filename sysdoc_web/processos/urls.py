from django.urls import path

from . import views

app_name = "processos"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("processos/novo/", views.novo_processo, name="novo"),
    path("processos/<slug:slug>/verificacao/", views.verificacao, name="verificacao"),
]
