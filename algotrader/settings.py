import os
from pathlib import Path
from datetime import datetime
import pytz

# --- CORE DJANGO CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'default-django-secret-key-for-dev')

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dashboard', # Our main application
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'algotrader.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # Added for general templates
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'algotrader.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- STATIC FILES CONFIGURATION (FIX FOR HEROKU) ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles' # <--- THIS LINE IS THE FIX
#STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage' # Optional for better serving

# --- TIMEZONE ---
IST = pytz.timezone("Asia/Kolkata")

# --- REDIS CONFIGURATION AND CHANNELS (LOW-LATENCY BUS) ---
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Channels for Pub/Sub communication
REDIS_DATA_CHANNEL = 'dhan_market_data'
REDIS_ORDER_UPDATE_CHANNEL = 'dhan_order_update'
REDIS_CANDLE_CHANNEL = 'dhan_candle_1m'
REDIS_CONTROL_CHANNEL = 'strategy_control_channel'
REDIS_AUTH_CHANNEL = 'auth_channel'

# Status Keys and Mappings
REDIS_STATUS_DATA_ENGINE = 'data_engine_status'
REDIS_STATUS_ALGO_ENGINE = 'algo_engine_status'
REDIS_DHAN_TOKEN_KEY = 'dhan_access_token'
PREV_DAY_HASH = 'prev_day_ohlc'
LIVE_OHLC_KEY = 'live_ohlc_data'
SYMBOL_ID_MAP_KEY = 'dhan_instrument_map'

# --- DHAN API CONFIGURATION KEYS ---
DHAN_CLIENT_ID = os.environ.get('DHAN_CLIENT_ID')
DHAN_ACCESS_TOKEN = os.environ.get('DHAN_ACCESS_TOKEN')

# --- STRATEGY CONSTANTS (used by algo_engine.py) ---
RISK_MULTIPLIER = 2.5
BREAKEVEN_TRIGGER_R = 1.25
MAX_MONITORING_MINUTES = 6

ENTRY_OFFSET_PCT = 0.0001
STOP_OFFSET_PCT = 0.0002
MAX_CANDLE_PCT = 0.007