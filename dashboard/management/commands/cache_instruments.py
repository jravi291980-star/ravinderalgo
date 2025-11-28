# # dashboard/management/commands/cache_instruments.py
# import json
# import os
# import time
# from datetime import datetime
# from django.core.management.base import BaseCommand, CommandError
# from django.conf import settings
# import redis
# from typing import Dict, List, Any, Optional

# # --- FIX: Robust Import of Dhan SDK components for Management Command ---
# # Import the client function and context conditionally to prevent module-level crashes
# try:
#     from dhanhq import DhanContext, dhanhq, MarketFeed
# except ImportError as e:
#     # If the import fails, we define placeholders, but the main code will crash gracefully below.
#     class DhanContext:
#         def __init__(self, client_id, access_token): pass
#     dhanhq = lambda ctx: None
#     MarketFeed = lambda: None
    
# # --- NIFTY 500 Symbol List (Placeholder representation) ---
# NIFTY_500_SYMBOLS = [
#     '360ONE', '3MINDIA', 'AADHARHFC', 'AARTIIND', 'AAVAS', 'ABB', 'ABBOTINDIA', 'ABCAPITAL', 'ABFRL', 'ABLBL', 'ABREL', 'ABSLAMC', 'ACC', 'ACE', 'ACMESOLAR', 'ADANIENSOL', 'ADANIENT', 'ADANIGREEN', 'ADANIPORTS', 'ADANIPOWER', 'ADVENTHTL', 'AEGISLOG', 'AEGISVOPAK', 'AFCONS', 'AFFLE', 'AGARWALEYE', 'AIAENG', 'AIIL', 'AJANTPHARM', 'AKUMS', 'AKZOINDIA', 'ALKEM', 'ALKYLAMINE', 'ALOKINDS', 'AMBER', 'AMBUJACEM', 'ANANDRATHI', 'ANANTRAJ', 'ANGELONE', 'APARINDS', 'APLAPOLLO', 'APLLTD', 'APOLLOHOSP', 'APOLLOTYRE', 'APTUS', 'ARE&M', 'ASAHIINDIA', 'ASHOKLEY', 'ASIANPAINT', 'ASTERDM', 'ASTRAL', 'ASTRAMICRO', 'ASTRAZEN', 'ATGL', 'ATHERENERG', 'ATUL', 'AUBANK', 'AUROPHARMA', 'AWL', 'AXISBANK', 'BAJAJ-AUTO', 'BAJAJFINSV', 'BAJAJHFL', 'BAJAJHLDNG', 'BAJFINANCE', 'BALKRISIND', 'BALRAMCHIN', 'BANDHANBNK', 'BANKBARODA', 'BANKINDIA', 'BASF', 'BATAINDIA', 'BAYERCROP', 'BBTC', 'BDL', 'BEL', 'BEML', 'BERGEPAINT', 'BHARATFORG', 'BHARTIARTL', 'BHARTIHEXA', 'BHEL', 'BIKAJI', 'BIOCON', 'BLS', 'BLUEDART', 'BLUEJET', 'BLUESTARCO', 'BOSCHLTD', 'BPCL', 'BRIGADE', 'BRITANNIA', 'BSE', 'BSOFT', 'CAMPUS', 'CAMS', 'CANBK', 'CANFINHOME', 'CAPLIPOINT', 'CARBORUNIV', 'CASTROLIND', 'CCL', 'CDSL', 'CEATLTD', 'CENTRALBK', 'CENTURYPLY', 'CERA', 'CESC', 'CGCL', 'CGPOWER', 'CHALET', 'CHAMBLFERT', 'CHENNPETRO', 'CHOICEIN', 'CHOLAFIN', 'CHOLAHLDNG', 'CIPLA', 'CLEAN', 'COALINDIA', 'COCHINSHIP', 'COFORGE', 'COHANCE', 'COLPAL', 'CONCOR', 'CONCORDBIO', 'COROMANDEL', 'CRAFTSMAN', 'CREDITACC', 'CRISIL', 'CROMPTON', 'CUB', 'CUMMINSIND', 'CYIENT', 'CYIENTDLM', 'DABUR', 'DALBHARAT', 'DATAPATTNS', 'DBCORP', 'DBREALTY', 'DCMSHRIRAM', 'DCXINDIA', 'DEEPAKFERT', 'DEEPAKNTR', 'DELHIVERY', 'DEVYANI', 'DIVISLAB', 'DIXON', 'DLF', 'DMART', 'DOMS', 'DRREDDY', 'DYNAMATECH', 'ECLERX', 'EICHERMOT', 'EIDPARRY', 'EIHOTEL', 'ELECON', 'ELGIEQUIP', 'EMAMILTD', 'EMCURE', 'ENDURANCE', 'ENGINERSIN', 'ENRIN', 'ERIS', 'ESCORTS', 'ETERNAL', 'EXIDEIND', 'FACT', 'FEDERALBNK', 'FINCABLES', 'FINPIPE', 'FIRSTCRY', 'FIVESTAR', 'FLUOROCHEM', 'FORCEMOT', 'FORTIS', 'FSL', 'GAIL', 'GESHIP', 'GICRE', 'GILLETTE', 'GLAND', 'GLAXO', 'GLENMARK', 'GMDCLTD', 'GMRAIRPORT', 'GODFRYPHLP', 'GODIGIT', 'GODREJAGRO', 'GODREJCP', 'GODREJIND', 'GODREJPROP', 'GPIL', 'GRANULES', 'GRAPHITE', 'GRASIM', 'GRAVITA', 'GRSE', 'GSPL', 'GUJGASLTD', 'GVT&D', 'HAL', 'HAPPSTMNDS', 'HATHWAY', 'HAVELLS', 'HBLENGINE', 'HCLTECH', 'HDFCAMC', 'HDFCBANK', 'HDFCLIFE', 'HEG', 'HEROMOTOCO', 'HEXT', 'HFCL', 'HINDALCO', 'HINDCOPPER', 'HINDPETRO', 'HINDUNILVR', 'HINDZINC', 'HOMEFIRST', 'HONASA', 'HONAUT', 'HSCL', 'HUDCO', 'HYUNDAI', 'ICICIBANK', 'ICICIGI', 'ICICIPRULI', 'IDBI', 'IDEA', 'IDFCFIRSTB', 'IEX', 'IFCI', 'IGIL', 'IGL', 'IIFL', 'IKS', 'INDGN', 'INDHOTEL', 'INDIACEM', 'INDIAMART', 'INDIANB', 'INDIGO', 'INDUSINDBK', 'INDUSTOWER', 'INFY', 'INOXINDIA', 'INOXWIND', 'INTELLECT', 'IOC', 'IPCALAB', 'IRB', 'IRCON', 'IRCTC', 'IREDA', 'IRFC', 'ITC', 'ITCHOTELS', 'ITI', 'J&KBANK', 'JBCHEPHARM', 'JBMA', 'JINDALSAW', 'JINDALSTEL', 'JIOFIN', 'JKCEMENT', 'JKTYRE', 'JMFINANCIL', 'JPPOWER', 'JSL', 'JSWENERGY', 'JSWINFRA', 'JSWSTEEL', 'JUBLFOOD', 'JUBLINGREA', 'JUBLPHARMA', 'JWL', 'JYOTHYLAB', 'JYOTICNC', 'KAJARIACER', 'KALYANKJIL', 'KARURVYSYA', 'KAYNES', 'KEC', 'KEI', 'KFINTECH', 'KIMS', 'KIRLOSBROS', 'KIRLOSENG', 'KOTAKBANK', 'KPIL', 'KPITTECH', 'KPRMILL', 'KSB', 'LALPATHLAB', 'LATENTVIEW', 'LAURUSLABS', 'LEMONTREE', 'LICHSGFIN', 'LICI', 'LINDEINDIA', 'LLOYDSME', 'LODHA', 'LT', 'LTF', 'LTFOODS', 'LTIM', 'LTTS', 'LUPIN', 'M&M', 'M&MFIN', 'MAHABANK', 'MAHSCOOTER', 'MAHSEAMLES', 'MANAPPURAM', 'MANKIND', 'MANYAVAR', 'MAPMYINDIA', 'MARICO', 'MARUTI', 'MAXHEALTH', 'MAZDOCK', 'MCX', 'MEDANTA', 'METROPOLIS', 'MFSL', 'MGL', 'MIDHANI', 'MINDACORP', 'MMTC', 'MOTHERSON', 'MOTILALOFS', 'MPHASIS', 'MRF', 'MRPL', 'MSUMI', 'MTARTECH', 'MUTHOOTFIN', 'NAM-INDIA', 'NATCOPHARM', 'NATIONALUM', 'NAUKRI', 'NAVA', 'NAVINFLUOR', 'NAZARA', 'NBCC', 'NCC', 'NESTLEIND', 'NETWEB', 'NETWORK18', 'NEULANDLAB', 'NEWGEN', 'NH', 'NHPC', 'NIACL', 'NIVABUPA', 'NLCINDIA', 'NMDC', 'NSLNISP', 'NTPC', 'NTPCGREEN', 'NUVAMA', 'NUVOCO', 'NYKAA', 'OBEROIRLTY', 'OFSS', 'OIL', 'OLAELEC', 'OLECTRA', 'ONESOURCE', 'ONGC', 'PAGEIND', 'PATANJALI', 'PAYTM', 'PCBL', 'PEL', 'PERSISTENT', 'PETRONET', 'PFC', 'PFIZER', 'PGEL', 'PGHH', 'PHOENIXLTD', 'PIDILITIND', 'PIIND', 'PNB', 'PNBHOUSING', 'POLICYBZR', 'POLYCAB', 'POLYMED', 'POONAWALLA', 'POWERGRID', 'POWERINDIA', 'PPLPHARMA', 'PRAJIND', 'PREMIERENE', 'PRESTIGE', 'PSB', 'PTCIL', 'PVRINOX', 'RADICO', 'RAILTEL', 'RAINBOW', 'RAMCOCEM', 'RATNAMANI', 'RBLBANK', 'RCF', 'RECLTD', 'REDINGTON', 'RELIANCE', 'RELINFRA', 'RHIM', 'RITES', 'RKFORGE', 'RPOWER', 'RRKABEL', 'RVNL', 'SAGILITY', 'SAIL', 'SAILIFE', 'SAMMAANCAP', 'SAPPHIRE', 'SARDAEN', 'SAREGAMA', 'SBFC', 'SBICARD', 'SBILIFE', 'SBIN', 'SCHAEFFLER', 'SCHNEIDER', 'SCI', 'SHREECEM', 'SHRIRAMFIN', 'SHYAMMETL', 'SIEMENS', 'SIGNATURE', 'SJVN', 'SKFINDIA', 'SOBHA', 'SOLARINDS', 'SONACOMS', 'SONATSOFTW', 'SRF', 'STARHEALTH', 'SUMICHEM', 'SUNDARMFIN', 'SUNDRMFAST', 'SUNPHARMA', 'SUNTV', 'SUPREMEIND', 'SUZLON', 'SWANCORP', 'SWIGGY', 'SYNGENE', 'SYRMA', 'TARIL', 'TATACHEM', 'TATACOMM', 'TATACONSUM', 'TATAELXSI', 'TATAINVEST', 'TATAMOTORS', 'TATAPOWER', 'TATASTEEL', 'TATATECH', 'TBOTEK', 'TCS', 'TECHM', 'TECHNOE', 'TEJASNET', 'THELEELA', 'THERMAX', 'TIINDIA', 'TIMKEN', 'TITAGARH', 'TITAN', 'TMPV', 'TORNTPHARM', 'TORNTPOWER', 'TRENT', 'TRIDENT', 'TRITURBINE', 'TRIVENI', 'TTML', 'TVSMOTOR', 'UBL', 'UCOBANK', 'ULTRACEMCO', 'UNIMECH', 'UNIONBANK', 'UNITDSPR', 'UNOMINDA', 'UPL', 'USHAMART', 'UTIAMC', 'VBL', 'VEDL', 'VENTIVE', 'VGUARD', 'VIJAYA', 'VMM', 'VOLTAS', 'VTL', 'WAAREEENER', 'WELCORP', 'WELSPUNLIV', 'WESTLIFE', 'WHIRLPOOL', 'WIPRO', 'WOCKPHARMA', 'YESBANK', 'ZEEL', 'ZENSARTECH', 'ZENTEC', 'ZFCVINDIA', 'ZYDUSLIFE'
# ]


# def get_dhan_client(client_id: str, token: str) -> Optional[object]:
#     """Tries to initialize the Dhan REST client and returns None on failure."""
#     try:
#         if not token:
#             return None
        
#         # Ensure imports are available inside this function scope
#         from dhanhq import DhanContext, dhanhq 
        
#         dhan_context = DhanContext(client_id, token)
#         dhan = dhanhq(dhan_context)
#         return dhan
#     except Exception as e:
#         # Catch any internal error during client instantiation
#         raise Exception(f"Dhan Client Initialization Failed with credentials: {e}")

# class Command(BaseCommand):
#     help = 'Fetches Dhan instrument mapping and caches Symbol <-> Security ID in Redis for the Nifty 500 list.'

#     def handle(self, *args, **options):
#         # 1. Initialize Redis and Auth Check
#         try:
#             r = redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None) 
#             token = r.get(settings.REDIS_DHAN_TOKEN_KEY)
            
#             if not token:
#                 raise CommandError("Dhan Access Token not found in Redis. Activate the trading session via the dashboard first.")
#         except Exception as e:
#             raise CommandError(f"Failed to connect/authenticate Redis: {e}")

#         # 2. Initialize Dhan Client (CRITICAL STEP)
#         self.stdout.write(self.style.NOTICE(f"Client initialized. Access Token retrieved."))
#         try:
#             dhan = get_dhan_client(settings.DHAN_CLIENT_ID, token)
#         except Exception as e:
#             raise CommandError(f"Critical Client Init Error: {e}")

#         if dhan is None:
#             # If get_dhan_client returns None (which is the root of the original error)
#             # We explicitly raise an error here to prevent the 'NoneType' traceback.
#              raise CommandError("Dhan client initialization failed (dhan object is None). Token/Client ID may be invalid.")


#         self.stdout.write(self.style.NOTICE(f"Client initialized. Fetching full security master list from Dhan..."))
        
#         # 3. Fetch Full Security List
#         try:
#             # The dhan object is confirmed non-None at this point
#             response = dhan.fetch_security_list("full")
#         except Exception as e:
#             # Catch API errors
#             raise CommandError(f"Failed to fetch security list from Dhan API: {e}")

#         if response.get('status') != 'success' or not response.get('data'):
#             raise CommandError(f"Dhan API returned non-success response (status: {response.get('status')}): {response}")

#         # 4. Process and Map Symbols
#         instrument_map = {}
#         target_symbols = set(NIFTY_500_SYMBOLS)
#         total_instruments = 0

#         for item in response['data']:
#             symbol = item.get('tradingSymbol')
#             security_id = item.get('securityId')
#             exchange_segment = item.get('exchangeSegment')
            
#             if symbol and security_id and exchange_segment and symbol in target_symbols:
#                 instrument_map[symbol] = {
#                     'security_id': str(security_id),
#                     'exchange_segment': exchange_segment,
#                     'symbol': symbol,
#                 }
#                 target_symbols.discard(symbol)
#                 total_instruments += 1

#         # 5. Cache Results in Redis
#         if instrument_map:
#             try:
#                 r.set(settings.SYMBOL_ID_MAP_KEY, json.dumps(instrument_map))
#                 self.stdout.write(self.style.SUCCESS(f"Successfully cached {total_instruments} instruments to Redis key: {settings.SYMBOL_ID_MAP_KEY}"))
                
#                 if target_symbols:
#                     self.stdout.write(self.style.WARNING(f"{len(target_symbols)} symbols were not found (e.g., newly listed or mismatch)."))
                
#             except Exception as e:
#                 raise CommandError(f"Failed to cache data in Redis: {e}")
#         else:
#             raise CommandError("No valid instruments were processed to cache. Check API response and token permissions.")

# dashboard/management/commands/cache_instruments.py
import json
import os
import time
import csv
import io
from datetime import datetime
from typing import Dict, List, Any, Optional

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

import redis
import requests

# --- NIFTY 500 Symbol List (Placeholder representation) ---
NIFTY_500_SYMBOLS = ['360ONE', '3MINDIA', 'AADHARHFC', 'AARTIIND', 'AAVAS', 'ABB', 'ABBOTINDIA', 'ABCAPITAL', 'ABFRL', 'ABLBL', 'ABREL', 'ABSLAMC', 'ACC', 'ACE', 'ACMESOLAR', 'ADANIENSOL', 'ADANIENT', 'ADANIGREEN', 'ADANIPORTS', 'ADANIPOWER', 'ADVENTHTL', 'AEGISLOG', 'AEGISVOPAK', 'AFCONS', 'AFFLE', 'AGARWALEYE', 'AIAENG', 'AIIL', 'AJANTPHARM', 'AKUMS', 'AKZOINDIA', 'ALKEM', 'ALKYLAMINE', 'ALOKINDS', 'AMBER', 'AMBUJACEM', 'ANANDRATHI', 'ANANTRAJ', 'ANGELONE', 'APARINDS', 'APLAPOLLO', 'APLLTD', 'APOLLOHOSP', 'APOLLOTYRE', 'APTUS', 'ARE&M', 'ASAHIINDIA', 'ASHOKLEY', 'ASIANPAINT', 'ASTERDM', 'ASTRAL', 'ASTRAMICRO', 'ASTRAZEN', 'ATGL', 'ATHERENERG', 'ATUL', 'AUBANK', 'AUROPHARMA', 'AWL', 'AXISBANK', 'BAJAJ-AUTO', 'BAJAJFINSV', 'BAJAJHFL', 'BAJAJHLDNG', 'BAJFINANCE', 'BALKRISIND', 'BALRAMCHIN', 'BANDHANBNK', 'BANKBARODA', 'BANKINDIA', 'BASF', 'BATAINDIA', 'BAYERCROP', 'BBTC', 'BDL', 'BEL', 'BEML', 'BERGEPAINT', 'BHARATFORG', 'BHARTIARTL', 'BHARTIHEXA', 'BHEL', 'BIKAJI', 'BIOCON', 'BLS', 'BLUEDART', 'BLUEJET', 'BLUESTARCO', 'BOSCHLTD', 'BPCL', 'BRIGADE', 'BRITANNIA', 'BSE', 'BSOFT', 'CAMPUS', 'CAMS', 'CANBK', 'CANFINHOME', 'CAPLIPOINT', 'CARBORUNIV', 'CASTROLIND', 'CCL', 'CDSL', 'CEATLTD', 'CENTRALBK', 'CENTURYPLY', 'CERA', 'CESC', 'CGCL', 'CGPOWER', 'CHALET', 'CHAMBLFERT', 'CHENNPETRO', 'CHOICEIN', 'CHOLAFIN', 'CHOLAHLDNG', 'CIPLA', 'CLEAN', 'COALINDIA', 'COCHINSHIP', 'COFORGE', 'COHANCE', 'COLPAL', 'CONCOR', 'CONCORDBIO', 'COROMANDEL', 'CRAFTSMAN', 'CREDITACC', 'CRISIL', 'CROMPTON', 'CUB', 'CUMMINSIND', 'CYIENT', 'CYIENTDLM', 'DABUR', 'DALBHARAT', 'DATAPATTNS', 'DBCORP', 'DBREALTY', 'DCMSHRIRAM', 'DCXINDIA', 'DEEPAKFERT', 'DEEPAKNTR', 'DELHIVERY', 'DEVYANI', 'DIVISLAB', 'DIXON', 'DLF', 'DMART', 'DOMS', 'DRREDDY', 'DYNAMATECH', 'ECLERX', 'EICHERMOT', 'EIDPARRY', 'EIHOTEL', 'ELECON', 'ELGIEQUIP', 'EMAMILTD', 'EMCURE', 'ENDURANCE', 'ENGINERSIN', 'ENRIN', 'ERIS', 'ESCORTS', 'ETERNAL', 'EXIDEIND', 'FACT', 'FEDERALBNK', 'FINCABLES', 'FINPIPE', 'FIRSTCRY', 'FIVESTAR', 'FLUOROCHEM', 'FORCEMOT', 'FORTIS', 'FSL', 'GAIL', 'GESHIP', 'GICRE', 'GILLETTE', 'GLAND', 'GLAXO', 'GLENMARK', 'GMDCLTD', 'GMRAIRPORT', 'GODFRYPHLP', 'GODIGIT', 'GODREJAGRO', 'GODREJCP', 'GODREJIND', 'GODREJPROP', 'GPIL', 'GRANULES', 'GRAPHITE', 'GRASIM', 'GRAVITA', 'GRSE', 'GSPL', 'GUJGASLTD', 'GVT&D', 'HAL', 'HAPPSTMNDS', 'HATHWAY', 'HAVELLS', 'HBLENGINE', 'HCLTECH', 'HDFCAMC', 'HDFCBANK', 'HDFCLIFE', 'HEG', 'HEROMOTOCO', 'HEXT', 'HFCL', 'HINDALCO', 'HINDCOPPER', 'HINDPETRO', 'HINDUNILVR', 'HINDZINC', 'HOMEFIRST', 'HONASA', 'HONAUT', 'HSCL', 'HUDCO', 'HYUNDAI', 'ICICIBANK', 'ICICIGI', 'ICICIPRULI', 'IDBI', 'IDEA', 'IDFCFIRSTB', 'IEX', 'IFCI', 'IGIL', 'IGL', 'IIFL', 'IKS', 'INDGN', 'INDHOTEL', 'INDIACEM', 'INDIAMART', 'INDIANB', 'INDIGO', 'INDUSINDBK', 'INDUSTOWER', 'INFY', 'INOXINDIA', 'INOXWIND', 'INTELLECT', 'IOC', 'IPCALAB', 'IRB', 'IRCON', 'IRCTC', 'IREDA', 'IRFC', 'ITC', 'ITCHOTELS', 'ITI', 'J&KBANK', 'JBCHEPHARM', 'JBMA', 'JINDALSAW', 'JINDALSTEL', 'JIOFIN', 'JKCEMENT', 'JKTYRE', 'JMFINANCIL', 'JPPOWER', 'JSL', 'JSWENERGY', 'JSWINFRA', 'JSWSTEEL', 'JUBLFOOD', 'JUBLINGREA', 'JUBLPHARMA', 'JWL', 'JYOTHYLAB', 'JYOTICNC', 'KAJARIACER', 'KALYANKJIL', 'KARURVYSYA', 'KAYNES', 'KEC', 'KEI', 'KFINTECH', 'KIMS', 'KIRLOSBROS', 'KIRLOSENG', 'KOTAKBANK', 'KPIL', 'KPITTECH', 'KPRMILL', 'KSB', 'LALPATHLAB', 'LATENTVIEW', 'LAURUSLABS', 'LEMONTREE', 'LICHSGFIN', 'LICI', 'LINDEINDIA', 'LLOYDSME', 'LODHA', 'LT', 'LTF', 'LTFOODS', 'LTIM', 'LTTS', 'LUPIN', 'M&M', 'M&MFIN', 'MAHABANK', 'MAHSCOOTER', 'MAHSEAMLES', 'MANAPPURAM', 'MANKIND', 'MANYAVAR', 'MAPMYINDIA', 'MARICO', 'MARUTI', 'MAXHEALTH', 'MAZDOCK', 'MCX', 'MEDANTA', 'METROPOLIS', 'MFSL', 'MGL', 'MIDHANI', 'MINDACORP', 'MMTC', 'MOTHERSON', 'MOTILALOFS', 'MPHASIS', 'MRF', 'MRPL', 'MSUMI', 'MTARTECH', 'MUTHOOTFIN', 'NAM-INDIA', 'NATCOPHARM', 'NATIONALUM', 'NAUKRI', 'NAVA', 'NAVINFLUOR', 'NAZARA', 'NBCC', 'NCC', 'NESTLEIND', 'NETWEB', 'NETWORK18', 'NEULANDLAB', 'NEWGEN', 'NH', 'NHPC', 'NIACL', 'NIVABUPA', 'NLCINDIA', 'NMDC', 'NSLNISP', 'NTPC', 'NTPCGREEN', 'NUVAMA', 'NUVOCO', 'NYKAA', 'OBEROIRLTY', 'OFSS', 'OIL', 'OLAELEC', 'OLECTRA', 'ONESOURCE', 'ONGC', 'PAGEIND', 'PATANJALI', 'PAYTM', 'PCBL', 'PEL', 'PERSISTENT', 'PETRONET', 'PFC', 'PFIZER', 'PGEL', 'PGHH', 'PHOENIXLTD', 'PIDILITIND', 'PIIND', 'PNB', 'PNBHOUSING', 'POLICYBZR', 'POLYCAB', 'POLYMED', 'POONAWALLA', 'POWERGRID', 'POWERINDIA', 'PPLPHARMA', 'PRAJIND', 'PREMIERENE', 'PRESTIGE', 'PSB', 'PTCIL', 'PVRINOX', 'RADICO', 'RAILTEL', 'RAINBOW', 'RAMCOCEM', 'RATNAMANI', 'RBLBANK', 'RCF', 'RECLTD', 'REDINGTON', 'RELIANCE', 'RELINFRA', 'RHIM', 'RITES', 'RKFORGE', 'RPOWER', 'RRKABEL', 'RVNL', 'SAGILITY', 'SAIL', 'SAILIFE', 'SAMMAANCAP', 'SAPPHIRE', 'SARDAEN', 'SAREGAMA', 'SBFC', 'SBICARD', 'SBILIFE', 'SBIN', 'SCHAEFFLER', 'SCHNEIDER', 'SCI', 'SHREECEM', 'SHRIRAMFIN', 'SHYAMMETL', 'SIEMENS', 'SIGNATURE', 'SJVN', 'SKFINDIA', 'SOBHA', 'SOLARINDS', 'SONACOMS', 'SONATSOFTW', 'SRF', 'STARHEALTH', 'SUMICHEM', 'SUNDARMFIN', 'SUNDRMFAST', 'SUNPHARMA', 'SUNTV', 'SUPREMEIND', 'SUZLON', 'SWANCORP', 'SWIGGY', 'SYNGENE', 'SYRMA', 'TARIL', 'TATACHEM', 'TATACOMM', 'TATACONSUM', 'TATAELXSI', 'TATAINVEST', 'TATAMOTORS', 'TATAPOWER', 'TATASTEEL', 'TATATECH', 'TBOTEK', 'TCS', 'TECHM', 'TECHNOE', 'TEJASNET', 'THELEELA', 'THERMAX', 'TIINDIA', 'TIMKEN', 'TITAGARH', 'TITAN', 'TMPV', 'TORNTPHARM', 'TORNTPOWER', 'TRENT', 'TRIDENT', 'TRITURBINE', 'TRIVENI', 'TTML', 'TVSMOTOR', 'UBL', 'UCOBANK', 'ULTRACEMCO', 'UNIMECH', 'UNIONBANK', 'UNITDSPR', 'UNOMINDA', 'UPL', 'USHAMART', 'UTIAMC', 'VBL', 'VEDL', 'VENTIVE', 'VGUARD', 'VIJAYA', 'VMM', 'VOLTAS', 'VTL', 'WAAREEENER', 'WELCORP', 'WELSPUNLIV', 'WESTLIFE', 'WHIRLPOOL', 'WIPRO', 'WOCKPHARMA', 'YESBANK', 'ZEEL', 'ZENSARTECH', 'ZENTEC', 'ZFCVINDIA', 'ZYDUSLIFE'
]


CSV_SCRIP_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"

def robust_imports():
    """
    Try several import paths for Dhan SDK that have been seen in different releases.
    Returns tuple (DhanContext_cls, dhan_factory_callable, MarketFeed_cls) or (None, None, None).
    """
    DhanContext = None
    dhan_factory = None
    MarketFeed = None

    import_errors = []

    try:
        # Preferred / documented import (many examples use this)
        from dhanhq import DhanContext as _D, dhanhq as _factory, MarketFeed as _M
        DhanContext, dhan_factory, MarketFeed = _D, _factory, _M
        return DhanContext, dhan_factory, MarketFeed
    except Exception as e:
        import_errors.append(f"root import failed: {e}")

    try:
        # Attempt likely submodule layout
        from dhanhq.dhan_context import DhanContext as _D
        from dhanhq.client import dhanhq as _factory
        # MarketFeed might not exist in older layouts
        try:
            from dhanhq.marketfeed import MarketFeed as _M
        except Exception:
            _M = None
        DhanContext, dhan_factory, MarketFeed = _D, _factory, _M
        return DhanContext, dhan_factory, MarketFeed
    except Exception as e:
        import_errors.append(f"submodule import failed: {e}")

    try:
        # Last resort: inspect top-level module exports
        import dhanhq as _d
        DhanContext = getattr(_d, "DhanContext", None)
        dhan_factory = getattr(_d, "dhanhq", None)
        MarketFeed = getattr(_d, "MarketFeed", None)
        if DhanContext and dhan_factory:
            return DhanContext, dhan_factory, MarketFeed
        else:
            import_errors.append("top-level dhanhq has no DhanContext/dhanhq exports")
    except Exception as e:
        import_errors.append(f"inspect top-level failed: {e}")

    # If we reach here, all attempts failed
    # For logging/diagnostics purposes return None tuple and errors can be inspected where called
    return None, None, None


def get_dhan_client(client_id: str, token: str) -> Optional[object]:
    """
    Tries to initialize the Dhan REST client and returns None on failure.
    We avoid raising here to let the caller decide whether to fallback to CSV.
    """
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


def fetch_instrument_map_from_csv(symbols_set: set) -> Dict[str, Dict[str, str]]:
    """
    Download Dhan's scrip master CSV and parse symbol -> securityId.
    Returns instrument_map like {symbol: {'security_id': '12345', ...}, ...}
    """
    try:
        resp = requests.get(CSV_SCRIP_MASTER_URL, timeout=20)
        resp.raise_for_status()
        text = resp.text
    except Exception as e:
        raise Exception(f"Failed to fetch instrument CSV from Dhan: {e}")

    instrument_map: Dict[str, Dict[str, str]] = {}
    f = io.StringIO(text)
    reader = csv.DictReader(f)
    for row in reader:
        # handle common field name variants
        sym = row.get("tradingSymbol") or row.get("symbol") or row.get("TradingSymbol")
        secid = row.get("securityId") or row.get("security_id") or row.get("SecurityID")
        exch = row.get("exchangeSegment") or row.get("exchange_segment") or row.get("ExchangeSegment") or ""
        if sym and secid and sym in symbols_set:
            instrument_map[sym] = {
                "security_id": str(secid),
                "exchange_segment": exch,
                "symbol": sym,
            }
    return instrument_map


class Command(BaseCommand):
    help = 'Fetches Dhan instrument mapping and caches Symbol <-> Security ID in Redis for the Nifty 500 list.'

    def handle(self, *args, **options):
        # Initialize Redis
        try:
            r = redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)
        except Exception as e:
            raise CommandError(f"Failed to connect to Redis (check REDIS_URL): {e}")

        token = None
        try:
            token = r.get(settings.REDIS_DHAN_TOKEN_KEY)
        except Exception:
            # Redis GET failed, but we still continue to attempt CSV fallback (it doesn't need token)
            token = None

        # Try SDK client first (if possible)
        dhan = None
        if token:
            dhan = get_dhan_client(settings.DHAN_CLIENT_ID, token)

        instrument_map: Dict[str, Dict[str, str]] = {}
        target_symbols = set(NIFTY_500_SYMBOLS)
        total_instruments = 0

        if dhan is not None:
            self.stdout.write(self.style.NOTICE("Dhan SDK client initialized — attempting API fetch of security list..."))
            try:
                response = dhan.fetch_security_list("full")
                # handle response shape robustly
                data = None
                if isinstance(response, dict):
                    data = response.get("data")
                elif hasattr(response, "data"):
                    data = getattr(response, "data")
                else:
                    data = response

                if not data:
                    raise Exception("Empty 'data' in SDK response.")
                for item in data:
                    symbol = item.get("tradingSymbol") or item.get("tradingSymbol".lower())
                    security_id = item.get("securityId") or item.get("securityId".lower())
                    exchange_segment = item.get("exchangeSegment") or item.get("exchangeSegment".lower())
                    if symbol and security_id and exchange_segment and symbol in target_symbols:
                        instrument_map[symbol] = {
                            "security_id": str(security_id),
                            "exchange_segment": exchange_segment,
                            "symbol": symbol,
                        }
                        target_symbols.discard(symbol)
                        total_instruments += 1

                self.stdout.write(self.style.SUCCESS(f"SDK: mapped {total_instruments} instruments via Dhan API."))

            except Exception as e:
                # SDK failed at runtime — fall back to CSV
                self.stdout.write(self.style.WARNING(f"Dhan SDK fetch failed: {e}. Falling back to CSV fetch."))

        # If SDK wasn't available or didn't yield items, use CSV fallback
        if not instrument_map:
            self.stdout.write(self.style.NOTICE("Fetching instrument master via Dhan's public CSV (fallback)..."))
            try:
                csv_map = fetch_instrument_map_from_csv(set(NIFTY_500_SYMBOLS))
                instrument_map.update(csv_map)
                total_instruments = len(instrument_map)
                self.stdout.write(self.style.SUCCESS(f"CSV: mapped {total_instruments} instruments from CSV endpoint."))
            except Exception as e:
                raise CommandError(f"Both SDK and CSV fetch failed: {e}")

        # Cache Results in Redis
        if instrument_map:
            try:
                r.set(settings.SYMBOL_ID_MAP_KEY, json.dumps(instrument_map))
                self.stdout.write(self.style.SUCCESS(f"Successfully cached {total_instruments} instruments to Redis key: {settings.SYMBOL_ID_MAP_KEY}"))
                if target_symbols:
                    # If some symbols remained unfound, warn the user
                    missing = [s for s in NIFTY_500_SYMBOLS if s not in instrument_map]
                    self.stdout.write(self.style.WARNING(f"{len(missing)} symbols were not found (examples): {missing[:8]}"))
            except Exception as e:
                raise CommandError(f"Failed to cache data in Redis: {e}")
        else:
            raise CommandError("No valid instruments were processed to cache. Check CSV/API and token permissions.")
