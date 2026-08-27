from django.urls import path

from . import views

app_name = "processos"

urlpatterns = [
    path("", views.inicio, name="inicio"),
]
