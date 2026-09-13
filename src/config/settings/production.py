import os
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured

from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ["SECRET_KEY"]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = os.environ["ALLOWED_HOSTS"].split(",")


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


_smtp_use_tls = _env_bool("SMTP_USE_TLS", "true")
_smtp_use_ssl = _env_bool("SMTP_USE_SSL")

if _smtp_use_tls and _smtp_use_ssl:
    raise ImproperlyConfigured("SMTP_USE_TLS and SMTP_USE_SSL cannot both be enabled.")

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "OPTIONS": {
            "host": os.environ["SMTP_HOST"],
            "port": int(os.getenv("SMTP_PORT", "587")),
            "username": os.getenv("SMTP_USERNAME", ""),
            "password": os.getenv("SMTP_PASSWORD", ""),
            "use_tls": _smtp_use_tls,
            "use_ssl": _smtp_use_ssl,
            "timeout": int(os.getenv("SMTP_TIMEOUT", "10")),
        },
    },
}


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

database_url = urlparse(os.environ["DATABASE_URL"])

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": database_url.path.lstrip("/"),
        "USER": database_url.username,
        "PASSWORD": database_url.password,
        "HOST": database_url.hostname,
        "PORT": database_url.port or 5432,
    }
}


# HTTPS-only production hardening.
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
