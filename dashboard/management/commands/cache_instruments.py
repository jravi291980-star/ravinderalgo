# dashboard/management/commands/cache_instruments.py
"""
Robust management command to cache Dhan symbol -> securityId mapping into Redis.

Features:
- Tries to use installed `dhanhq` SDK (with tolerant import attempts).
- If SDK unavailable or fails, downloads Dhan's detailed CSV and parses it robustly.
- Flexible column detection, symbol normalization, fuzzy fallback.
- Prints CSV header/sample rows to stdout for quick Heroku debugging.
- Writes JSON map to Redis key defined in settings.SYMBOL_ID_MAP_KEY.

Requirements: add `requests` to your requirements.txt if not present.

Usage:
    python manage.py cache_instruments

"""

import json
import csv
import io
import re
from typing import Dict, Optional, Set
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

import redis
import requests
from difflib import get_close_matches


# --- FULL NIFTY 500 SYMBOL LIST ---
NIFTY_500_SYMBOLS = [
    '360ONE', '3MINDIA', 'AADHARHFC', 'AARTIIND', 'AAVAS', 'ABB', 'ABBOTINDIA', 'ABCAPITAL', 'ABFRL', 'ABLBL',
    'ABREL', 'ABSLAMC', 'ACC', 'ACE', 'ACMESOLAR', 'ADANIENSOL', 'ADANIENT', 'ADANIGREEN', 'ADANIPORTS', 'ADANIPOWER',
    'ADVENTHTL', 'AEGISLOG', 'AEGISVOPAK', 'AFCONS', 'AFFLE', 'AGARWALEYE', 'AIAENG', 'AIIL', 'AJANTPHARM', 'AKUMS',
    'AKZOINDIA', 'ALKEM', 'ALKYLAMINE', 'ALOKINDS', 'AMBER', 'AMBUJACEM', 'ANANDRATHI', 'ANANTRAJ', 'ANGELONE', 'APARINDS',
    'APLAPOLLO', 'APLLTD', 'APOLLOHOSP', 'APOLLOTYRE', 'APTUS', 'ARE&M', 'ASAHIINDIA', 'ASHOKLEY', 'ASIANPAINT', 'ASTERDM',
    'ASTRAL', 'ASTRAMICRO', 'ASTRAZEN', 'ATGL', 'ATHERENERG', 'ATUL', 'AUBANK', 'AUROPHARMA', 'AWL', 'AXISBANK',
    'BAJAJ-AUTO', 'BAJAJFINSV', 'BAJAJHFL', 'BAJAJHLDNG', 'BAJFINANCE', 'BALKRISIND', 'BALRAMCHIN', 'BANDHANBNK', 'BANKBARODA', 'BANKINDIA',
    'BASF', 'BATAINDIA', 'BAYERCROP', 'BBTC', 'BDL', 'BEL', 'BEML', 'BERGEPAINT', 'BHARATFORG', 'BHARTIARTL',
    'BHARTIHEXA', 'BHEL', 'BIKAJI', 'BIOCON', 'BLS', 'BLUEDART', 'BLUEJET', 'BLUESTARCO', 'BOSCHLTD', 'BPCL',
    'BRIGADE', 'BRITANNIA', 'BSE', 'BSOFT', 'CAMPUS', 'CAMS', 'CANBK', 'CANFINHOME', 'CAPLIPOINT', 'CARBORUNIV',
    'CASTROLIND', 'CCL', 'CDSL', 'CEATLTD', 'CENTRALBK', 'CENTURYPLY', 'CERA', 'CESC', 'CGCL', 'CGPOWER',
    'CHALET', 'CHAMBLFERT', 'CHENNPETRO', 'CHOICEIN', 'CHOLAFIN', 'CHOLAHLDNG', 'CIPLA', 'CLEAN', 'COALINDIA', 'COCHINSHIP',
    'COFORGE', 'COHANCE', 'COLPAL', 'CONCOR', 'CONCORDBIO', 'COROMANDEL', 'CRAFTSMAN', 'CREDITACC', 'CRISIL', 'CROMPTON',
    'CUB', 'CUMMINSIND', 'CYIENT', 'CYIENTDLM', 'DABUR', 'DALBHARAT', 'DATAPATTNS', 'DBCORP', 'DBREALTY', 'DCMSHRIRAM',
    'DCXINDIA', 'DEEPAKFERT', 'DEEPAKNTR', 'DELHIVERY', 'DEVYANI', 'DIVISLAB', 'DIXON', 'DLF', 'DMART', 'DOMS',
    'DRREDDY', 'DYNAMATECH', 'ECLERX', 'EICHERMOT', 'EIDPARRY', 'EIHOTEL', 'ELECON', 'ELGIEQUIP', 'EMAMILTD', 'EMCURE',
    'ENDURANCE', 'ENGINERSIN', 'ENRIN', 'ERIS', 'ESCORTS', 'ETERNAL', 'EXIDEIND', 'FACT', 'FEDERALBNK', 'FINCABLES',
    'FINPIPE', 'FIRSTCRY', 'FIVESTAR', 'FLUOROCHEM', 'FORCEMOT', 'FORTIS', 'FSL', 'GAIL', 'GESHIP', 'GICRE',
    'GILLETTE', 'GLAND', 'GLAXO', 'GLENMARK', 'GMDCLTD', 'GMRAIRPORT', 'GODFRYPHLP', 'GODIGIT', 'GODREJAGRO', 'GODREJCP',
    'GODREJIND', 'GODREJPROP', 'GPIL', 'GRANULES', 'GRAPHITE', 'GRASIM', 'GRAVITA', 'GRSE', 'GSPL', 'GUJGASLTD',
    'GVT&D', 'HAL', 'HAPPSTMNDS', 'HATHWAY', 'HAVELLS', 'HBLENGINE', 'HCLTECH', 'HDFCAMC', 'HDFCBANK', 'HDFCLIFE',
    'HEG', 'HEROMOTOCO', 'HEXT', 'HFCL', 'HINDALCO', 'HINDCOPPER', 'HINDPETRO', 'HINDUNILVR', 'HINDZINC', 'HOMEFIRST',
    'HONASA', 'HONAUT', 'HSCL', 'HUDCO', 'HYUNDAI', 'ICICIBANK', 'ICICIGI', 'ICICIPRULI', 'IDBI', 'IDEA',
    'IDFCFIRSTB', 'IEX', 'IFCI', 'IGIL', 'IGL', 'IIFL', 'IKS', 'INDGN', 'INDHOTEL', 'INDIACEM',
    'INDIAMART', 'INDIANB', 'INDIGO', 'INDUSINDBK', 'INDUSTOWER', 'INFY', 'INOXINDIA', 'INOXWIND', 'INTELLECT', 'IOC',
    'IPCALAB', 'IRB', 'IRCON', 'IRCTC', 'IREDA', 'IRFC', 'ITC', 'ITCHOTELS', 'ITI', 'J&KBANK',
    'JBCHEPHARM', 'JBMA', 'JINDALSAW', 'JINDALSTEL', 'JIOFIN', 'JKCEMENT', 'JKTYRE', 'JMFINANCIL', 'JPPOWER', 'JSL',
    'JSWENERGY', 'JSWINFRA', 'JSWSTEEL', 'JUBLFOOD', 'JUBLINGREA', 'JUBLPHARMA', 'JWL', 'JYOTHYLAB', 'JYOTICNC', 'KAJARIACER',
    'KALYANKJIL', 'KARURVYSYA', 'KAYNES', 'KEC', 'KEI', 'KFINTECH', 'KIMS', 'KIRLOSBROS', 'KIRLOSENG', 'KOTAKBANK',
    'KPIL', 'KPITTECH', 'KPRMILL', 'KSB', 'LALPATHLAB', 'LATENTVIEW', 'LAURUSLABS', 'LEMONTREE', 'LICHSGFIN', 'LICI',
    'LINDEINDIA', 'LLOYDSME', 'LODHA', 'LT', 'LTF', 'LTFOODS', 'LTIM', 'LTTS', 'LUPIN', 'M&M',
    'M&MFIN', 'MAHABANK', 'MAHSCOOTER', 'MAHSEAMLES', 'MANAPPURAM', 'MANKIND', 'MANYAVAR', 'MAPMYINDIA', 'MARICO', 'MARUTI',
    'MAXHEALTH', 'MAZDOCK', 'MCX', 'MEDANTA', 'METROPOLIS', 'MFSL', 'MGL', 'MIDHANI', 'MINDACORP', 'MMTC',
    'MOTHERSON', 'MOTILALOFS', 'MPHASIS', 'MRF', 'MRPL', 'MSUMI', 'MTARTECH', 'MUTHOOTFIN', 'NAM-INDIA', 'NATCOPHARM',
    'NATIONALUM', 'NAUKRI', 'NAVA', 'NAVINFLUOR', 'NAZARA', 'NBCC', 'NCC', 'NESTLEIND', 'NETWEB', 'NETWORK18',
    'NEULANDLAB', 'NEWGEN', 'NH', 'NHPC', 'NIACL', 'NIVABUPA', 'NLCINDIA', 'NMDC', 'NSLNISP', 'NTPC',
    'NTPCGREEN', 'NUVAMA', 'NUVOCO', 'NYKAA', 'OBEROIRLTY', 'OFSS', 'OIL', 'OLAELEC', 'OLECTRA', 'ONESOURCE',
    'ONGC', 'PAGEIND', 'PATANJALI', 'PAYTM', 'PCBL', 'PEL', 'PERSISTENT', 'PETRONET', 'PFC', 'PFIZER',
    'PGEL', 'PGHH', 'PHOENIXLTD', 'PIDILITIND', 'PIIND', 'PNB', 'PNBHOUSING', 'POLICYBZR', 'POLYCAB', 'POLYMED',
    'POONAWALLA', 'POWERGRID', 'POWERINDIA', 'PPLPHARMA', 'PRAJIND', 'PREMIERENE', 'PRESTIGE', 'PSB', 'PTCIL', 'PVRINOX',
    'RADICO', 'RAILTEL', 'RAINBOW', 'RAMCOCEM', 'RATNAMANI', 'RBLBANK', 'RCF', 'RECLTD', 'REDINGTON', 'RELIANCE',
    'RELINFRA', 'RHIM', 'RITES', 'RKFORGE', 'RPOWER', 'RRKABEL', 'RVNL', 'SAGILITY', 'SAIL', 'SAILIFE',
    'SAMMAANCAP', 'SAPPHIRE', 'SARDAEN', 'SAREGAMA', 'SBFC', 'SBICARD', 'SBILIFE', 'SBIN', 'SCHAEFFLER', 'SCHNEIDER',
    'SCI', 'SHREECEM', 'SHRIRAMFIN', 'SHYAMMETL', 'SIEMENS', 'SIGNATURE', 'SJVN', 'SKFINDIA', 'SOBHA', 'SOLARINDS',
    'SONACOMS', 'SONATSOFTW', 'SRF', 'STARHEALTH', 'SUMICHEM', 'SUNDARMFIN', 'SUNDRMFAST', 'SUNPHARMA', 'SUNTV', 'SUPREMEIND',
    'SUZLON', 'SWANCORP', 'SWIGGY', 'SYNGENE', 'SYRMA', 'TARIL', 'TATACHEM', 'TATACOMM', 'TATACONSUM', 'TATAELXSI',
    'TATAINVEST', 'TATAMOTORS', 'TATAPOWER', 'TATASTEEL', 'TATATECH', 'TBOTEK', 'TCS', 'TECHM', 'TECHNOE', 'TEJASNET',
    'THELEELA', 'THERMAX', 'TIINDIA', 'TIMKEN', 'TITAGARH', 'TITAN', 'TMPV', 'TORNTPHARM', 'TORNTPOWER', 'TRENT',
    'TRIDENT', 'TRITURBINE', 'TRIVENI', 'TTML', 'TVSMOTOR', 'UBL', 'UCOBANK', 'ULTRACEMCO', 'UNIMECH', 'UNIONBANK',
    'UNITDSPR', 'UNOMINDA', 'UPL', 'USHAMART', 'UTIAMC', 'VBL', 'VEDL', 'VENTIVE', 'VGUARD', 'VIJAYA',
    'VMM', 'VOLTAS', 'VTL', 'WAAREEENER', 'WELCORP', 'WELSPUNLIV', 'WESTLIFE', 'WHIRLPOOL', 'WIPRO', 'WOCKPHARMA',
    'YESBANK', 'ZEEL', 'ZENSARTECH', 'ZENTEC', 'ZFCVINDIA', 'ZYDUSLIFE'
]

CSV_SCRIP_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"


_clean_re = re.compile(r'[^A-Z0-9]')


def clean_symbol(raw: str) -> str:
    """Normalize trading symbol: uppercase, strip common suffixes/punctuation, keep letters+digits only."""
    if raw is None:
        return ""
    s = raw.upper().strip()
    # remove common vendor suffixes & exchange markers
    s = re.sub(r'(\-EQ|_EQ|\.EQ|\sEQ|\sNSE|\sBSE|_NSE|_BSE|\.NSE|\.BSE)$', '', s)
    s = _clean_re.sub('', s)
    return s


def robust_imports():
    """
    Try several import paths for Dhan SDK that have been seen in different releases.
    Returns tuple (DhanContext_cls, dhan_factory_callable, MarketFeed_cls) or (None, None, None).
    """
    DhanContext = None
    dhan_factory = None
    MarketFeed = None

    try:
        # Preferred canonical import
        from dhanhq import DhanContext as _D, dhanhq as _factory, MarketFeed as _M
        return _D, _factory, _M
    except Exception:
        pass

    try:
        # Try common submodule layout
        from dhanhq.dhan_context import DhanContext as _D
        from dhanhq.client import dhanhq as _factory
        try:
            from dhanhq.marketfeed import MarketFeed as _M
        except Exception:
            _M = None
        return _D, _factory, _M
    except Exception:
        pass

    try:
        # Inspect top-level module
        import dhanhq as _d
        DhanContext = getattr(_d, 'DhanContext', None)
        dhan_factory = getattr(_d, 'dhanhq', None)
        MarketFeed = getattr(_d, 'MarketFeed', None)
        if DhanContext and dhan_factory:
            return DhanContext, dhan_factory, MarketFeed
    except Exception:
        pass

    return None, None, None


def get_dhan_client(client_id: str, token: str) -> Optional[object]:
    """Initialize Dhan REST client if SDK present; return None if not available."""
    if not token:
        return None

    DhanContext, dhan_factory, MarketFeed = robust_imports()
    if not (DhanContext and dhan_factory):
        return None

    try:
        ctx = DhanContext(client_id, token)
        dhan = dhan_factory(ctx)
        return dhan
    except Exception:
        return None


def fetch_instrument_map_from_dhan_csv(symbols_set: Set[str]) -> Dict[str, Dict[str, str]]:
    """
    Download Dhan's scrip master CSV and robustly parse symbol -> securityId mapping.
    Returns: {your_symbol: {'security_id', 'exchange_segment', 'csv_symbol'}}
    """
    try:
        resp = requests.get(CSV_SCRIP_MASTER_URL, timeout=20)
        resp.raise_for_status()
        text = resp.text
    except Exception as e:
        raise Exception(f"Failed to fetch instrument CSV from Dhan: {e}")

    lines = text.splitlines()
    if len(lines) >= 1:
        print("CSV HEADER:", lines[0])
    if len(lines) >= 2:
        print("CSV SAMPLE ROW 1:", lines[1])
    if len(lines) >= 3:
        print("CSV SAMPLE ROW 2:", lines[2])

    f = io.StringIO(text)
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames or []
    print("Detected CSV columns:", fieldnames[:60])

    # Candidate names based on Dhan docs
    symbol_candidates = [
        'tradingSymbol', 'SEM_TRADING_SYMBOL', 'DISPLAY_NAME', 'SEM_CUSTOM_SYMBOL',
        'SYMBOL_NAME', 'SM_SYMBOL_NAME', 'INSTRUMENT', 'symbol', 'TradingSymbol'
    ]
    secid_candidates = ['securityId', 'SECURITYID', 'security_id', 'SecurityID', 'secid']
    exch_candidates = ['exchangeSegment', 'EXCH_ID', 'SEGMENT', 'exchange', 'ExchangeSegment']

    def pick(cands):
        for k in cands:
            for f in fieldnames:
                if f and f.lower() == k.lower():
                    return f
        for k in cands:
            for f in fieldnames:
                if f and k.lower() in f.lower():
                    return f
        return None

    symbol_col = pick(symbol_candidates)
    secid_col = pick(secid_candidates)
    exch_col = pick(exch_candidates)

    print("Using columns -> symbol:", symbol_col, " secid:", secid_col, " exchange:", exch_col)

    cleaned_target = {clean_symbol(s): s for s in symbols_set}
    csv_seen = []
    rows = list(reader)

    instrument_map: Dict[str, Dict[str, str]] = {}

    # 1) Exact cleaned matches
    for row in rows:
        raw_sym = row.get(symbol_col) if symbol_col else None
        raw_secid = row.get(secid_col) if secid_col else None
        raw_exch = row.get(exch_col) if exch_col else None
        if not raw_sym or not raw_secid:
            continue
        cs = clean_symbol(raw_sym)
        csv_seen.append(cs)
        if cs in cleaned_target:
            instrument_map[cleaned_target[cs]] = {
                'security_id': str(raw_secid),
                'exchange_segment': raw_exch or '',
                'csv_symbol': raw_sym,
            }

    # 2) startswith/contains
    if len(instrument_map) < len(symbols_set):
        remaining = {s for s in symbols_set if s not in instrument_map}
        for row in rows:
            raw_sym = row.get(symbol_col) if symbol_col else None
            raw_secid = row.get(secid_col) if secid_col else None
            raw_exch = row.get(exch_col) if exch_col else None
            if not raw_sym or not raw_secid:
                continue
            cs = clean_symbol(raw_sym)
            for target in list(remaining):
                if cs.startswith(clean_symbol(target)) or clean_symbol(target).startswith(cs) or clean_symbol(target) in cs:
                    instrument_map[target] = {
                        'security_id': str(raw_secid),
                        'exchange_segment': raw_exch or '',
                        'csv_symbol': raw_sym,
                    }
                    remaining.discard(target)

    # 3) fuzzy match
    if len(instrument_map) < len(symbols_set):
        csv_seen = list(set(csv_seen))
        remaining = [s for s in symbols_set if s not in instrument_map]
        for target in remaining:
            ct = clean_symbol(target)
            close = get_close_matches(ct, csv_seen, n=3, cutoff=0.82)
            if close:
                match_cs = close[0]
                for row in rows:
                    raw_sym = row.get(symbol_col) if symbol_col else None
                    raw_secid = row.get(secid_col) if secid_col else None
                    raw_exch = row.get(exch_col) if exch_col else None
                    if raw_sym and clean_symbol(raw_sym) == match_cs and raw_secid:
                        instrument_map[target] = {
                            'security_id': str(raw_secid),
                            'exchange_segment': raw_exch or '',
                            'csv_symbol': raw_sym,
                        }
                        break

    return instrument_map


class Command(BaseCommand):
    help = 'Fetches Dhan instrument mapping and caches Symbol <-> Security ID in Redis for the Nifty 500 list.'

    def handle(self, *args, **options):
        # 1) Redis init
        try:
            r = redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)
        except Exception as e:
            raise CommandError(f"Failed to connect to Redis (check REDIS_URL): {e}")

        token = None
        try:
            token = r.get(settings.REDIS_DHAN_TOKEN_KEY)
        except Exception:
            token = None

        # Try SDK client if token present
        dhan = None
        if token:
            dhan = get_dhan_client(settings.DHAN_CLIENT_ID, token)

        instrument_map: Dict[str, Dict[str, str]] = {}
        target_symbols = set(NIFTY_500_SYMBOLS)
        total_instruments = 0

        # If SDK available, try to fetch via API
        if dhan is not None:
            self.stdout.write(self.style.NOTICE('Dhan SDK client initialized — attempting API fetch of security list...'))
            try:
                response = dhan.fetch_security_list('full')
                data = None
                if isinstance(response, dict):
                    data = response.get('data')
                elif hasattr(response, 'data'):
                    data = getattr(response, 'data')
                else:
                    data = response

                if not data:
                    raise Exception('Empty data in SDK response')

                for item in data:
                    symbol = item.get('tradingSymbol') or item.get('tradingSymbol'.lower()) or item.get('trading_symbol')
                    security_id = item.get('securityId') or item.get('securityId'.lower()) or item.get('security_id')
                    exchange_segment = item.get('exchangeSegment') or item.get('exchangeSegment'.lower()) or item.get('exchange_segment')
                    if symbol and security_id and symbol in target_symbols:
                        instrument_map[symbol] = {
                            'security_id': str(security_id),
                            'exchange_segment': exchange_segment,
                            'symbol': symbol,
                        }
                        target_symbols.discard(symbol)

                total_instruments = len(instrument_map)
                self.stdout.write(self.style.SUCCESS(f"SDK: mapped {total_instruments} instruments via Dhan API."))

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Dhan SDK fetch failed: {e}. Falling back to CSV fetch."))

        # If no SDK result or no token, use CSV fallback
        if not instrument_map:
            self.stdout.write(self.style.NOTICE("Fetching instrument master via Dhan's public CSV (fallback)..."))
            try:
                csv_map = fetch_instrument_map_from_dhan_csv(set(NIFTY_500_SYMBOLS))
                instrument_map.update(csv_map)
                total_instruments = len(instrument_map)
                self.stdout.write(self.style.SUCCESS(f"CSV: mapped {total_instruments} instruments from CSV endpoint."))
            except Exception as e:
                raise CommandError(f"Both SDK and CSV fetch failed: {e}")

        # Cache in Redis
        if instrument_map:
            try:
                r.set(settings.SYMBOL_ID_MAP_KEY, json.dumps(instrument_map))
                self.stdout.write(self.style.SUCCESS(f"Successfully cached {total_instruments} instruments to Redis key: {settings.SYMBOL_ID_MAP_KEY}"))
                missing = [s for s in NIFTY_500_SYMBOLS if s not in instrument_map]
                if missing:
                    self.stdout.write(self.style.WARNING(f"{len(missing)} symbols were not found (examples): {missing[:12]}"))
            except Exception as e:
                raise CommandError(f"Failed to cache data in Redis: {e}")
        else:
            raise CommandError("No valid instruments were processed to cache. Check CSV/API and token permissions.")
