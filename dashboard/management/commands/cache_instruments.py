# dashboard/management/commands/cache_instruments.py
import json
import os
import time
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import redis
from typing import Dict, List, Any

# --- FIX: Robust Import of Dhan SDK components for Management Command ---
try:
    from dhanhq import DhanContext, dhanhq, MarketFeed
except ImportError:
    # Fallback to older patterns/define placeholders if current version fails
    class DhanContext:
        def __init__(self, client_id, access_token):
            self.client_id = client_id
            self.access_token = access_token
    dhanhq = lambda ctx: None
    MarketFeed = lambda: None
    
# --- NIFTY 500 Symbol List (Must be loaded locally) ---
# NOTE: The full list is too long to display here, but the code assumes the list 
# exists locally in the actual Django environment.
NIFTY_500_SYMBOLS = [
    '360ONE', '3MINDIA', 'AADHARHFC', 'AARTIIND', 'AAVAS', 'ABB', 'ABBOTINDIA', 'ABCAPITAL', 'ABFRL', 'ABLBL', 'ABREL', 'ABSLAMC', 'ACC', 'ACE', 'ACMESOLAR', 'ADANIENSOL', 'ADANIENT', 'ADANIGREEN', 'ADANIPORTS', 'ADANIPOWER', 'ADVENTHTL', 'AEGISLOG', 'AEGISVOPAK', 'AFCONS', 'AFFLE', 'AGARWALEYE', 'AIAENG', 'AIIL', 'AJANTPHARM', 'AKUMS', 'AKZOINDIA', 'ALKEM', 'ALKYLAMINE', 'ALOKINDS', 'AMBER', 'AMBUJACEM', 'ANANDRATHI', 'ANANTRAJ', 'ANGELONE', 'APARINDS', 'APLAPOLLO', 'APLLTD', 'APOLLOHOSP', 'APOLLOTYRE', 'APTUS', 'ARE&M', 'ASAHIINDIA', 'ASHOKLEY', 'ASIANPAINT', 'ASTERDM', 'ASTRAL', 'ASTRAMICRO', 'ASTRAZEN', 'ATGL', 'ATHERENERG', 'ATUL', 'AUBANK', 'AUROPHARMA', 'AWL', 'AXISBANK', 'BAJAJ-AUTO', 'BAJAJFINSV', 'BAJAJHFL', 'BAJAJHLDNG', 'BAJFINANCE', 'BALKRISIND', 'BALRAMCHIN', 'BANDHANBNK', 'BANKBARODA', 'BANKINDIA', 'BASF', 'BATAINDIA', 'BAYERCROP', 'BBTC', 'BDL', 'BEL', 'BEML', 'BERGEPAINT', 'BHARATFORG', 'BHARTIARTL', 'BHARTIHEXA', 'BHEL', 'BIKAJI', 'BIOCON', 'BLS', 'BLUEDART', 'BLUEJET', 'BLUESTARCO', 'BOSCHLTD', 'BPCL', 'BRIGADE', 'BRITANNIA', 'BSE', 'BSOFT', 'CAMPUS', 'CAMS', 'CANBK', 'CANFINHOME', 'CAPLIPOINT', 'CARBORUNIV', 'CASTROLIND', 'CCL', 'CDSL', 'CEATLTD', 'CENTRALBK', 'CENTURYPLY', 'CERA', 'CESC', 'CGCL', 'CGPOWER', 'CHALET', 'CHAMBLFERT', 'CHENNPETRO', 'CHOICEIN', 'CHOLAFIN', 'CHOLAHLDNG', 'CIPLA', 'CLEAN', 'COALINDIA', 'COCHINSHIP', 'COFORGE', 'COHANCE', 'COLPAL', 'CONCOR', 'CONCORDBIO', 'COROMANDEL', 'CRAFTSMAN', 'CREDITACC', 'CRISIL', 'CROMPTON', 'CUB', 'CUMMINSIND', 'CYIENT', 'CYIENTDLM', 'DABUR', 'DALBHARAT', 'DATAPATTNS', 'DBCORP', 'DBREALTY', 'DCMSHRIRAM', 'DCXINDIA', 'DEEPAKFERT', 'DEEPAKNTR', 'DELHIVERY', 'DEVYANI', 'DIVISLAB', 'DIXON', 'DLF', 'DMART', 'DOMS', 'DRREDDY', 'DYNAMATECH', 'ECLERX', 'EICHERMOT', 'EIDPARRY', 'EIHOTEL', 'ELECON', 'ELGIEQUIP', 'EMAMILTD', 'EMCURE', 'ENDURANCE', 'ENGINERSIN', 'ENRIN', 'ERIS', 'ESCORTS', 'ETERNAL', 'EXIDEIND', 'FACT', 'FEDERALBNK', 'FINCABLES', 'FINPIPE', 'FIRSTCRY', 'FIVESTAR', 'FLUOROCHEM', 'FORCEMOT', 'FORTIS', 'FSL', 'GAIL', 'GESHIP', 'GICRE', 'GILLETTE', 'GLAND', 'GLAXO', 'GLENMARK', 'GMDCLTD', 'GMRAIRPORT', 'GODFRYPHLP', 'GODIGIT', 'GODREJAGRO', 'GODREJCP', 'GODREJIND', 'GODREJPROP', 'GPIL', 'GRANULES', 'GRAPHITE', 'GRASIM', 'GRAVITA', 'GRSE', 'GSPL', 'GUJGASLTD', 'GVT&D', 'HAL', 'HAPPSTMNDS', 'HATHWAY', 'HAVELLS', 'HBLENGINE', 'HCLTECH', 'HDFCAMC', 'HDFCBANK', 'HDFCLIFE', 'HEG', 'HEROMOTOCO', 'HEXT', 'HFCL', 'HINDALCO', 'HINDCOPPER', 'HINDPETRO', 'HINDUNILVR', 'HINDZINC', 'HOMEFIRST', 'HONASA', 'HONAUT', 'HSCL', 'HUDCO', 'HYUNDAI', 'ICICIBANK', 'ICICIGI', 'ICICIPRULI', 'IDBI', 'IDEA', 'IDFCFIRSTB', 'IEX', 'IFCI', 'IGIL', 'IGL', 'IIFL', 'IKS', 'INDGN', 'INDHOTEL', 'INDIACEM', 'INDIAMART', 'INDIANB', 'INDIGO', 'INDUSINDBK', 'INDUSTOWER', 'INFY', 'INOXINDIA', 'INOXWIND', 'INTELLECT', 'IOB', 'IOC', 'IPCALAB', 'IRB', 'IRCON', 'IRCTC', 'IREDA', 'IRFC', 'ITC', 'ITCHOTELS', 'ITI', 'J&KBANK', 'JBCHEPHARM', 'JBMA', 'JINDALSAW', 'JINDALSTEL', 'JIOFIN', 'JKCEMENT', 'JKTYRE', 'JMFINANCIL', 'JPPOWER', 'JSL', 'JSWENERGY', 'JSWINFRA', 'JSWSTEEL', 'JUBLFOOD', 'JUBLINGREA', 'JUBLPHARMA', 'JWL', 'JYOTHYLAB', 'JYOTICNC', 'KAJARIACER', 'KALYANKJIL', 'KARURVYSYA', 'KAYNES', 'KEC', 'KEI', 'KFINTECH', 'KIMS', 'KIRLOSBROS', 'KIRLOSENG', 'KOTAKBANK', 'KPIL', 'KPITTECH', 'KPRMILL', 'KSB', 'LALPATHLAB', 'LATENTVIEW', 'LAURUSLABS', 'LEMONTREE', 'LICHSGFIN', 'LICI', 'LINDEINDIA', 'LLOYDSME', 'LODHA', 'LT', 'LTF', 'LTFOODS', 'LTIM', 'LTTS', 'LUPIN', 'M&M', 'M&MFIN', 'MAHABANK', 'MAHSCOOTER', 'MAHSEAMLES', 'MANAPPURAM', 'MANKIND', 'MANYAVAR', 'MAPMYINDIA', 'MARICO', 'MARUTI', 'MAXHEALTH', 'MAZDOCK', 'MCX', 'MEDANTA', 'METROPOLIS', 'MFSL', 'MGL', 'MIDHANI', 'MINDACORP', 'MMTC', 'MOTHERSON', 'MOTILALOFS', 'MPHASIS', 'MRF', 'MRPL', 'MSUMI', 'MTARTECH', 'MUTHOOTFIN', 'NAM-INDIA', 'NATCOPHARM', 'NATIONALUM', 'NAUKRI', 'NAVA', 'NAVINFLUOR', 'NAZARA', 'NBCC', 'NCC', 'NESTLEIND', 'NETWEB', 'NETWORK18', 'NEULANDLAB', 'NEWGEN', 'NH', 'NHPC', 'NIACL', 'NIVABUPA', 'NLCINDIA', 'NMDC', 'NSLNISP', 'NTPC', 'NTPCGREEN', 'NUVAMA', 'NUVOCO', 'NYKAA', 'OBEROIRLTY', 'OFSS', 'OIL', 'OLAELEC', 'OLECTRA', 'ONESOURCE', 'ONGC', 'PAGEIND', 'PATANJALI', 'PAYTM', 'PCBL', 'PEL', 'PERSISTENT', 'PETRONET', 'PFC', 'PFIZER', 'PGEL', 'PGHH', 'PHOENIXLTD', 'PIDILITIND', 'PIIND', 'PNB', 'PNBHOUSING', 'POLICYBZR', 'POLYCAB', 'POLYMED', 'POONAWALLA', 'POWERGRID', 'POWERINDIA', 'PPLPHARMA', 'PRAJIND', 'PREMIERENE', 'PRESTIGE', 'PSB', 'PTCIL', 'PVRINOX', 'RADICO', 'RAILTEL', 'RAINBOW', 'RAMCOCEM', 'RATNAMANI', 'RBLBANK', 'RCF', 'RECLTD', 'REDINGTON', 'RELIANCE', 'RELINFRA', 'RHIM', 'RITES', 'RKFORGE', 'RPOWER', 'RRKABEL', 'RVNL', 'SAGILITY', 'SAIL', 'SAILIFE', 'SAMMAANCAP', 'SAPPHIRE', 'SARDAEN', 'SAREGAMA', 'SBFC', 'SBICARD', 'SBILIFE', 'SBIN', 'SCHAEFFLER', 'SCHNEIDER', 'SCI', 'SHREECEM', 'SHRIRAMFIN', 'SHYAMMETL', 'SIEMENS', 'SIGNATURE', 'SJVN', 'SKFINDIA', 'SOBHA', 'SOLARINDS', 'SONACOMS', 'SONATSOFTW', 'SRF', 'STARHEALTH', 'SUMICHEM', 'SUNDARMFIN', 'SUNDRMFAST', 'SUNPHARMA', 'SUNTV', 'SUPREMEIND', 'SUZLON', 'SWANCORP', 'SWIGGY', 'SYNGENE', 'SYRMA', 'TARIL', 'TATACHEM', 'TATACOMM', 'TATACONSUM', 'TATAELXSI', 'TATAINVEST', 'TATAMOTORS', 'TATAPOWER', 'TATASTEEL', 'TATATECH', 'TBOTEK', 'TCS', 'TECHM', 'TECHNOE', 'TEJASNET', 'THELEELA', 'THERMAX', 'TIINDIA', 'TIMKEN', 'TITAGARH', 'TITAN', 'TMPV', 'TORNTPHARM', 'TORNTPOWER', 'TRENT', 'TRIDENT', 'TRITURBINE', 'TRIVENI', 'TTML', 'TVSMOTOR', 'UBL', 'UCOBANK', 'ULTRACEMCO', 'UNIMECH', 'UNIONBANK', 'UNITDSPR', 'UNOMINDA', 'UPL', 'USHAMART', 'UTIAMC', 'VBL', 'VEDL', 'VENTIVE', 'VGUARD', 'VIJAYA', 'VMM', 'VOLTAS', 'VTL', 'WAAREEENER', 'WELCORP', 'WELSPUNLIV', 'WESTLIFE', 'WHIRLPOOL', 'WIPRO', 'WOCKPHARMA', 'YESBANK', 'ZEEL', 'ZENSARTECH', 'ZENTEC', 'ZFCVINDIA', 'ZYDUSLIFE'
]


class Command(BaseCommand):
    help = 'Fetches Dhan instrument mapping and caches Symbol <-> Security ID in Redis for the Nifty 500 list.'

    def handle(self, *args, **options):
        # 1. Initialize Redis and Auth Check
        try:
            # Use SSL skip for Heroku Redis reliability
            r = redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None) 
            token = r.get(settings.REDIS_DHAN_TOKEN_KEY)
            if not token:
                raise CommandError("Dhan Access Token not found in Redis. Activate the trading session via the dashboard first.")
        except Exception as e:
            raise CommandError(f"Failed to connect/authenticate Redis: {e}")

        # 2. Initialize Dhan Client (Uses the robust import defined above)
        try:
            dhan_context = DhanContext(settings.DHAN_CLIENT_ID, token)
            dhan = dhanhq(dhan_context)
        except Exception as e:
            raise CommandError(f"Failed to initialize Dhan Client: {e}. Check DHAN_CLIENT_ID or token validity.")

        self.stdout.write(self.style.NOTICE(f"Client initialized. Fetching full security master list from Dhan..."))
        
        # 3. Fetch Full Security List
        try:
            response = dhan.fetch_security_list("full")
        except Exception as e:
            raise CommandError(f"Failed to fetch security list from Dhan API: {e}")

        if response.get('status') != 'success' or not response.get('data'):
            raise CommandError(f"Dhan API returned non-success response: {response}")

        # 4. Process and Map Symbols
        instrument_map = {}
        target_symbols = set(NIFTY_500_SYMBOLS)
        missing_symbols = set(target_symbols)
        total_instruments = 0

        for item in response['data']:
            symbol = item.get('tradingSymbol')
            security_id = item.get('securityId')
            exchange_segment = item.get('exchangeSegment')
            
            # Check if it's one of the target Nifty 500 symbols and necessary IDs are present
            if symbol and security_id and exchange_segment and symbol in target_symbols:
                instrument_map[symbol] = {
                    'security_id': str(security_id),
                    'exchange_segment': exchange_segment,
                    'symbol': symbol,
                }
                if symbol in missing_symbols:
                    missing_symbols.remove(symbol)
                total_instruments += 1

        # 5. Cache Results in Redis
        if instrument_map:
            try:
                # Store a single JSON blob containing the map.
                r.set(settings.SYMBOL_ID_MAP_KEY, json.dumps(instrument_map))
                self.stdout.write(self.style.SUCCESS(f"Successfully cached {total_instruments} instruments to Redis key: {settings.SYMBOL_ID_MAP_KEY}"))
                
                if missing_symbols:
                    self.stdout.write(self.style.WARNING(f"{len(missing_symbols)} symbols were not found or matched in the API response."))
                
            except Exception as e:
                raise CommandError(f"Failed to cache data in Redis: {e}")
        else:
            raise CommandError("No valid instruments were processed to cache. Check API response and list.")