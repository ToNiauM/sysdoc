def resposta_bloqueio(request, original_response, credentials=None):
    """Configurado em `AXES_LOCKOUT_CALLABLE`.

    Sem isto, `axes.middleware.AxesMiddleware` substitui a resposta de
    QUALQUER view por uma página HTML genérica própria (status
    `AXES_HTTP_RESPONSE_CODE`, default 429) sempre que
    `request.axes_locked_out` for `True` — mesmo quando a view já detectou o
    bloqueio e devolveu o fragmento correto em HTTP 200 (Pitfall 1: HTMX não
    faz swap de respostas 4xx/5xx). Sem este callable, a página genérica do
    axes sobrescreveria silenciosamente a resposta da view.
    """
    return original_response
