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
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "darkguard.urls"

TEMPLATES: list[dict[str, object]] = []

WSGI_APPLICATION = "darkguard.wsgi.application"

DATABASES: dict[str, dict[str, object]] = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "/static/"

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

# CORS — locked to chrome-extension:// and localhost for dev
CORS_ALLOWED_ORIGIN_REGEXES: list[str] = [
    r"^chrome-extension://.*$",
]
CORS_ALLOWED_ORIGINS: list[str] = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://localhost:5173",
]

# Analyzer timeout (seconds)
ANALYZER_TIMEOUT: int = int(os.getenv("ANALYZER_TIMEOUT", "10"))

# Google GenAI
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

# NVIDIA NIM (optional)
NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")

# LLM Provider: "auto" (default), "gemini", "nvidia"
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto")
