# dashboard/management/commands/fetch_prev_day_ohlc.py
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import redis

# --- Global Helper for Dhan Client Initialization (Robust) ---
def get_dhan_client(client_id: str, access_token: str) -> Optional[object]:
    """
    Initializes and returns the Dhan REST client using the most compatible
    DhanHQ SDK pattern, handling version differences on Heroku.
    """
    if not access_token or not client_id:
        return None
    
    try:
        # A. RECOMMENDED: Try the current v2.1+ context-based pattern
        from dhanhq import DhanContext, dhanhq 
        dhan_context = DhanContext(client_id, access_token) 
        dhan = dhanhq(dhan_context) 
        return dhan
    except ImportError:
        try:
            # B. FALLBACK: Try the older v1 direct instantiation pattern
            import dhanhq
            dhan = dhanhq.dhanhq(client_id, access_token)
            return dhan
        except Exception:
            return None
    except Exception:
        return None

class Command(BaseCommand):
    help = 'Fetches OHLC data for Nifty 500 stocks and caches the Last Traded Day (PDH/PDL) in Redis.'

    def handle(self, *args, **options):
        # 1. Initialize Redis
        try:
            r = redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)
            token = r.get(settings.REDIS_DHAN_TOKEN_KEY)
            
            if not token:
                raise CommandError("Dhan Access Token not found in Redis. Activate via dashboard.")
        except Exception as e:
            raise CommandError(f"Redis Error: {e}")

        # 2. Initialize Dhan Client
        dhan = get_dhan_client(settings.DHAN_CLIENT_ID, token)
        if not dhan:
            raise CommandError("Failed to initialize Dhan Client. Check Client ID/Token.")

        # 3. Prepare Date Range (Last 15 days to catch the last valid trading session)
        today = datetime.now()
        from_date_obj = today - timedelta(days=15) 
        to_date_obj = today 
        
        from_date = from_date_obj.strftime('%Y-%m-%d')
        to_date = to_date_obj.strftime('%Y-%m-%d')

        instrument_map = settings.SECURITY_ID_MAP
        total_symbols = len(instrument_map)
        
        self.stdout.write(self.style.NOTICE(f"Fetching Historical Data for {total_symbols} instruments ({from_date} to {to_date})..."))

        ohlc_data_to_cache = {}
        processed_count = 0
        error_count = 0

        # 4. Iterate and Fetch Data
        for i, (symbol, security_id) in enumerate(instrument_map.items()):
            try:
                # API Call: Historical Daily Data
                # FIX: Changed instrument_type to 'EQUITY' based on standard usage
                response = dhan.historical_daily_data(
                    security_id=str(security_id),
                    exchange_segment=dhan.NSE, 
                    instrument_type='EQUITY', 
                    from_date=from_date,
                    to_date=to_date
                )
                
                # DEBUG: Print the first response to diagnose API format issues
                if i == 0:
                    print(f"DEBUG RESP ({symbol}): {response}")

                if response.get('status') == 'success' and response.get('data'):
                    data_list = response['data']
                    # Dhan v2 historical data is often a dict with keys like 'start_Time', 'open', etc. lists
                    # OR a list of dicts. We handle the list of dicts format here.
                    
                    if isinstance(data_list, list) and len(data_list) > 0:
                        # Get the LAST candle (Most recent completed session)
                        # This automatically handles weekends/holidays
                        prev_day_candle = data_list[-1]
                        
                        ohlc_data_to_cache[symbol] = json.dumps({
                            'high': float(prev_day_candle.get('high', 0)),
                            'low': float(prev_day_candle.get('low', 0)),
                            'close': float(prev_day_candle.get('close', 0)),
                            'date': prev_day_candle.get('tradingDate') or prev_day_candle.get('start_Time')
                        })
                        processed_count += 1
                    # Handle v2 format where data might be a dict of lists (rare but possible in some versions)
                    elif isinstance(data_list, dict) and 'high' in data_list:
                         # Assume list structure inside dict
                         highs = data_list.get('high', [])
                         lows = data_list.get('low', [])
                         closes = data_list.get('close', [])
                         if highs:
                             ohlc_data_to_cache[symbol] = json.dumps({
                                 'high': float(highs[-1]),
                                 'low': float(lows[-1]),
                                 'close': float(closes[-1]),
                                 'date': 'latest'
                             })
                             processed_count += 1
                else:
                    error_count += 1
            
            except Exception as e:
                # Simple backoff to respect rate limits
                time.sleep(0.05) 
                error_count += 1
                if i == 0: print(f"DEBUG ERROR ({symbol}): {e}")
                continue
            
            # Gentle rate limiting
            if processed_count % 10 == 0:
                time.sleep(0.1)

        # 5. Atomic Save to Redis
        if ohlc_data_to_cache:
            try:
                r.hmset(settings.PREV_DAY_HASH, ohlc_data_to_cache)
                self.stdout.write(self.style.SUCCESS(f"Successfully cached PDH/PDL for {processed_count} instruments to Redis key: {settings.PREV_DAY_HASH}"))
                
                if error_count > 0:
                    self.stdout.write(self.style.WARNING(f"Skipped {error_count} instruments (No data/API Error). Check Debug logs."))
            
            except Exception as e:
                raise CommandError(f"Failed to write data to Redis: {e}")
        else:
            self.stdout.write(self.style.ERROR("No data fetched. Review the DEBUG RESP output above."))