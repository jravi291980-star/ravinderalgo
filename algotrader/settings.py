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
STATIC_URL = '/static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- TIMEZONE ---
IST = pytz.timezone("Asia/Kolkata")

# --- REDIS CONFIGURATION AND CHANNELS (LOW-LATENCY BUS) ---
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Channels for Pub/Sub communication
REDIS_DATA_CHANNEL = 'dhan_market_data'          # MarketFeed (Ticks/Quotes) -> Algo Engine
REDIS_ORDER_UPDATE_CHANNEL = 'dhan_order_update' # OrderUpdate (Fill/Status) -> Algo Engine
REDIS_CANDLE_CHANNEL = 'dhan_candle_1m'          # Algo Engine (Aggregator) -> Algo Engine (Strategy)
REDIS_CONTROL_CHANNEL = 'strategy_control_channel' # Web Engine -> Algo Engine
REDIS_AUTH_CHANNEL = 'auth_channel'              # Web Engine -> All Workers

# Status Keys and Mappings
REDIS_STATUS_DATA_ENGINE = 'data_engine_status'
REDIS_STATUS_ALGO_ENGINE = 'algo_engine_status'
REDIS_DHAN_TOKEN_KEY = 'dhan_access_token'       # Centralized token storage
PREV_DAY_HASH = 'prev_day_ohlc'                  # Stores PDH/PDL from CMD 2
LIVE_OHLC_KEY = 'live_ohlc_data'                 # Stores current LTP snapshot from aggregator
SYMBOL_ID_MAP_KEY = 'dhan_instrument_map'        # Stores Security ID map from CMD 1

# --- DHAN API CONFIGURATION KEYS ---
DHAN_CLIENT_ID = os.environ.get('DHAN_CLIENT_ID')
DHAN_ACCESS_TOKEN = os.environ.get('DHAN_ACCESS_TOKEN')

# --- STRATEGY CONSTANTS (used by algo_engine.py) ---
RISK_MULTIPLIER = 2.5
BREAKEVEN_TRIGGER_R = 1.25
MAX_MONITORING_MINUTES = 6

# Default values for models (must be kept here for consistency, though models.py handles defaults)
ENTRY_OFFSET_PCT = 0.0001
STOP_OFFSET_PCT = 0.0002
MAX_CANDLE_PCT = 0.007