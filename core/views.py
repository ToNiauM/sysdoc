from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_not_required
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.templatetags.static import static
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django_htmx.http import HttpResponseClientRedirect

from core.tema import COR_PAGE_CLARO


@login_not_required
def healthz(request):
    """Rota de healthcheck (usada pelo `compose.yml` — Plan 01-03).

    Sem `@login_not_required`, o `LoginRequiredMiddleware` (Pitfall 9)
    redirecionaria toda requisição sem sessão para `/login/`, quebrando o
    healthcheck do container.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "error"}, status=503)
    return JsonResponse({"status": "ok"})


def _redirecionar(request, destino):
    """Redirect pós-autenticação ciente de htmx (CR-01).

    Requisição htmx precisa de `HX-Redirect` (Pitfall 2): um 302 comum
    seria seguido pelo próprio XHR e o htmx faria swap do HTML da página de
    destino dentro do alvo do form, em vez de navegar. Já um POST
    tradicional (o fallback no-JS dos forms de login/logout, que declaram
    `method="post"`/`action`) precisa do 302 real — a resposta
    `HX-Redirect` é um 200 de corpo vazio, que um navegador sem JS
    renderizaria como página em branco.
    """
    if request.htmx:
        return HttpResponseClientRedirect(destino)
    return redirect(destino)


@login_not_required
def login_view(request):
    """GET renderiza a tela de login; POST autentica (CORE-02).

    O POST atende dois caminhos: o principal via htmx (fragmento
    `_login_form.html` no erro, `HX-Redirect` no sucesso) e o fallback
    no-JS do form (página completa no erro, 302 real no sucesso) — ver
    `_redirecionar` e o comentário em `_login_form.html` (CR-01).

    Nunca envolve `authenticate()` com `except PermissionDenied`: o
    dispatcher de alto nível do Django (`django.contrib.auth.authenticate`)
    captura o `PermissionDenied` que o `AxesBackend` levanta internamente e
    NUNCA o repassa para quem chamou — só devolve `None` (comportamento
    documentado). A forma correta de distinguir "bloqueado pelo axes" de
    "credenciais erradas comuns" é o atributo `request.axes_locked_out`, que
    o `AxesBackend` seta no request antes de levantar (e sobrevive à captura
    silenciosa do dispatcher) — ver Pitfall 3/4 do 01-RESEARCH.md.
    """
    if request.method != "POST":
        # `next` chega via querystring no GET (posto lá pelo
        # `LoginRequiredMiddleware`) e precisa ser propagado para o template
        # como campo oculto do form — sem isto, o POST subsequente nunca
        # carrega o destino e o redirect pós-login sempre cai em "/"
        # (CR-01).
        return TemplateResponse(
            request, "core/login.html", {"next": request.GET.get("next", "")}
        )

    email = request.POST.get("email", "")
    senha = request.POST.get("password", "")
    next_bruto = request.POST.get("next", "")

    user = authenticate(request, username=email, password=senha)

    if user is None:
        bloqueado = bool(getattr(request, "axes_locked_out", False))
        # htmx troca só o fragmento do form (hx-swap="outerHTML"); o POST
        # tradicional do fallback no-JS precisa da página completa — devolver
        # o fragmento cru deixaria o usuário sem layout/estilo (CR-01).
        template_erro = (
            "core/_login_form.html" if request.htmx else "core/login.html"
        )
        return TemplateResponse(
            request,
            template_erro,
            {
                "email": email,
                # Preserva `next` também no branch de erro/bloqueio — senão
                # se perde já na segunda tentativa após uma senha errada.
                "next": next_bruto,
                "bloqueado": bloqueado,
                "erro": not bloqueado,
            },
            status=200,  # nunca 4xx puro — htmx não faz swap por padrão (Pitfall 1)
        )

    login(request, user)

    # Proteção contra open redirect (T-04-03): `?next=` é entrada controlada
    # pelo cliente. `url_has_allowed_host_and_scheme` garante que só um
    # caminho relativo ao próprio host é aceito como destino. O campo oculto
    # do form é a fonte primária (é o que o ciclo GET→POST real usa); o
    # fallback em `request.GET` cobre o caso raro de um POST direto para
    # `/login/?next=...` (ex.: chamada programática/teste).
    destino_bruto = next_bruto or request.GET.get("next")
    if destino_bruto and url_has_allowed_host_and_scheme(
        destino_bruto,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        destino = destino_bruto
    else:
        destino = "/"

    return _redirecionar(request, destino)


@require_POST
def logout_view(request):
    logout(request)
    return _redirecionar(request, "/login/")


def shell_view(request):
    """Shell autenticado completo (CORE-04): aside + gaveta mobile + blocos.

    Sem `@login_not_required`: precisa de sessão válida, o que o
    `LoginRequiredMiddleware` já garante por padrão (Pitfall 9).

    Contrato `trilha` (D-12): a view monta os breadcrumbs como uma lista de
    dicts `{"rotulo": str, "url": str|None}` a partir de dados JÁ presentes
    no contexto — o partial `core/_breadcrumbs.html` só renderiza, nunca
    consulta banco nem usa templatetag com ORM por trás. O ÚLTIMO item é
    sempre a página atual e nunca carrega `url`. A trilha abaixo, de item
    único, é o exemplo vivo do contrato que as views de domínio copiam.
    """
    trilha = [{"rotulo": "Início", "url": None}]
    return TemplateResponse(request, "core/shell.html", {"trilha": trilha})


@login_not_required
def manifest_view(request):
    """`manifest.json` servido por view, não arquivo estático puro (D-18).

    Sem `@login_not_required` o `LoginRequiredMiddleware` devolveria 302 para
    `/login/` e a PWA nunca instalaria (Pitfall 5).

    Em produção o `CompressedManifestStaticFilesStorage` do WhiteNoise hasheia
    o nome de cada ícone (`icon-192.abcd1234.png`); um `.json` estático com
    `"/static/img/icon-192.png"` literal 404aria depois do primeiro
    `collectstatic` — e só em produção, mascarando o bug em dev (Pitfall 3).
    Resolvendo via `static()` aqui, o corpo do manifest sempre aponta para o
    nome real do arquivo, hasheado ou não.
    """
    dados = {
        # Identidade 100% via settings (D-16/D-17): o manifest muda de nome e
        # cor junto com o `.env` do sistema gerado, sem tocar em código.
        "name": settings.SISTEMA_NOME,
        "short_name": settings.SISTEMA_SIGLA,
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        # Vem de core.tema.COR_PAGE_CLARO, que espelha o --cor-page do
        # bloco :root de input.css e está amarrado a ele por teste
        # (core/tests/test_tema.py) — sem duplicata literal. Neutro de
        # template, não identidade (A3): não entra na regra dos dois
        # touchpoints de D-17.
        "background_color": COR_PAGE_CLARO,
        "theme_color": settings.COR_PRIMARIA,
        "icons": [
            {
                "src": static("img/icon-192.png"),
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": static("img/icon-512.png"),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": static("img/icon-512-maskable.png"),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
    }
    return JsonResponse(dados, content_type="application/manifest+json")


@login_not_required
def service_worker_view(request):
    """`sw.js` hand-rolled (D-19, sem Workbox) — só cacheia `/static/`.

    Servido por rota de raiz (nunca `/static/sw.js` — isso limitaria o escopo
    do SW a `/static/` e a PWA não instalaria, Pitfall 4) com o header
    `Service-Worker-Allowed: /` explícito. Estratégia mínima e auditável:
    precache da página offline no `install` e fallback de navegação quando a
    rede falha. HTML, fragmentos HTMX e JSON nunca são interceptados — só GET
    de mesma origem sob `/static/`. Cachear HTML autenticado deixaria
    conteúdo de sessão legível no Cache Storage após o logout (T-02-10).
    """
    offline_url = static("offline.html")
    texto = (
        "// CACHE_NAME versionado manualmente — faça bump do sufixo sempre que\n"
        "// o formato do conjunto de estáticos cacheados mudar; o `activate`\n"
        "// abaixo apaga qualquer cache com nome diferente. O Cache Storage é\n"
        "// escopado por origem, então o nome neutro não colide entre sistemas.\n"
        'const CACHE_NAME = "static-v1";\n'
        f'const OFFLINE_URL = "{offline_url}";\n'
        "\n"
        'self.addEventListener("install", (event) => {\n'
        "  self.skipWaiting();\n"
        "  event.waitUntil(\n"
        "    caches.open(CACHE_NAME).then((cache) => cache.addAll([OFFLINE_URL]))\n"
        "  );\n"
        "});\n"
        "\n"
        'self.addEventListener("fetch", (event) => {\n'
        "  const url = new URL(event.request.url);\n"
        "\n"
        "  // Navegação (troca de página): sempre tenta a rede primeiro; só cai\n"
        "  // para a página offline quando a rede falha de fato — NUNCA serve\n"
        "  // nem grava HTML em cache (o respondWith abaixo não tem cache.put:\n"
        "  // HTML autenticado no Cache Storage vazaria conteúdo após logout).\n"
        '  if (event.request.mode === "navigate") {\n'
        "    event.respondWith(\n"
        "      fetch(event.request).catch(() => caches.match(OFFLINE_URL))\n"
        "    );\n"
        "    return;\n"
        "  }\n"
        "\n"
        "  // 1) só GET, 2) só mesma origem, 3) SÓ /static/. Todo o resto passa\n"
        "  // direto (sem respondWith nenhum) — HTML, fragmentos HTMX e JSON\n"
        "  // nunca entram no Cache Storage.\n"
        '  if (event.request.method !== "GET") return;\n'
        "  if (url.origin !== location.origin) return;\n"
        '  if (!url.pathname.startsWith("/static/")) return;\n'
        "  event.respondWith(\n"
        "    caches.match(event.request).then((r) => r || fetch(event.request).then((resp) => {\n"
        '      if (resp.ok && resp.type === "basic") {\n'
        "        const c = resp.clone();\n"
        "        caches.open(CACHE_NAME).then((k) => k.put(event.request, c));\n"
        "      }\n"
        "      return resp;\n"
        "    }))\n"
        "  );\n"
        "});\n"
        "\n"
        'self.addEventListener("activate", (event) => event.waitUntil(\n'
        "  caches.keys().then((ks) => Promise.all(\n"
        "    ks.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))\n"
        "  )).then(() => self.clients.claim())\n"
        "));\n"
    )
    resposta = HttpResponse(texto, content_type="application/javascript")
    resposta["Service-Worker-Allowed"] = "/"
    return resposta
