# import os
# from pathlib import Path
# from datetime import datetime
# import pytz
# import dj_database_url # For configuring PostgreSQL connection

# # --- CORE DJANGO CONFIGURATION ---
# BASE_DIR = Path(__file__).resolve().parent.parent

# # SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-default-key-for-local-dev-change-me')

# # SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# # Allow all hosts (*) for Heroku deployment
# ALLOWED_HOSTS = ['*']

# INSTALLED_APPS = [
#     'django.contrib.admin',
#     'django.contrib.auth',
#     'django.contrib.contenttypes',
#     'django.contrib.sessions',
#     'django.contrib.messages',
#     'django.contrib.staticfiles',
#     'dashboard', # Our main application containing models and dashboard UI
# ]

# MIDDLEWARE = [
#     'django.middleware.security.SecurityMiddleware',
#     # WhiteNoise middleware should be used immediately after SecurityMiddleware for static files
#     'whitenoise.middleware.WhiteNoiseMiddleware', 
#     'django.contrib.sessions.middleware.SessionMiddleware',
#     'django.middleware.common.CommonMiddleware',
#     'django.middleware.csrf.CsrfViewMiddleware',
#     'django.contrib.auth.middleware.AuthenticationMiddleware',
#     'django.contrib.messages.middleware.MessageMiddleware',
#     'django.middleware.clickjacking.XFrameOptionsMiddleware',
# ]

# ROOT_URLCONF = 'algotrader.urls'

# TEMPLATES = [
#     {
#         'BACKEND': 'django.template.backends.django.DjangoTemplates',
#         'DIRS': [BASE_DIR / 'templates'], 
#         'APP_DIRS': True,
#         'OPTIONS': {
#             'context_processors': [
#                 'django.template.context_processors.debug',
#                 'django.template.context_processors.request',
#                 'django.contrib.auth.context_processors.auth',
#                 'django.contrib.messages.context_processors.messages',
#             ],
#         },
#     },
# ]

# WSGI_APPLICATION = 'algotrader.wsgi.application'


# # --- DATABASE CONFIGURATION (PostgreSQL/SQLite Switch) ---
# if 'DATABASE_URL' in os.environ:
#     # Use the database URL provided by the Heroku Postgres add-on
#     DATABASES = {
#         'default': dj_database_url.config(
#             default=os.environ.get('DATABASE_URL'), 
#             conn_max_age=600, 
#             ssl_require=True
#         )
#     }
# else:
#     # Fallback for local development (SQLite)
#     DATABASES = {
#         'default': {
#             'ENGINE': 'django.db.backends.sqlite3',
#             'NAME': BASE_DIR / 'db.sqlite3',
#         }
#     }


# # --- Password Validation, Time Zones, and i18n ---
# AUTH_PASSWORD_VALIDATORS = [
#     {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
#     {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
#     {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
#     {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
# ]

# LANGUAGE_CODE = 'en-us'
# TIME_ZONE = 'UTC'
# USE_I18N = True
# USE_TZ = True
# DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# # --- STATIC FILES CONFIGURATION (FIX FOR HEROKU DEPLOYMENT) ---
# STATIC_URL = '/static/'
# STATIC_ROOT = BASE_DIR / 'staticfiles' 
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# # --- TIMEZONE CONSTANTS ---
# IST = pytz.timezone("Asia/Kolkata")


# # -------------------------------------------------------------------
# # --- REDIS CONFIGURATION AND CHANNELS (LOW-LATENCY BUS) ---
# # -------------------------------------------------------------------

# # REDIS_URL environment variable is set by Heroku Redis Addon
# REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# # --- MISSING CONSTANTS RESTORED BELOW ---

# # Pub/Sub & Stream Channels
# REDIS_DATA_CHANNEL = 'dhan_market_data'       # Legacy/Backup channel
# REDIS_STREAM_MARKET = 'stream:dhan:market'    # Main Market Data Stream
# REDIS_STREAM_ORDERS = 'stream:dhan:orders'    # Order Updates Stream
# REDIS_STREAM_CONTROL = 'stream:algo:control'  # Control Signals Stream

# # Control Channels (Used by Dashboard)
# REDIS_CONTROL_CHANNEL = 'strategy_control_channel' 
# REDIS_AUTH_CHANNEL = 'auth_channel'          # <--- THIS WAS MISSING

# # Consumer Group Config
# REDIS_CONSUMER_GROUP = 'algo_engine_group'
# REDIS_CONSUMER_NAME = f"algo_worker_{os.environ.get('DYNO', 'local')}"

# # Status Keys and Mappings
# REDIS_STATUS_DATA_ENGINE = 'data_engine_status'
# REDIS_STATUS_ALGO_ENGINE = 'algo_engine_status'
# REDIS_DHAN_TOKEN_KEY = 'dhan_access_token'   # Key where live token is stored
# PREV_DAY_HASH = 'prev_day_ohlc'             # T-1 High/Low/Close data
# LIVE_OHLC_KEY = 'live_ohlc_data'            # Current LTP snapshot for monitoring
# SYMBOL_ID_MAP_KEY = 'dhan_instrument_map'   # (Legacy)

# # --- DHAN API CONFIGURATION KEYS ---
# DHAN_CLIENT_ID = os.environ.get('DHAN_CLIENT_ID')

# # --- STRATEGY CONSTANTS ---
# RISK_MULTIPLIER = 2.5
# BREAKEVEN_TRIGGER_R = 1.25
# MAX_MONITORING_MINUTES = 6

# ENTRY_OFFSET_PCT = 0.0001
# STOP_OFFSET_PCT = 0.0002
# MAX_CANDLE_PCT = 0.007

# # --- NIFTY 500 SECURITY ID MAP (Static Data Source) ---
# # This dictionary maps the Symbol (key) to the Dhan Security ID (value).
# SECURITY_ID_MAP = {
#     '360ONE': 13061, '3MINDIA': 474, 'AADHARHFC': 23729, 'AARTIIND': 7, 'AAVAS': 5385, 'ABB': 13, 
#     'ABBOTINDIA': 17903, 'ABCAPITAL': 21614, 'ABFRL': 30108, 'ABLBL': 756843, 'ABREL': 625, 
#     'ABSLAMC': 6018, 'ACC': 22, 'ACE': 13587, 'ACMESOLAR': 27061, 'ADANIENSOL': 10217, 
#     'ADANIENT': 25, 'ADANIGREEN': 3563, 'ADANIPORTS': 15083, 'ADANIPOWER': 17388, 'ADVENTHTL': 759769, 
#     'AEGISLOG': 40, 'AEGISVOPAK': 757336, 'AFCONS': 25977, 'AFFLE': 11343, 'AGARWALEYE': 29452, 
#     'AIAENG': 13086, 'AIIL': 23553, 'AJANTPHARM': 8124, 'AKUMS': 24715, 'AKZOINDIA': 1467, 
#     'ALKEM': 11703, 'ALKYLAMINE': 4487, 'ALOKINDS': 17675, 'AMBER': 1185, 'AMBUJACEM': 1270, 
#     'ANANDRATHI': 7145, 'ANANTRAJ': 13620, 'ANGELONE': 324, 'APARINDS': 11491, 'APLAPOLLO': 25780, 
#     'APLLTD': 25328, 'APOLLOHOSP': 157, 'APOLLOTYRE': 163, 'APTUS': 5435, 'ARE&M': 100, 
#     'ASAHIINDIA': 5378, 'ASHOKLEY': 212, 'ASIANPAINT': 236, 'ASTERDM': 1508, 'ASTRAL': 14418, 
#     'ASTRAMICRO': 11618, 'ASTRAZEN': 5610, 'ATGL': 6066, 'ATHERENERG': 757645, 'ATUL': 263, 
#     'AUBANK': 21238, 'AUROPHARMA': 275, 'AWL': 8110, 'AXISBANK': 5900, 'BAJAJ-AUTO': 16669, 
#     'BAJAJFINSV': 16675, 'BAJAJHFL': 25270, 'BAJAJHLDNG': 305, 'BAJFINANCE': 317, 'BALKRISIND': 335, 
#     'BALRAMCHIN': 341, 'BANDHANBNK': 2263, 'BANKBARODA': 4668, 'BANKINDIA': 4745, 'BASF': 368, 
#     'BATAINDIA': 371, 'BAYERCROP': 17927, 'BBTC': 380, 'BDL': 2144, 'BEL': 383, 
#     'BEML': 395, 'BERGEPAINT': 404, 'BHARATFORG': 422, 'BHARTIARTL': 10604, 'BHARTIHEXA': 23489, 
#     'BHEL': 438, 'BIKAJI': 11966, 'BIOCON': 11373, 'BLS': 17279, 'BLUEDART': 495, 
#     'BLUEJET': 19686, 'BLUESTARCO': 8311, 'BOSCHLTD': 2181, 'BPCL': 526, 'BRIGADE': 15184, 
#     'BRITANNIA': 547, 'BSE': 19585, 'BSOFT': 6994, 'CAMPUS': 9362, 'CAMS': 342, 
#     'CANBK': 10794, 'CANFINHOME': 583, 'CAPLIPOINT': 3906, 'CARBORUNIV': 595, 'CASTROLIND': 1250, 
#     'CCL': 11452, 'CDSL': 21174, 'CEATLTD': 15254, 'CENTRALBK': 14894, 'CENTURYPLY': 13305, 
#     'CERA': 15039, 'CESC': 628, 'CGCL': 20329, 'CGPOWER': 760, 'CHALET': 8546, 
#     'CHAMBLFERT': 637, 'CHENNPETRO': 2049, 'CHOICEIN': 8866, 'CHOLAFIN': 685, 'CHOLAHLDNG': 21740, 
#     'CIPLA': 694, 'CLEAN': 5049, 'COALINDIA': 20374, 'COCHINSHIP': 21508, 'COFORGE': 11543, 
#     'COHANCE': 17945, 'COLPAL': 15141, 'CONCOR': 4749, 'CONCORDBIO': 18060, 'COROMANDEL': 739, 
#     'CRAFTSMAN': 2854, 'CREDITACC': 4421, 'CRISIL': 757, 'CROMPTON': 17094, 'CUB': 5701, 
#     'CUMMINSIND': 1901, 'CYIENT': 5748, 'CYIENTDLM': 17187, 'DABUR': 772, 'DALBHARAT': 8075, 
#     'DATAPATTNS': 7358, 'DBCORP': 17881, 'DBREALTY': 18124, 'DCMSHRIRAM': 811, 'DCXINDIA': 11895, 
#     'DEEPAKFERT': 827, 'DEEPAKNTR': 19943, 'DELHIVERY': 9599, 'DEVYANI': 5373, 'DIVISLAB': 10940, 
#     'DIXON': 21690, 'DLF': 14732, 'DMART': 19913, 'DOMS': 20551, 'DRREDDY': 881, 
#     'DYNAMATECH': 4525, 'ECLERX': 15179, 'EICHERMOT': 910, 'EIDPARRY': 916, 'EIHOTEL': 919, 
#     'ELECON': 13643, 'ELGIEQUIP': 937, 'EMAMILTD': 13517, 'EMCURE': 24398, 'ENDURANCE': 18822, 
#     'ENGINERSIN': 4907, 'ENRIN': 756871, 'ERIS': 21154, 'ESCORTS': 958, 'ETERNAL': 5097, 
#     'EXIDEIND': 676, 'FACT': 1008, 'FEDERALBNK': 1023, 'FINCABLES': 1038, 'FINPIPE': 1041, 
#     'FIRSTCRY': 24814, 'FIVESTAR': 12032, 'FLUOROCHEM': 13750, 'FORCEMOT': 11573, 'FORTIS': 14592, 
#     'FSL': 14304, 'GAIL': 4717, 'GESHIP': 13776, 'GICRE': 277, 'GILLETTE': 1576, 
#     'GLAND': 1186, 'GLAXO': 1153, 'GLENMARK': 7406, 'GMDCLTD': 5204, 'GMRAIRPORT': 13528, 
#     'GODFRYPHLP': 1181, 'GODIGIT': 23799, 'GODREJAGRO': 144, 'GODREJCP': 10099, 'GODREJIND': 10925, 
#     'GODREJPROP': 17875, 'GPIL': 13409, 'GRANULES': 11872, 'GRAPHITE': 592, 'GRASIM': 1232, 
#     'GRAVITA': 20534, 'GRSE': 5475, 'GSPL': 13197, 'GUJGASLTD': 10599, 'GVT&D': 16783, 
#     'HAL': 2303, 'HAPPSTMNDS': 48, 'HATHWAY': 18154, 'HAVELLS': 9819, 'HBLENGINE': 13966, 
#     'HCLTECH': 7229, 'HDFCAMC': 4244, 'HDFCBANK': 1333, 'HDFCLIFE': 467, 'HEG': 1336, 
#     'HEROMOTOCO': 1348, 'HEXT': 29666, 'HFCL': 21951, 'HINDALCO': 1363, 'HINDCOPPER': 17939, 
#     'HINDPETRO': 1406, 'HINDUNILVR': 1394, 'HINDZINC': 1424, 'HOMEFIRST': 2056, 'HONASA': 19813, 
#     'HONAUT': 3417, 'HSCL': 14334, 'HUDCO': 20825, 'HYUNDAI': 25844, 'ICICIBANK': 4963, 
#     'ICICIGI': 21770, 'ICICIPRULI': 18652, 'IDBI': 1476, 'IDEA': 14366, 'IDFCFIRSTB': 11184, 
#     'IEX': 220, 'IFCI': 1491, 'IGIL': 28378, 'IGL': 11262, 'IIFL': 11809, 
#     'IKS': 28125, 'INDGN': 23693, 'INDHOTEL': 1512, 'INDIACEM': 1515, 'INDIAMART': 10726, 
#     'INDIANB': 14309, 'INDIGO': 11195, 'INDUSINDBK': 5258, 'INDUSTOWER': 29135, 'INFY': 1594, 
#     'INOXINDIA': 20607, 'INOXWIND': 7852, 'INTELLECT': 5926, 'IOB': 9348, 'IOC': 1624, 
#     'IPCALAB': 1633, 'IRB': 15313, 'IRCON': 4986, 'IRCTC': 13611, 'IREDA': 20261, 
#     'IRFC': 2029, 'ITC': 1660, 'ITCHOTELS': 29251, 'ITI': 1675, 'J&KBANK': 5633, 
#     'JBCHEPHARM': 1726, 'JBMA': 11655, 'JINDALSAW': 3024, 'JINDALSTEL': 6733, 'JIOFIN': 18143, 
#     'JKCEMENT': 13270, 'JKTYRE': 14435, 'JMFINANCIL': 13637, 'JPPOWER': 11763, 'JSL': 11236, 
#     'JSWENERGY': 17869, 'JSWINFRA': 19020, 'JSWSTEEL': 11723, 'JUBLFOOD': 18096, 'JUBLINGREA': 2783, 
#     'JUBLPHARMA': 3637, 'JWL': 20224, 'JYOTHYLAB': 15146, 'JYOTICNC': 21334, 'KAJARIACER': 1808, 
#     'KALYANKJIL': 2955, 'KARURVYSYA': 1838, 'KAYNES': 12092, 'KEC': 13260, 'KEI': 13310, 
#     'KFINTECH': 13359, 'KIMS': 4847, 'KIRLOSBROS': 18581, 'KIRLOSENG': 20936, 'KOTAKBANK': 1922, 
#     'KPIL': 1814, 'KPITTECH': 9683, 'KPRMILL': 14912, 'KSB': 1949, 'LALPATHLAB': 11654, 
#     'LATENTVIEW': 6818, 'LAURUSLABS': 19234, 'LEMONTREE': 2606, 'LICHSGFIN': 1997, 'LICI': 9480, 
#     'LINDEINDIA': 1627, 'LLOYDSME': 17313, 'LODHA': 3220, 'LT': 11483, 'LTF': 24948, 
#     'LTFOODS': 13816, 'LTIM': 17818, 'LTTS': 18564, 'LUPIN': 10440, 'M&M': 2031, 
#     'M&MFIN': 20050, 'MAHABANK': 11377, 'MAHSCOOTER': 2085, 'MAHSEAMLES': 2088, 'MANAPPURAM': 19061, 
#     'MANKIND': 15380, 'MANYAVAR': 8167, 'MAPMYINDIA': 7227, 'MARICO': 4067, 'MARUTI': 10999, 
#     'MAXHEALTH': 22377, 'MAZDOCK': 509, 'MCX': 31181, 'MEDANTA': 11956, 'METROPOLIS': 9581, 
#     'MFSL': 2142, 'MGL': 17534, 'MIDHANI': 2463, 'MINDACORP': 25897, 'MMTC': 17957, 
#     'MOTHERSON': 4204, 'MOTILALOFS': 14947, 'MPHASIS': 4503, 'MRF': 2277, 'MRPL': 2283, 
#     'MSUMI': 8596, 'MTARTECH': 2709, 'MUTHOOTFIN': 23650, 'NAM-INDIA': 357, 'NATCOPHARM': 3918, 
#     'NATIONALUM': 6364, 'NAUKRI': 13751, 'NAVA': 4014, 'NAVINFLUOR': 14672, 'NAZARA': 2987, 
#     'NBCC': 31415, 'NCC': 2319, 'NESTLEIND': 17963, 'NETWEB': 17433, 'NETWORK18': 14111, 
#     'NEULANDLAB': 2406, 'NEWGEN': 1164, 'NH': 11840, 'NHPC': 17400, 'NIACL': 399, 
#     'NIVABUPA': 27097, 'NLCINDIA': 8585, 'NMDC': 15332, 'NSLNISP': 14180, 'NTPC': 11630, 
#     'NTPCGREEN': 27176, 'NUVAMA': 18721, 'NUVOCO': 5426, 'NYKAA': 6545, 'OBEROIRLTY': 20242, 
#     'OFSS': 10738, 'OIL': 17438, 'OLAELEC': 24779, 'OLECTRA': 2475, 'ONESOURCE': 29224, 
#     'ONGC': 2475, 'PAGEIND': 14413, 'PATANJALI': 17029, 'PAYTM': 6705, 'PCBL': 2649, 
#     'PEL': 1, 'PERSISTENT': 18365, 'PETRONET': 11351, 'PFC': 14299, 'PFIZER': 2643, 
#     'PGEL': 25358, 'PGHH': 2535, 'PHOENIXLTD': 14552, 'PIDILITIND': 2664, 'PIIND': 24184, 
#     'PNB': 10666, 'PNBHOUSING': 18908, 'POLICYBZR': 6656, 'POLYCAB': 9590, 'POLYMED': 25718, 
#     'POONAWALLA': 11403, 'POWERGRID': 14977, 'POWERINDIA': 18457, 'PPLPHARMA': 11571, 'PRAJIND': 2705, 
#     'PREMIERENE': 25049, 'PRESTIGE': 20302, 'PSB': 21001, 'PTCIL': 16682, 'PVRINOX': 13147, 
#     'RADICO': 10990, 'RAILTEL': 2431, 'RAINBOW': 9408, 'RAMCOCEM': 2043, 'RATNAMANI': 13451, 
#     'RBLBANK': 18391, 'RCF': 2866, 'RECLTD': 15355, 'REDINGTON': 14255, 'RELIANCE': 2885, 
#     'RELINFRA': 4791, 'RHIM': 31163, 'RITES': 3761, 'RKFORGE': 11411, 'RPOWER': 15259, 
#     'RRKABEL': 18566, 'RVNL': 9552, 'SAGILITY': 27052, 'SAIL': 2963, 'SAILIFE': 27839, 
#     'SAMMAANCAP': 30125, 'SAPPHIRE': 6718, 'SARDAEN': 17758, 'SAREGAMA': 4892, 'SBFC': 18026, 
#     'SBICARD': 17971, 'SBILIFE': 21808, 'SBIN': 3045, 'SCHAEFFLER': 1011, 'SCHNEIDER': 31234, 
#     'SCI': 3048, 'SHREECEM': 3103, 'SHRIRAMFIN': 4306, 'SHYAMMETL': 4693, 'SIEMENS': 3150, 
#     'SIGNATURE': 18743, 'SJVN': 18883, 'SKFINDIA': 3186, 'SOBHA': 13826, 'SOLARINDS': 13332, 
#     'SONACOMS': 4684, 'SONATSOFTW': 6596, 'SRF': 3273, 'STARHEALTH': 7083, 'SUMICHEM': 17105, 
#     'SUNDARMFIN': 3339, 'SUNDRMFAST': 3345, 'SUNPHARMA': 3351, 'SUNTV': 13404, 'SUPREMEIND': 3363, 
#     'SUZLON': 12018, 'SWANCORP': 27095, 'SWIGGY': 27066, 'SYNGENE': 10243, 'SYRMA': 10793, 
#     'TARIL': 15174, 'TATACHEM': 3405, 'TATACOMM': 3721, 'TATACONSUM': 3432, 'TATAELXSI': 3411, 
#     'TATAINVEST': 1621, 'TATAMOTORS': 3426, 'TATAPOWER': 3426, 'TATASTEEL': 3499, 'TATATECH': 20293, 
#     'TBOTEK': 23740, 'TCS': 11536, 'TECHM': 13538, 'TECHNOE': 6445, 'TEJASNET': 21131, 
#     'THELEELA': 757014, 'THERMAX': 3475, 'TIINDIA': 312, 'TIMKEN': 14198, 'TITAGARH': 15414, 
#     'TITAN': 3506, 'TMPV': 3456, 'TORNTPHARM': 3518, 'TORNTPOWER': 13786, 'TRENT': 1964, 
#     'TRIDENT': 9685, 'TRITURBINE': 25584, 'TRIVENI': 13081, 'TTML': 8954, 'TVSMOTOR': 8479, 
#     'UBL': 16713, 'UCOBANK': 11223, 'ULTRACEMCO': 11532, 'UNIMECH': 28960, 'UNIONBANK': 10753, 
#     'UNITDSPR': 10447, 'UNOMINDA': 14154, 'UPL': 11287, 'USHAMART': 8840, 'UTIAMC': 527, 
#     'VBL': 18921, 'VEDL': 3063, 'VENTIVE': 28847, 'VGUARD': 15362, 'VIJAYA': 5585, 
#     'VMM': 27969, 'VOLTAS': 3718, 'VTL': 2073, 'WAAREEENER': 25907, 'WELCORP': 11821, 
#     'WELSPUNLIV': 11253, 'WESTLIFE': 11580, 'WHIRLPOOL': 18011, 'WIPRO': 3787, 'WOCKPHARMA': 7506, 
#     'YESBANK': 11915, 'ZEEL': 3812, 'ZENSARTECH': 1076, 'ZENTEC': 7508, 'ZFCVINDIA': 16915, 
#     'ZYDUSLIFE': 7929
# }

# # --- Target symbol list derived from the map keys ---
# NIFTY_500_STOCKS = list(SECURITY_ID_MAP.keys())

import os
from pathlib import Path
from datetime import datetime, timedelta
import pytz
import dj_database_url 
from dotenv import load_dotenv # <--- ADDED: Load .env file for VPS

# --- LOAD ENVIRONMENT VARIABLES ---
load_dotenv()
# --- CORE DJANGO CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-default-key-for-local-dev-change-me')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# Allow all hosts (*) for Heroku deployment
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dashboard', # Custom App
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'algotrader.urls'
WSGI_APPLICATION = 'algotrader.wsgi.application'

# --- DATABASE CONFIGURATION ---
if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'), 
            conn_max_age=600, 
            ssl_require=True
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# --- PASSWORD VALIDATION ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# --- I18N & TIMEZONE ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata' # IST
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
IST = pytz.timezone("Asia/Kolkata")

# --- STATIC FILES ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles' 
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_DIRS = []

# --- TEMPLATES ---
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

# -------------------------------------------------------------------
# --- REDIS CONFIGURATION AND CHANNELS (LOW-LATENCY BUS) ---
# -------------------------------------------------------------------

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Streams (Primary Data Flow)
REDIS_STREAM_MARKET = 'stream:dhan:market'      # Raw Ticks
REDIS_STREAM_CANDLES = 'stream:dhan:candles'    # Completed 1m Candles
REDIS_STREAM_ORDERS = 'stream:dhan:orders'      # Order Updates
REDIS_STREAM_CONTROL = 'stream:algo:control'    # Admin Signals

# Pub/Sub (Legacy/Backup)
REDIS_DATA_CHANNEL = 'dhan_market_data'
REDIS_ORDER_UPDATE_CHANNEL = 'dhan_order_update'
REDIS_CANDLE_CHANNEL = 'dhan_candle_1m'
REDIS_CONTROL_CHANNEL = 'strategy_control_channel'
REDIS_AUTH_CHANNEL = 'auth_channel'

# Consumer Group Config
REDIS_CONSUMER_GROUP = 'algo_engine_group'
REDIS_CONSUMER_NAME = f"algo_worker_{os.environ.get('DYNO', 'local')}"

# Status & Storage Keys
REDIS_STATUS_DATA_ENGINE = 'data_engine_status'
REDIS_STATUS_ALGO_ENGINE = 'algo_engine_status'
REDIS_DHAN_TOKEN_KEY = 'dhan_access_token'
PREV_DAY_HASH = 'prev_day_ohlc'
LIVE_OHLC_KEY = 'live_ohlc_data'
SYMBOL_ID_MAP_KEY = 'dhan_instrument_map'
HISTORY_KEY_PREFIX = 'history' # Prefix for candle history lists

# --- DHAN API CONFIGURATION ---
DHAN_CLIENT_ID = os.environ.get('DHAN_CLIENT_ID')
DHAN_API_SECRET = os.environ.get('DHAN_API_SECRET')
DHAN_REDIRECT_URI = os.environ.get('DHAN_REDIRECT_URI')

# --- STRATEGY CONSTANTS ---
RISK_MULTIPLIER = 2.5
BREAKEVEN_TRIGGER_R = 1.25
MAX_MONITORING_MINUTES = 6
ENTRY_OFFSET_PCT = 0.0001
STOP_OFFSET_PCT = 0.0002
MAX_CANDLE_PCT = 0.007

# --- NIFTY 500 SECURITY ID MAP (Source of Truth) ---
SECURITY_ID_MAP = {
    '360ONE': 13061, '3MINDIA': 474, 'AADHARHFC': 23729, 'AARTIIND': 7, 'AAVAS': 5385, 'ABB': 13, 
    'ABBOTINDIA': 17903, 'ABCAPITAL': 21614, 'ABFRL': 30108, 'ABLBL': 756843, 'ABREL': 625, 
    'ABSLAMC': 6018, 'ACC': 22, 'ACE': 13587, 'ACMESOLAR': 27061, 'ADANIENSOL': 10217, 
    'ADANIENT': 25, 'ADANIGREEN': 3563, 'ADANIPORTS': 15083, 'ADANIPOWER': 17388, 'ADVENTHTL': 759769, 
    'AEGISLOG': 40, 'AEGISVOPAK': 757336, 'AFCONS': 25977, 'AFFLE': 11343, 'AGARWALEYE': 29452, 
    'AIAENG': 13086, 'AIIL': 23553, 'AJANTPHARM': 8124, 'AKUMS': 24715, 'AKZOINDIA': 1467, 
    'ALKEM': 11703, 'ALKYLAMINE': 4487, 'ALOKINDS': 17675, 'AMBER': 1185, 'AMBUJACEM': 1270, 
    'ANANDRATHI': 7145, 'ANANTRAJ': 13620, 'ANGELONE': 324, 'APARINDS': 11491, 'APLAPOLLO': 25780, 
    'APLLTD': 25328, 'APOLLOHOSP': 157, 'APOLLOTYRE': 163, 'APTUS': 5435, 'ARE&M': 100, 
    'ASAHIINDIA': 5378, 'ASHOKLEY': 212, 'ASIANPAINT': 236, 'ASTERDM': 1508, 'ASTRAL': 14418, 
    'ASTRAMICRO': 11618, 'ASTRAZEN': 5610, 'ATGL': 6066, 'ATHERENERG': 757645, 'ATUL': 263, 
    'AUBANK': 21238, 'AUROPHARMA': 275, 'AWL': 8110, 'AXISBANK': 5900, 'BAJAJ-AUTO': 16669, 
    'BAJAJFINSV': 16675, 'BAJAJHFL': 25270, 'BAJAJHLDNG': 305, 'BAJFINANCE': 317, 'BALKRISIND': 335, 
    'BALRAMCHIN': 341, 'BANDHANBNK': 2263, 'BANKBARODA': 4668, 'BANKINDIA': 4745, 'BASF': 368, 
    'BATAINDIA': 371, 'BAYERCROP': 17927, 'BBTC': 380, 'BDL': 2144, 'BEL': 383, 
    'BEML': 395, 'BERGEPAINT': 404, 'BHARATFORG': 422, 'BHARTIARTL': 10604, 'BHARTIHEXA': 23489, 
    'BHEL': 438, 'BIKAJI': 11966, 'BIOCON': 11373, 'BLS': 17279, 'BLUEDART': 495, 
    'BLUEJET': 19686, 'BLUESTARCO': 8311, 'BOSCHLTD': 2181, 'BPCL': 526, 'BRIGADE': 15184, 
    'BRITANNIA': 547, 'BSE': 19585, 'BSOFT': 6994, 'CAMPUS': 9362, 'CAMS': 342, 
    'CANBK': 10794, 'CANFINHOME': 583, 'CAPLIPOINT': 3906, 'CARBORUNIV': 595, 'CASTROLIND': 1250, 
    'CCL': 11452, 'CDSL': 21174, 'CEATLTD': 15254, 'CENTRALBK': 14894, 'CENTURYPLY': 13305, 
    'CERA': 15039, 'CESC': 628, 'CGCL': 20329, 'CGPOWER': 760, 'CHALET': 8546, 
    'CHAMBLFERT': 637, 'CHENNPETRO': 2049, 'CHOICEIN': 8866, 'CHOLAFIN': 685, 'CHOLAHLDNG': 21740, 
    'CIPLA': 694, 'CLEAN': 5049, 'COALINDIA': 20374, 'COCHINSHIP': 21508, 'COFORGE': 11543, 
    'COHANCE': 17945, 'COLPAL': 15141, 'CONCOR': 4749, 'CONCORDBIO': 18060, 'COROMANDEL': 739, 
    'CRAFTSMAN': 2854, 'CREDITACC': 4421, 'CRISIL': 757, 'CROMPTON': 17094, 'CUB': 5701, 
    'CUMMINSIND': 1901, 'CYIENT': 5748, 'CYIENTDLM': 17187, 'DABUR': 772, 'DALBHARAT': 8075, 
    'DATAPATTNS': 7358, 'DBCORP': 17881, 'DBREALTY': 18124, 'DCMSHRIRAM': 811, 'DCXINDIA': 11895, 
    'DEEPAKFERT': 827, 'DEEPAKNTR': 19943, 'DELHIVERY': 9599, 'DEVYANI': 5373, 'DIVISLAB': 10940, 
    'DIXON': 21690, 'DLF': 14732, 'DMART': 19913, 'DOMS': 20551, 'DRREDDY': 881, 
    'DYNAMATECH': 4525, 'ECLERX': 15179, 'EICHERMOT': 910, 'EIDPARRY': 916, 'EIHOTEL': 919, 
    'ELECON': 13643, 'ELGIEQUIP': 937, 'EMAMILTD': 13517, 'EMCURE': 24398, 'ENDURANCE': 18822, 
    'ENGINERSIN': 4907, 'ENRIN': 756871, 'ERIS': 21154, 'ESCORTS': 958, 'ETERNAL': 5097, 
    'EXIDEIND': 676, 'FACT': 1008, 'FEDERALBNK': 1023, 'FINCABLES': 1038, 'FINPIPE': 1041, 
    'FIRSTCRY': 24814, 'FIVESTAR': 12032, 'FLUOROCHEM': 13750, 'FORCEMOT': 11573, 'FORTIS': 14592, 
    'FSL': 14304, 'GAIL': 4717, 'GESHIP': 13776, 'GICRE': 277, 'GILLETTE': 1576, 
    'GLAND': 1186, 'GLAXO': 1153, 'GLENMARK': 7406, 'GMDCLTD': 5204, 'GMRAIRPORT': 13528, 
    'GODFRYPHLP': 1181, 'GODIGIT': 23799, 'GODREJAGRO': 144, 'GODREJCP': 10099, 'GODREJIND': 10925, 
    'GODREJPROP': 17875, 'GPIL': 13409, 'GRANULES': 11872, 'GRAPHITE': 592, 'GRASIM': 1232, 
    'GRAVITA': 20534, 'GRSE': 5475, 'GSPL': 13197, 'GUJGASLTD': 10599, 'GVT&D': 16783, 
    'HAL': 2303, 'HAPPSTMNDS': 48, 'HATHWAY': 18154, 'HAVELLS': 9819, 'HBLENGINE': 13966, 
    'HCLTECH': 7229, 'HDFCAMC': 4244, 'HDFCBANK': 1333, 'HDFCLIFE': 467, 'HEG': 1336, 
    'HEROMOTOCO': 1348, 'HEXT': 29666, 'HFCL': 21951, 'HINDALCO': 1363, 'HINDCOPPER': 17939, 
    'HINDPETRO': 1406, 'HINDUNILVR': 1394, 'HINDZINC': 1424, 'HOMEFIRST': 2056, 'HONASA': 19813, 
    'HONAUT': 3417, 'HSCL': 14334, 'HUDCO': 20825, 'HYUNDAI': 25844, 'ICICIBANK': 4963, 
    'ICICIGI': 21770, 'ICICIPRULI': 18652, 'IDBI': 1476, 'IDEA': 14366, 'IDFCFIRSTB': 11184, 
    'IEX': 220, 'IFCI': 1491, 'IGIL': 28378, 'IGL': 11262, 'IIFL': 11809, 
    'IKS': 28125, 'INDGN': 23693, 'INDHOTEL': 1512, 'INDIACEM': 1515, 'INDIAMART': 10726, 
    'INDIANB': 14309, 'INDIGO': 11195, 'INDUSINDBK': 5258, 'INDUSTOWER': 29135, 'INFY': 1594, 
    'INOXINDIA': 20607, 'INOXWIND': 7852, 'INTELLECT': 5926, 'IOB': 9348, 'IOC': 1624, 
    'IPCALAB': 1633, 'IRB': 15313, 'IRCON': 4986, 'IRCTC': 13611, 'IREDA': 20261, 
    'IRFC': 2029, 'ITC': 1660, 'ITCHOTELS': 29251, 'ITI': 1675, 'J&KBANK': 5633, 
    'JBCHEPHARM': 1726, 'JBMA': 11655, 'JINDALSAW': 3024, 'JINDALSTEL': 6733, 'JIOFIN': 18143, 
    'JKCEMENT': 13270, 'JKTYRE': 14435, 'JMFINANCIL': 13637, 'JPPOWER': 11763, 'JSL': 11236, 
    'JSWENERGY': 17869, 'JSWINFRA': 19020, 'JSWSTEEL': 11723, 'JUBLFOOD': 18096, 'JUBLINGREA': 2783, 
    'JUBLPHARMA': 3637, 'JWL': 20224, 'JYOTHYLAB': 15146, 'JYOTICNC': 21334, 'KAJARIACER': 1808, 
    'KALYANKJIL': 2955, 'KARURVYSYA': 1838, 'KAYNES': 12092, 'KEC': 13260, 'KEI': 13310, 
    'KFINTECH': 13359, 'KIMS': 4847, 'KIRLOSBROS': 18581, 'KIRLOSENG': 20936, 'KOTAKBANK': 1922, 
    'KPIL': 1814, 'KPITTECH': 9683, 'KPRMILL': 14912, 'KSB': 1949, 'LALPATHLAB': 11654, 
    'LATENTVIEW': 6818, 'LAURUSLABS': 19234, 'LEMONTREE': 2606, 'LICHSGFIN': 1997, 'LICI': 9480, 
    'LINDEINDIA': 1627, 'LLOYDSME': 17313, 'LODHA': 3220, 'LT': 11483, 'LTF': 24948, 
    'LTFOODS': 13816, 'LTIM': 17818, 'LTTS': 18564, 'LUPIN': 10440, 'M&M': 2031, 
    'M&MFIN': 20050, 'MAHABANK': 11377, 'MAHSCOOTER': 2085, 'MAHSEAMLES': 2088, 'MANAPPURAM': 19061, 
    'MANKIND': 15380, 'MANYAVAR': 8167, 'MAPMYINDIA': 7227, 'MARICO': 4067, 'MARUTI': 10999, 
    'MAXHEALTH': 22377, 'MAZDOCK': 509, 'MCX': 31181, 'MEDANTA': 11956, 'METROPOLIS': 9581, 
    'MFSL': 2142, 'MGL': 17534, 'MIDHANI': 2463, 'MINDACORP': 25897, 'MMTC': 17957, 
    'MOTHERSON': 4204, 'MOTILALOFS': 14947, 'MPHASIS': 4503, 'MRF': 2277, 'MRPL': 2283, 
    'MSUMI': 8596, 'MTARTECH': 2709, 'MUTHOOTFIN': 23650, 'NAM-INDIA': 357, 'NATCOPHARM': 3918, 
    'NATIONALUM': 6364, 'NAUKRI': 13751, 'NAVA': 4014, 'NAVINFLUOR': 14672, 'NAZARA': 2987, 
    'NBCC': 31415, 'NCC': 2319, 'NESTLEIND': 17963, 'NETWEB': 17433, 'NETWORK18': 14111, 
    'NEULANDLAB': 2406, 'NEWGEN': 1164, 'NH': 11840, 'NHPC': 17400, 'NIACL': 399, 
    'NIVABUPA': 27097, 'NLCINDIA': 8585, 'NMDC': 15332, 'NSLNISP': 14180, 'NTPC': 11630, 
    'NTPCGREEN': 27176, 'NUVAMA': 18721, 'NUVOCO': 5426, 'NYKAA': 6545, 'OBEROIRLTY': 20242, 
    'OFSS': 10738, 'OIL': 17438, 'OLAELEC': 24779, 'OLECTRA': 2475, 'ONESOURCE': 29224, 
    'ONGC': 2475, 'PAGEIND': 14413, 'PATANJALI': 17029, 'PAYTM': 6705, 'PCBL': 2649, 
    'PEL': 1, 'PERSISTENT': 18365, 'PETRONET': 11351, 'PFC': 14299, 'PFIZER': 2643, 
    'PGEL': 25358, 'PGHH': 2535, 'PHOENIXLTD': 14552, 'PIDILITIND': 2664, 'PIIND': 24184, 
    'PNB': 10666, 'PNBHOUSING': 18908, 'POLICYBZR': 6656, 'POLYCAB': 9590, 'POLYMED': 25718, 
    'POONAWALLA': 11403, 'POWERGRID': 14977, 'POWERINDIA': 18457, 'PPLPHARMA': 11571, 'PRAJIND': 2705, 
    'PREMIERENE': 25049, 'PRESTIGE': 20302, 'PSB': 21001, 'PTCIL': 16682, 'PVRINOX': 13147, 
    'RADICO': 10990, 'RAILTEL': 2431, 'RAINBOW': 9408, 'RAMCOCEM': 2043, 'RATNAMANI': 13451, 
    'RBLBANK': 18391, 'RCF': 2866, 'RECLTD': 15355, 'REDINGTON': 14255, 'RELIANCE': 2885, 
    'RELINFRA': 4791, 'RHIM': 31163, 'RITES': 3761, 'RKFORGE': 11411, 'RPOWER': 15259, 
    'RRKABEL': 18566, 'RVNL': 9552, 'SAGILITY': 27052, 'SAIL': 2963, 'SAILIFE': 27839, 
    'SAMMAANCAP': 30125, 'SAPPHIRE': 6718, 'SARDAEN': 17758, 'SAREGAMA': 4892, 'SBFC': 18026, 
    'SBICARD': 17971, 'SBILIFE': 21808, 'SBIN': 3045, 'SCHAEFFLER': 1011, 'SCHNEIDER': 31234, 
    'SCI': 3048, 'SHREECEM': 3103, 'SHRIRAMFIN': 4306, 'SHYAMMETL': 4693, 'SIEMENS': 3150, 
    'SIGNATURE': 18743, 'SJVN': 18883, 'SKFINDIA': 3186, 'SOBHA': 13826, 'SOLARINDS': 13332, 
    'SONACOMS': 4684, 'SONATSOFTW': 6596, 'SRF': 3273, 'STARHEALTH': 7083, 'SUMICHEM': 17105, 
    'SUNDARMFIN': 3339, 'SUNDRMFAST': 3345, 'SUNPHARMA': 3351, 'SUNTV': 13404, 'SUPREMEIND': 3363, 
    'SUZLON': 12018, 'SWANCORP': 27095, 'SWIGGY': 27066, 'SYNGENE': 10243, 'SYRMA': 10793, 
    'TARIL': 15174, 'TATACHEM': 3405, 'TATACOMM': 3721, 'TATACONSUM': 3432, 'TATAELXSI': 3411, 
    'TATAINVEST': 1621, 'TATAMOTORS': 3426, 'TATAPOWER': 3426, 'TATASTEEL': 3499, 'TATATECH': 20293, 
    'TBOTEK': 23740, 'TCS': 11536, 'TECHM': 13538, 'TECHNOE': 6445, 'TEJASNET': 21131, 
    'THELEELA': 757014, 'THERMAX': 3475, 'TIINDIA': 312, 'TIMKEN': 14198, 'TITAGARH': 15414, 
    'TITAN': 3506, 'TMPV': 3456, 'TORNTPHARM': 3518, 'TORNTPOWER': 13786, 'TRENT': 1964, 
    'TRIDENT': 9685, 'TRITURBINE': 25584, 'TRIVENI': 13081, 'TTML': 8954, 'TVSMOTOR': 8479, 
    'UBL': 16713, 'UCOBANK': 11223, 'ULTRACEMCO': 11532, 'UNIMECH': 28960, 'UNIONBANK': 10753, 
    'UNITDSPR': 10447, 'UNOMINDA': 14154, 'UPL': 11287, 'USHAMART': 8840, 'UTIAMC': 527, 
    'VBL': 18921, 'VEDL': 3063, 'VENTIVE': 28847, 'VGUARD': 15362, 'VIJAYA': 5585, 
    'VMM': 27969, 'VOLTAS': 3718, 'VTL': 2073, 'WAAREEENER': 25907, 'WELCORP': 11821, 
    'WELSPUNLIV': 11253, 'WESTLIFE': 11580, 'WHIRLPOOL': 18011, 'WIPRO': 3787, 'WOCKPHARMA': 7506, 
    'YESBANK': 11915, 'ZEEL': 3812, 'ZENSARTECH': 1076, 'ZENTEC': 7508, 'ZFCVINDIA': 16915, 
    'ZYDUSLIFE': 7929
}

NIFTY_500_STOCKS = list(SECURITY_ID_MAP.keys())