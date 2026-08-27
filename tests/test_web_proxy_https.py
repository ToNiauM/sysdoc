"""
Testes do reconhecimento de TLS terminado em proxy reverso.

Quando a aplicação roda atrás de um proxy que termina TLS (o caso de
`sysdoc.sistemascfc.org` atrás de Cloudflare/nginx), o container recebe HTTP
puro. Sem `SECURE_PROXY_SSL_HEADER`, `request.is_secure()` devolve `False` e
o Django monta URLs absolutas com esquema `http://`.

O reconhecimento é deliberadamente **opt-in** (`SYSDOC_WEB_ATRAS_DE_PROXY=1`):
confiar em `X-Forwarded-Proto` incondicionalmente permitiria a um cliente
forjar "conexão segura" caso a aplicação ficasse diretamente alcançável.
Estes testes travam as duas metades — o reconhecimento quando pedido e a
ausência dele quando não pedido.

Lê `sysdoc_web/settings.py` como texto, sem importar Django, para que o
módulo rode mesmo em ambiente sem o extra `web` instalado.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / "sysdoc_web" / "settings.py"


def _fonte() -> str:
    return SETTINGS.read_text(encoding="utf-8")


def _executar_settings(env: dict[str, str]) -> dict:
    """Executa o bloco de HTTPS/proxy do settings isoladamente."""
    ambiente = dict(env)
    escopo: dict = {}
    fonte = _fonte()
    inicio = fonte.index("_usar_https =")
    fim = fonte.index("SESSION_EXPIRE_AT_BROWSER_CLOSE")
    trecho = fonte[inicio:fim]
    exec(  # noqa: S102 - trecho do próprio repo, sem entrada externa
        "import os\n"
        "os.environ.clear()\n"
        "os.environ.update(_env)\n"
        "DEBUG = os.environ.get('SYSDOC_WEB_DEBUG', '0') == '1'\n" + trecho,
        {"_env": ambiente},
        escopo,
    )
    return escopo


class TestReconhecimentoDeProxy:
    def test_https_atras_de_proxy_confia_no_cabecalho(self):
        escopo = _executar_settings(
            {"SYSDOC_WEB_HTTPS": "1", "SYSDOC_WEB_ATRAS_DE_PROXY": "1"}
        )
        assert escopo["SECURE_PROXY_SSL_HEADER"] == ("HTTP_X_FORWARDED_PROTO", "https")
        assert escopo["USE_X_FORWARDED_HOST"] is True

    def test_https_sem_proxy_nao_confia_no_cabecalho(self):
        escopo = _executar_settings({"SYSDOC_WEB_HTTPS": "1"})
        assert "SECURE_PROXY_SSL_HEADER" not in escopo

    def test_sem_https_nunca_confia_no_cabecalho(self):
        escopo = _executar_settings({"SYSDOC_WEB_ATRAS_DE_PROXY": "1"})
        assert "SECURE_PROXY_SSL_HEADER" not in escopo

    def test_padrao_local_nao_confia_no_cabecalho(self):
        escopo = _executar_settings({})
        assert "SECURE_PROXY_SSL_HEADER" not in escopo
        assert escopo["SESSION_COOKIE_SECURE"] is False


class TestCookiesSeguros:
    def test_https_marca_cookies_como_seguros(self):
        escopo = _executar_settings({"SYSDOC_WEB_HTTPS": "1"})
        assert escopo["SESSION_COOKIE_SECURE"] is True
        assert escopo["CSRF_COOKIE_SECURE"] is True
