# dashboard/management/commands/fetch_prev_day_ohlc.py
import json
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from dhanhq import DhanContext, dhanhq
import redis
import time


class Command(BaseCommand):
    help = 'Fetches previous day (T-1) OHLC data for all tracked symbols and caches PDH/PDL in Redis.'

    def handle(self, *args, **options):
        # 1. Initialize Redis and Auth Check
        try:
            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            token = r.get(settings.REDIS_DHAN_TOKEN_KEY)
            if not token:
                raise CommandError("Dhan Access Token not found.")
        except Exception as e:
            raise CommandError(f"Failed to connect/authenticate Redis: {e}")

        # 2. Initialize Dhan Client
        try:
            dhan_context = DhanContext(settings.DHAN_CLIENT_ID, token)
            dhan = dhanhq(dhan_context)
        except Exception as e:
            raise CommandError(f"Failed to initialize Dhan Client: {e}")

        # 3. Load Instrument Map
        instrument_map_raw = r.get(settings.SYMBOL_ID_MAP_KEY)
        if not instrument_map_raw:
            raise CommandError(f"Instrument map missing. Run 'cache_instruments' first.")

        instrument_map = json.loads(instrument_map_raw)

        # Determine the date range (Yesterday's date)
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        from_date = yesterday.strftime('%Y-%m-%d')
        to_date = yesterday.strftime('%Y-%m-%d')

        self.stdout.write(
            self.style.NOTICE(f"Fetching daily OHLC for {len(instrument_map)} instruments for date {from_date}..."))

        # 4. Fetch Historical Data and Cache OHLC
        ohlc_cached_count = 0
        ohlc_data_to_cache = {}

        for symbol, instrument in instrument_map.items():
            security_id = instrument['security_id']
            exchange_segment = instrument['exchange_segment']

            try:
                # Use historical_daily_data endpoint
                response = dhan.historical_daily_data(
                    security_id=security_id,
                    exchange_segment=exchange_segment,
                    instrument_type='EQ',  # Equity segment
                    from_date=from_date,
                    to_date=to_date
                )

                # Check for rate limit or API error before continuing
                if response.get('status') == 'error' and 'rate limit' in response.get('message', '').lower():
                    self.stdout.write(self.style.ERROR(f"Rate limit hit! Stopping command."))
                    break

                if response.get('status') == 'success' and response.get('data'):
                    daily_candle = response['data'][0]

                    # Store required data: high, low, close
                    ohlc_data_to_cache[symbol] = json.dumps({
                        'high': daily_candle.get('high'),
                        'low': daily_candle.get('low'),
                        'close': daily_candle.get('close'),
                        'date': daily_candle.get('datetime')
                    })
                    ohlc_cached_count += 1

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Failed to fetch data for {symbol}: {e}"))
                time.sleep(0.1)  # Soft rate limit protection for Dhan API

        # 5. Atomic Hash Update in Redis
        if ohlc_data_to_cache:
            try:
                r.hmset(settings.PREV_DAY_HASH, ohlc_data_to_cache)
                self.stdout.write(self.style.SUCCESS(
                    f"Successfully cached PDH/PDL for {ohlc_cached_count} instruments to Redis Hash: {settings.PREV_DAY_HASH}"))
            except Exception as e:
                raise CommandError(f"Failed to cache OHLC data in Redis: {e}")
        else:
            self.stdout.write(self.style.WARNING("No valid daily OHLC data was retrieved."))