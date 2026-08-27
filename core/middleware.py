from django_htmx.http import HttpResponseClientRedirect


class HtmxRedirectMiddleware:
    """Converte qualquer 301/302 numa requisição htmx em HX-Redirect.

    Sem isto, o XHR do htmx segue o redirect de forma transparente e o
    navegador troca o alvo do swap por uma página inteira — o caso letal é
    a expiração de sessão: o `<form>` de login inteiro aparece aninhado
    dentro do fragmento de um elemento qualquer (Pitfall 2). Precisa vir
    DEPOIS de `django_htmx.middleware.HtmxMiddleware`, que é quem popula
    `request.htmx`.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if getattr(request, "htmx", False) and response.status_code in (301, 302):
            # `.get()` em vez de `[...]` (IN-01): degrada devolvendo a
            # resposta original em vez de estourar KeyError, caso um
            # 301/302 chegue sem header `Location` (não acontece hoje — todo
            # redirect passa por `redirect_to_login()` ou por
            # `HttpResponseClientRedirect` explícito — mas protege contra
            # regressão futura de view/middleware de terceiros).
            destino = response.get("Location")
            if destino:
                return HttpResponseClientRedirect(destino)
        return response
