"""
Django settings for DarkGuard backend.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env.example")

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")

DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS: list[str] = [
    h.strip()
    for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

INSTALLED_APPS: list[str] = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "core",
    "dom_analyzer",
    "text_analyzer",
    "visual_analyzer",
    "review_analyzer",
    "consent_analyzer",
    "checkout_flow_analyzer",
    "subscription_analyzer",
    "privacy_analyzer",
    "nagging_analyzer",
    "pricing_analyzer",
    "scans",
]

MIDDLEWARE: list[str] = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "darkguard.urls"

TEMPLATES: list[dict[str, object]] = []

WSGI_APPLICATION = "darkguard.wsgi.application"

# Database — use PostgreSQL in production (DATABASE_URL set by Render)
# Falls back to SQLite for local development.
_db_url = os.getenv("DATABASE_URL", "")
if _db_url:
    import dj_database_url  # type: ignore[import-untyped]
    DATABASES: dict[str, dict[str, object]] = {
        "default": dj_database_url.config(default=_db_url, conn_max_age=600)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# DRF
REST_FRAMEWORK: dict[str, object] = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "UNAUTHENTICATED_USER": None,
}

# CORS — locked to chrome-extension:// and localhost for dev;
# in production add your Vercel dashboard URL via CORS_ALLOWED_ORIGINS env var.
_extra_cors = [
    o.strip()
    for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]
CORS_ALLOWED_ORIGIN_REGEXES: list[str] = [
    r"^chrome-extension://.*$",
]
CORS_ALLOWED_ORIGINS: list[str] = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://localhost:5173",
    *_extra_cors,
]

# Analyzer timeout (seconds)
ANALYZER_TIMEOUT: int = int(os.getenv("ANALYZER_TIMEOUT", "10"))

# Google GenAI
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

# NVIDIA NIM (optional)
NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")

# LLM Provider: "auto" (default), "gemini", "nvidia"
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto")
