"""Réglages Django. Les valeurs sensibles viennent du fichier .env (voir .env.example)."""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_list(nom: str, defaut: str = "") -> list[str]:
    """Liste séparée par des virgules ; une variable vide dans .env prend la valeur par défaut."""
    return [v.strip() for v in (os.environ.get(nom) or defaut).split(",") if v.strip()]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-uniquement-a-changer")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
# En développement, Django accepte toutes les adresses : le site s'ouvre depuis
# une autre machine du réseau (http://192.168.x.x:3000). En production, lister les domaines.
ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    "*" if DEBUG else "jessnaevent.pythonanywhere.com,jessna-event.vercel.app,localhost,127.0.0.1",
)

# Next.js transmet /api et /media à Django en indiquant l'adresse d'origine
# (X-Forwarded-Host / X-Forwarded-Proto) : les liens et les images construits
# par Django utilisent alors l'adresse que l'invité ou l'agent a ouverte.
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Adresse publique du site, pour les QR codes (FRONTEND_URL/i/<code>).
# Vide = automatique, d'après l'adresse utilisée pour ouvrir le site.
FRONTEND_URL = os.environ.get("FRONTEND_URL", "").rstrip("/")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "invitations",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# PostgreSQL en production (DATABASE_URL), SQLite par défaut pour démarrer vite.
DATABASES = {
    "default": dj_database_url.parse(
        os.environ.get("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr"
TIME_ZONE = "Africa/Kinshasa"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Le front Next.js tourne sur une autre adresse : on l'autorise explicitement.
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    ",".join(filter(None, (
        FRONTEND_URL,
        "https://jessna-event.vercel.app",
        "https://jessnaevent.pythonanywhere.com",
    ))),
)
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # Limites par adresse IP : un agent qui scanne en boucle ou un robot qui
    # essaie des mots de passe ne peut pas tester des milliers de valeurs.
    "DEFAULT_THROTTLE_RATES": {
        "scan": "120/min",
        "connexion": "10/min",
        "pin": "10/min",
        "invitation": "600/min",
    },
}

# Next.js (localhost:3000) envoie le cookie de session à Django (localhost:8000).
CORS_ALLOW_CREDENTIALS = True
# Le scanner de l'agent envoie son jeton dans cet en-tête.
from corsheaders.defaults import default_headers  # noqa: E402

CORS_ALLOW_HEADERS = (*default_headers, "x-agent-token")
