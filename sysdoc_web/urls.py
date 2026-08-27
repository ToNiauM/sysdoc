from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("entrar/", LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("sair/", LogoutView.as_view(http_method_names=["post"]), name="logout"),
    path("", include("sysdoc_web.processos.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
