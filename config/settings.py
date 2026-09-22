import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "insecure-development-key-change-me")
DEBUG = os.getenv("DEBUG", "1") == "1"
ALLOWED_HOSTS = [host for host in os.getenv("ALLOWED_HOSTS", "*").split(",") if host]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "stations",
    "trips",
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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / os.getenv("SQLITE_NAME", "db.sqlite3"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "OPTIONS": {"MAX_ENTRIES": 5000},
    }
}

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "EXCEPTION_HANDLER": "trips.exceptions.api_exception_handler",
    "UNAUTHENTICATED_USER": None,
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
}

# External services
OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org")
NOMINATIM_BASE_URL = os.getenv("NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org")
NOMINATIM_USER_AGENT = os.getenv("NOMINATIM_USER_AGENT", "fuel-route-planner/1.0")
EXTERNAL_API_TIMEOUT_SECONDS = float(os.getenv("EXTERNAL_API_TIMEOUT_SECONDS", "15"))
GEOCODE_CACHE_SECONDS = int(os.getenv("GEOCODE_CACHE_SECONDS", str(7 * 24 * 3600)))
ROUTE_CACHE_SECONDS = int(os.getenv("ROUTE_CACHE_SECONDS", str(24 * 3600)))

# Vehicle and planning parameters
VEHICLE_RANGE_MILES = float(os.getenv("VEHICLE_RANGE_MILES", "500"))
VEHICLE_MPG = float(os.getenv("VEHICLE_MPG", "10"))
STATION_CORRIDOR_MILES = float(os.getenv("STATION_CORRIDOR_MILES", "10"))
ROUTE_SAMPLE_MILES = float(os.getenv("ROUTE_SAMPLE_MILES", "1"))
EXTRA_COST_TOLERANCE_USD = float(os.getenv("EXTRA_COST_TOLERANCE_USD", "2"))

# Map page tiles (any Leaflet-compatible raster tile URL template)
MAP_TILE_URL = os.getenv(
    "MAP_TILE_URL",
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
)
MAP_TILE_ATTRIBUTION = os.getenv(
    "MAP_TILE_ATTRIBUTION",
    'Tiles &copy; <a href="https://www.esri.com/">Esri</a> &mdash; Esri, HERE, Garmin, USGS, Intermap, NRCAN, TomTom',
)

# Station data files
FUEL_PRICES_CSV = BASE_DIR / "data" / "fuel-prices-for-be-assessment.csv"
CITY_COORDINATES_FILE = BASE_DIR / "data" / "city_coordinates.json"
MAJOR_CITIES_FILE = BASE_DIR / "data" / "major_cities.json"
