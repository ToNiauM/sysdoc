from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # As rotas do fluxo do pregoeiro vêm ANTES de `core.urls` de propósito.
    # Ambos declaram a raiz `""`: o núcleo com o shell vazio de exemplo, e o
    # SysDoc com a lista de processos. Quem resolve `/` é o primeiro match,
    # então a raiz é a lista — que é a página útil para quem entra. O nome
    # `core:shell` continua reverso para `/`, então o item "Início" da
    # navegação do núcleo aponta para a lista, sem precisar editar o partial
    # do núcleo (que é território de `copier update`).
    path("", include("sysdoc_web.processos.urls")),
    # Login, logout, manifesto da PWA e service worker vêm do núcleo — mesma
    # tela de entrada dos sistemas irmãos (pca, dividaativa).
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
