import os
from pathlib import Path
from datetime import datetime, timedelta
import pytz
import dj_database_url # For configuring PostgreSQL connection

# --- CORE DJANGO CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-default-key-for-local-dev-change-me')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# Allow all hosts (*) for Heroku deployment
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dashboard', # Our main application containing models and dashboard UI
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise middleware should be used immediately after SecurityMiddleware for static files
    # 'whitenoise.middleware.WhiteNoiseMiddleware', # Add if you install whitenoise package
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
        'DIRS': [BASE_DIR / 'templates'], 
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


# --- DATABASE CONFIGURATION (PostgreSQL/SQLite Switch) ---
# Default to SQLite for local development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Overwrite default settings using the DATABASE_URL environment variable 
# provided by Heroku PostgreSQL addon.
DB_FROM_ENV = dj_database_url.config(conn_max_age=600)
if DB_FROM_ENV:
    DATABASES['default'] = DB_FROM_ENV


# --- Password Validation, Time Zones, and i18n ---
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

# --- STATIC FILES CONFIGURATION (FIX FOR HEROKU DEPLOYMENT) ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles' # <-- REQUIRED for 'collectstatic' in production


# --- TIMEZONE CONSTANTS ---
IST = pytz.timezone("Asia/Kolkata")


# -------------------------------------------------------------------
# --- REDIS CONFIGURATION AND CHANNELS (LOW-LATENCY BUS) ---
# -------------------------------------------------------------------

# REDIS_URL environment variable is set by Heroku Redis Addon
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Channels for Pub/Sub communication
REDIS_DATA_CHANNEL = 'dhan_market_data'       # Raw Ticks/Full Packet data
REDIS_ORDER_UPDATE_CHANNEL = 'dhan_order_update' # Real-time fill status
REDIS_CANDLE_CHANNEL = 'dhan_candle_1m'      # Completed 1-minute candles
REDIS_CONTROL_CHANNEL = 'strategy_control_channel' # Dashboard control signals
REDIS_AUTH_CHANNEL = 'auth_channel'          # Token refresh signals

# Status Keys and Mappings
REDIS_STATUS_DATA_ENGINE = 'data_engine_status'
REDIS_STATUS_ALGO_ENGINE = 'algo_engine_status'
REDIS_DHAN_TOKEN_KEY = 'dhan_access_token'   # Key where live token is stored
PREV_DAY_HASH = 'prev_day_ohlc'             # T-1 High/Low/Close data
LIVE_OHLC_KEY = 'live_ohlc_data'            # Current LTP snapshot for monitoring
SYMBOL_ID_MAP_KEY = 'dhan_instrument_map'   # Symbol to Security ID mapping

# -------------------------------------------------------------------
# --- DHAN API & STRATEGY CONSTANTS ---
# -------------------------------------------------------------------

# DHAN API & AUTH KEYS (MUST BE SET VIA HEROKU CONFIG VARS)
DHAN_CLIENT_ID = os.environ.get('DHAN_CLIENT_ID')
DHAN_API_SECRET = os.environ.get('DHAN_API_SECRET') # Needed for programmatic token exchange
DHAN_REDIRECT_URI = os.environ.get('DHAN_REDIRECT_URI') # e.g., https://your-app.herokuapp.com/dhan-callback/

# --- STRATEGY CONSTANTS (used by algo_engine.py) ---
RISK_MULTIPLIER = 2.5
BREAKEVEN_TRIGGER_R = 1.25
MAX_MONITORING_MINUTES = 6

ENTRY_OFFSET_PCT = 0.0001
STOP_OFFSET_PCT = 0.0002
MAX_CANDLE_PCT = 0.007

# --- NIFTY 500 SYMBOL LIST (REQUIRED FOR CACHING/FILTERING) ---
NIFTY_500_STOCKS=[
    '360ONE', '3MINDIA', 'AADHARHFC', 'AARTIIND', 'AAVAS', 'ABB', 'ABBOTINDIA', 'ABCAPITAL', 'ABFRL', 'ABLBL', 'ABREL', 'ABSLAMC', 'ACC', 'ACE', 'ACMESOLAR', 'ADANIENSOL', 'ADANIENT', 'ADANIGREEN', 'ADANIPORTS', 'ADANIPOWER', 'ADVENTHTL', 'AEGISLOG', 'AEGISVOPAK', 'AFCONS', 'AFFLE', 'AGARWALEYE', 'AIAENG', 'AIIL', 'AJANTPHARM', 'AKUMS', 'AKZOINDIA', 'ALKEM', 'ALKYLAMINE', 'ALOKINDS', 'AMBER', 'AMBUJACEM', 'ANANDRATHI', 'ANANTRAJ', 'ANGELONE', 'APARINDS', 'APLAPOLLO', 'APLLTD', 'APOLLOHOSP', 'APOLLOTYRE', 'APTUS', 'ARE&M', 'ASAHIINDIA', 'ASHOKLEY', 'ASIANPAINT', 'ASTERDM', 'ASTRAL', 'ASTRAMICRO', 'ASTRAZEN', 'ATGL', 'ATHERENERG', 'ATUL', 'AUBANK', 'AUROPHARMA', 'AWL', 'AXISBANK', 'BAJAJ-AUTO', 'BAJAJFINSV', 'BAJAJHFL', 'BAJAJHLDNG', 'BAJFINANCE', 'BALKRISIND', 'BALRAMCHIN', 'BANDHANBNK', 'BANKBARODA', 'BANKINDIA', 'BASF', 'BATAINDIA', 'BAYERCROP', 'BBTC', 'BDL', 'BEL', 'BEML', 'BERGEPAINT', 'BHARATFORG', 'BHARTIARTL', 'BHARTIHEXA', 'BHEL', 'BIKAJI', 'BIOCON', 'BLS', 'BLUEDART', 'BLUEJET', 'BLUESTARCO', 'BOSCHLTD', 'BPCL', 'BRIGADE', 'BRITANNIA', 'BSE', 'BSOFT', 'CAMPUS', 'CAMS', 'CANBK', 'CANFINHOME', 'CAPLIPOINT', 'CARBORUNIV', 'CASTROLIND', 'CCL', 'CDSL', 'CEATLTD', 'CENTRALBK', 'CENTURYPLY', 'CERA', 'CESC', 'CGCL', 'CGPOWER', 'CHALET', 'CHAMBLFERT', 'CHENNPETRO', 'CHOICEIN', 'CHOLAFIN', 'CHOLAHLDNG', 'CIPLA', 'CLEAN', 'COALINDIA', 'COCHINSHIP', 'COFORGE', 'COHANCE', 'COLPAL', 'CONCOR', 'CONCORDBIO', 'COROMANDEL', 'CRAFTSMAN', 'CREDITACC', 'CRISIL', 'CROMPTON', 'CUB', 'CUMMINSIND', 'CYIENT', 'CYIENTDLM', 'DABUR', 'DALBHARAT', 'DATAPATTNS', 'DBCORP', 'DBREALTY', 'DCMSHRIRAM', 'DCXINDIA', 'DEEPAKFERT', 'DEEPAKNTR', 'DELHIVERY', 'DEVYANI', 'DIVISLAB', 'DIXON', 'DLF', 'DMART', 'DOMS', 'DRREDDY', 'DYNAMATECH', 'ECLERX', 'EICHERMOT', 'EIDPARRY', 'EIHOTEL', 'ELECON', 'ELGIEQUIP', 'EMAMILTD', 'EMCURE', 'ENDURANCE', 'ENGINERSIN', 'ENRIN', 'ERIS', 'ESCORTS', 'ETERNAL', 'EXIDEIND', 'FACT', 'FEDERALBNK', 'FINCABLES', 'FINPIPE', 'FIRSTCRY', 'FIVESTAR', 'FLUOROCHEM', 'FORCEMOT', 'FORTIS', 'FSL', 'GAIL', 'GESHIP', 'GICRE', 'GILLETTE', 'GLAND', 'GLAXO', 'GLENMARK', 'GMDCLTD', 'GMRAIRPORT', 'GODFRYPHLP', 'GODIGIT', 'GODREJAGRO', 'GODREJCP', 'GODREJIND', 'GODREJPROP', 'GPIL', 'GRANULES', 'GRAPHITE', 'GRASIM', 'GRAVITA', 'GRSE', 'GSPL', 'GUJGASLTD', 'GVT&D', 'HAL', 'HAPPSTMNDS', 'HATHWAY', 'HAVELLS', 'HBLENGINE', 'HCLTECH', 'HDFCAMC', 'HDFCBANK', 'HDFCLIFE', 'HEG', 'HEROMOTOCO', 'HEXT', 'HFCL', 'HINDALCO', 'HINDCOPPER', 'HINDPETRO', 'HINDUNILVR', 'HINDZINC', 'HOMEFIRST', 'HONASA', 'HONAUT', 'HSCL', 'HUDCO', 'HYUNDAI', 'ICICIBANK', 'ICICIGI', 'ICICIPRULI', 'IDBI', 'IDEA', 'IDFCFIRSTB', 'IEX', 'IFCI', 'IGIL', 'IGL', 'IIFL', 'IKS', 'INDGN', 'INDHOTEL', 'INDIACEM', 'INDIAMART', 'INDIANB', 'INDIGO', 'INDUSINDBK', 'INDUSTOWER', 'INFY', 'INOXINDIA', 'INOXWIND', 'INTELLECT', 'IOB', 'IOC', 'IPCALAB', 'IRB', 'IRCON', 'IRCTC', 'IREDA', 'IRFC', 'ITC', 'ITCHOTELS', 'ITI', 'J&KBANK', 'JBCHEPHARM', 'JBMA', 'JINDALSAW', 'JINDALSTEL', 'JIOFIN', 'JKCEMENT', 'JKTYRE', 'JMFINANCIL', 'JPPOWER', 'JSL', 'JSWENERGY', 'JSWINFRA', 'JSWSTEEL', 'JUBLFOOD', 'JUBLINGREA', 'JUBLPHARMA', 'JWL', 'JYOTHYLAB', 'JYOTICNC', 'KAJARIACER', 'KALYANKJIL', 'KARURVYSYA', 'KAYNES', 'KEC', 'KEI', 'KFINTECH', 'KIMS', 'KIRLOSBROS', 'KIRLOSENG', 'KOTAKBANK', 'KPIL', 'KPITTECH', 'KPRMILL', 'KSB', 'LALPATHLAB', 'LATENTVIEW', 'LAURUSLABS', 'LEMONTREE', 'LICHSGFIN', 'LICI', 'LINDEINDIA', 'LLOYDSME', 'LODHA', 'LT', 'LTF', 'LTFOODS', 'LTIM', 'LTTS', 'LUPIN', 'M&M', 'M&MFIN', 'MAHABANK', 'MAHSCOOTER', 'MAHSEAMLES', 'MANAPPURAM', 'MANKIND', 'MANYAVAR', 'MAPMYINDIA', 'MARICO', 'MARUTI', 'MAXHEALTH', 'MAZDOCK', 'MCX', 'MEDANTA', 'METROPOLIS', 'MFSL', 'MGL', 'MIDHANI', 'MINDACORP', 'MMTC', 'MOTHERSON', 'MOTILALOFS', 'MPHASIS', 'MRF', 'MRPL', 'MSUMI', 'MTARTECH', 'MUTHOOTFIN', 'NAM-INDIA', 'NATCOPHARM', 'NATIONALUM', 'NAUKRI', 'NAVA', 'NAVINFLUOR', 'NAZARA', 'NBCC', 'NCC', 'NESTLEIND', 'NETWEB', 'NETWORK18', 'NEULANDLAB', 'NEWGEN', 'NH', 'NHPC', 'NIACL', 'NIVABUPA', 'NLCINDIA', 'NMDC', 'NSLNISP', 'NTPC', 'NTPCGREEN', 'NUVAMA', 'NUVOCO', 'NYKAA', 'OBEROIRLTY', 'OFSS', 'OIL', 'OLAELEC', 'OLECTRA', 'ONESOURCE', 'ONGC', 'PAGEIND', 'PATANJALI', 'PAYTM', 'PCBL', 'PEL', 'PERSISTENT', 'PETRONET', 'PFC', 'PFIZER', 'PGEL', 'PGHH', 'PHOENIXLTD', 'PIDILITIND', 'PIIND', 'PNB', 'PNBHOUSING', 'POLICYBZR', 'POLYCAB', 'POLYMED', 'POONAWALLA', 'POWERGRID', 'POWERINDIA', 'PPLPHARMA', 'PRAJIND', 'PREMIERENE', 'PRESTIGE', 'PSB', 'PTCIL', 'PVRINOX', 'RADICO', 'RAILTEL', 'RAINBOW', 'RAMCOCEM', 'RATNAMANI', 'RBLBANK', 'RCF', 'RECLTD', 'REDINGTON', 'RELIANCE', 'RELINFRA', 'RHIM', 'RITES', 'RKFORGE', 'RPOWER', 'RRKABEL', 'RVNL', 'SAGILITY', 'SAIL', 'SAILIFE', 'SAMMAANCAP', 'SAPPHIRE', 'SARDAEN', 'SAREGAMA', 'SBFC', 'SBICARD', 'SBILIFE', 'SBIN', 'SCHAEFFLER', 'SCHNEIDER', 'SCI', 'SHREECEM', 'SHRIRAMFIN', 'SHYAMMETL', 'SIEMENS', 'SIGNATURE', 'SJVN', 'SKFINDIA', 'SOBHA', 'SOLARINDS', 'SONACOMS', 'SONATSOFTW', 'SRF', 'STARHEALTH', 'SUMICHEM', 'SUNDARMFIN', 'SUNDRMFAST', 'SUNPHARMA', 'SUNTV', 'SUPREMEIND', 'SUZLON', 'SWANCORP', 'SWIGGY', 'SYNGENE', 'SYRMA', 'TARIL', 'TATACHEM', 'TATACOMM', 'TATACONSUM', 'TATAELXSI', 'TATAINVEST', 'TATAMOTORS', 'TATAPOWER', 'TATASTEEL', 'TATATECH', 'TBOTEK', 'TCS', 'TECHM', 'TECHNOE', 'TEJASNET', 'THELEELA', 'THERMAX', 'TIINDIA', 'TIMKEN', 'TITAGARH', 'TITAN', 'TMPV', 'TORNTPHARM', 'TORNTPOWER', 'TRENT', 'TRIDENT', 'TRITURBINE', 'TRIVENI', 'TTML', 'TVSMOTOR', 'UBL', 'UCOBANK', 'ULTRACEMCO', 'UNIMECH', 'UNIONBANK', 'UNITDSPR', 'UNOMINDA', 'UPL', 'USHAMART', 'UTIAMC', 'VBL', 'VEDL', 'VENTIVE', 'VGUARD', 'VIJAYA', 'VMM', 'VOLTAS', 'VTL', 'WAAREEENER', 'WELCORP', 'WELSPUNLIV', 'WESTLIFE', 'WHIRLPOOL', 'WIPRO', 'WOCKPHARMA', 'YESBANK', 'ZEEL', 'ZENSARTECH', 'ZENTEC', 'ZFCVINDIA', 'ZYDUSLIFE'
]