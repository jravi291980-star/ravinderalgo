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
    help = 'Fetches T-1 OHLC data for all Nifty 500 stocks defined in settings.SECURITY_ID_MAP and caches PDH/PDL in Redis.'

    def handle(self, *args, **options):
        # 1. Initialize Redis
        try:
            # Use SSL skip for Heroku Redis reliability
            r = redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)
            token = r.get(settings.REDIS_DHAN_TOKEN_KEY)
            
            if not token:
                raise CommandError("Dhan Access Token not found in Redis. Activate the trading session via the dashboard first.")
        except Exception as e:
            raise CommandError(f"Failed to connect/authenticate Redis: {e}")

        # 2. Initialize Dhan Client (Robustly)
        dhan = get_dhan_client(settings.DHAN_CLIENT_ID, token)
        
        if not dhan:
            # Provide specific debugging info
            raise CommandError(f"Failed to initialize Dhan Client. Client ID: {settings.DHAN_CLIENT_ID}, Token Length: {len(token) if token else 0}. Check library version.")

        # 3. Prepare Date Range (Last 5 days to handle weekends/holidays)
        today = datetime.now()
        from_date_obj = today - timedelta(days=5) 
        to_date_obj = today - timedelta(days=1)   
        
        from_date = from_date_obj.strftime('%Y-%m-%d')
        to_date = to_date_obj.strftime('%Y-%m-%d')

        # Load Map directly from Settings
        instrument_map = settings.SECURITY_ID_MAP
        total_symbols = len(instrument_map)
        
        self.stdout.write(self.style.NOTICE(f"Fetching T-1 OHLC for {total_symbols} instruments (Range: {from_date} to {to_date})..."))

        ohlc_data_to_cache = {}
        processed_count = 0
        error_count = 0

        # 4. Iterate and Fetch Data
        for symbol, security_id in instrument_map.items():
            try:
                # API Call: Historical Daily Data
                response = dhan.historical_daily_data(
                    security_id=str(security_id),
                    exchange_segment=dhan.NSE, 
                    instrument_type='EQ',
                    from_date=from_date,
                    to_date=to_date
                )
                
                if response.get('status') == 'success' and response.get('data'):
                    data_list = response['data']
                    if data_list:
                        # Get the LAST candle in the list (most recent trading day)
                        prev_day_candle = data_list[-1]
                        
                        # Store essential breakout reference points
                        ohlc_data_to_cache[symbol] = json.dumps({
                            'high': prev_day_candle.get('high'),
                            'low': prev_day_candle.get('low'),
                            'close': prev_day_candle.get('close'),
                            'date': prev_day_candle.get('tradingDate') or prev_day_candle.get('start_Time')
                        })
                        processed_count += 1
                else:
                    error_count += 1
            
            except Exception:
                # Simple backoff
                time.sleep(0.05) 
                error_count += 1
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
                    self.stdout.write(self.style.WARNING(f"Failed to fetch data for {error_count} instruments."))
            
            except Exception as e:
                raise CommandError(f"Failed to write data to Redis: {e}")
        else:
            self.stdout.write(self.style.ERROR("No data fetched. Check API response, Market Status, or Date Range."))