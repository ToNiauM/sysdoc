import os
import re
import secrets
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("SYSDOC_WEB_DEBUG", "0") == "1"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = secrets.token_urlsafe(50)
    else:
        raise ImproperlyConfigured(
            "A variável de ambiente DJANGO_SECRET_KEY é obrigatória fora do "
            "modo de depuração (SYSDOC_WEB_DEBUG=1)."
        )

_allowed_hosts_env = os.environ.get("SYSDOC_WEB_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = (
    [h.strip() for h in _allowed_hosts_env.split(",") if h.strip()]
    if _allowed_hosts_env
    else ["localhost", "127.0.0.1"]
)

_csrf_origins_env = os.environ.get("SYSDOC_WEB_CSRF_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins_env.split(",") if o.strip()]

SYSDOC_WEB_DATA_DIR = Path(os.environ.get("SYSDOC_WEB_DATA_DIR", BASE_DIR / "dados_web"))
SYSDOC_PROCESSOS_DIR = SYSDOC_WEB_DATA_DIR / "processos"
SYSDOC_PROCESSOS_DIR.mkdir(parents=True, exist_ok=True)

SYSDOC_WEB_MAX_UPLOAD_MB = int(os.environ.get("SYSDOC_WEB_MAX_UPLOAD_MB", "50"))
SYSDOC_WEB_MAX_ARQUIVOS = int(os.environ.get("SYSDOC_WEB_MAX_ARQUIVOS", "20"))

INSTALLED_APPS = [
    "whitenoise.runserver_nostatic",
    "core.apps.CoreConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Substitui a entrada plain do app admin do Django (nunca coexistir com
    # ela — duas configs do mesmo app geram "Application labels aren't unique").
    "core.apps.SistemaAdminConfig",
    "django_htmx",
    "simple_history",
    "sysdoc_web.processos",
]

# A ordem do MIDDLEWARE é normativa — copiada dos sistemas irmãos que já
# rodam sobre o mesmo núcleo (pca, dividaativa). Não reordenar sem entender
# o motivo de cada posição.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # Serve /estatico/ direto do processo. Sem isto o collectstatic roda,
    # copia os arquivos e ninguém os entrega: o gunicorn não serve estático
    # com DEBUG=False e o nginx repassa tudo para a aplicação — a página
    # sai sem folha de estilo nenhuma, com 404 silencioso no CSS.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Precisa vir DEPOIS do AuthenticationMiddleware para capturar
    # request.user como history_user em toda escrita auditada.
    "simple_history.middleware.HistoryRequestMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "core.middleware.HtmxRedirectMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    # Exige sessão em TODA view por padrão; as exceções do núcleo (login,
    # manifest, service worker) são marcadas com @login_not_required.
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
]

AUTH_USER_MODEL = "core.Usuario"

ROOT_URLCONF = "sysdoc_web.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # `core/templates` primeiro: é de onde vêm `base.html` e
        # `core/shell.html`, que as telas do fluxo estendem. O diretório
        # `templates/` da raiz do repositório (modelos imutáveis da análise:
        # `analise_template.html`) NÃO entra aqui de propósito — ele não é
        # material de interface web e é renderizado por
        # `templates/render_analise.py`, nunca pelo Django.
        "DIRS": [
            BASE_DIR / "core" / "templates",
            BASE_DIR / "sysdoc_web" / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.usuario_atual",
                "core.context_processors.identidade",
            ],
        },
    },
]

WSGI_APPLICATION = "sysdoc_web.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": SYSDOC_WEB_DATA_DIR / "db.sqlite3",
        "OPTIONS": {"timeout": 20},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# Identidade do sistema, consumida por `core.context_processors.identidade`
# em base.html, shell, login, admin e manifesto da PWA. Fonte única — nunca
# repetir o nome do sistema dentro de template.
SISTEMA_NOME = os.environ.get("SISTEMA_NOME", "SysDoc")
SISTEMA_SIGLA = os.environ.get("SISTEMA_SIGLA", "SysDoc")
COR_PRIMARIA = os.environ.get("COR_PRIMARIA", "#1d4ed8")

if not re.fullmatch(r"#[0-9a-fA-F]{6}", COR_PRIMARIA):
    raise ImproperlyConfigured(
        "COR_PRIMARIA deve estar no formato hexadecimal #RRGGBB; "
        f"valor recebido: {COR_PRIMARIA!r}. Corrija o .env antes de subir."
    )

STATIC_URL = "/estatico/"
STATICFILES_DIRS = [
    BASE_DIR / "core" / "static",
    BASE_DIR / "sysdoc_web" / "static",
]
STATIC_ROOT = SYSDOC_WEB_DATA_DIR / "estatico"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

_usar_https = os.environ.get("SYSDOC_WEB_HTTPS", "0") == "1"
SESSION_COOKIE_SECURE = (not DEBUG) if _usar_https else False
CSRF_COOKIE_SECURE = (not DEBUG) if _usar_https else False

if _usar_https and os.environ.get("SYSDOC_WEB_ATRAS_DE_PROXY", "0") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

DATA_UPLOAD_MAX_MEMORY_SIZE = SYSDOC_WEB_MAX_UPLOAD_MB * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FILES = SYSDOC_WEB_MAX_ARQUIVOS

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "sysdoc_web": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}
