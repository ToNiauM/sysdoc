import os
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
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "sysdoc_web.processos",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "sysdoc_web.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "sysdoc_web" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
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

STATIC_URL = "/estatico/"
STATICFILES_DIRS = [BASE_DIR / "sysdoc_web" / "static"]
STATIC_ROOT = SYSDOC_WEB_DATA_DIR / "estatico"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/entrar/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/entrar/"

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
