from django.urls import path

from core import views

app_name = "core"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # PWA na RAIZ do site (core.urls é incluído sem prefixo em config/urls.py):
    # o service worker nunca pode viver sob /static/ — o escopo dele fica
    # limitado ao caminho de onde é servido e a PWA não instala (D-19).
    path("manifest.json", views.manifest_view, name="manifest"),
    path("sw.js", views.service_worker_view, name="service_worker"),
    path("", views.shell_view, name="shell"),
]
