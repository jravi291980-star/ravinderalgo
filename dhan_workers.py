# # # dhan_workers.py - Runs on the Worker Dyno
# # import redis
# # import json
# # import os
# # import time
# # import threading
# # import sys
# # from datetime import datetime
# # from typing import Dict, List, Any, Optional

# # # --- Django Environment Setup ---
# # sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# # os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'algotrader.settings')

# # import django
# # django.setup()
# # from django.conf import settings

# # # --- ROBUST REAL IMPORT (FIXED) ---
# # # We try specific submodule paths which are more reliable than top-level imports
# # DhanContext = None
# # dhanhq = None
# # MarketFeed = None
# # OrderUpdate = None

# # try:
# #     # Attempt 1: Top-level import (Standard Documentation)
# #     from dhanhq import DhanContext, dhanhq, MarketFeed, OrderUpdate
# #     print("Imported DhanHQ from top-level.")
# # except ImportError as e1:
# #     print(f"Top-level import failed ({e1}). Trying submodules...")
# #     try:
# #         # Attempt 2: Explicit Submodules (Fix for 'cannot import name' errors)
# #         # The core classes often live in 'dhanhq.dhanhq' or similar paths
# #         from dhanhq.dhanhq import DhanContext, dhanhq
# #         from dhanhq.marketfeed import MarketFeed
# #         from dhanhq.order_update import OrderUpdate
# #         print("Imported DhanHQ from submodules.")
# #     except ImportError as e2:
# #         print(f"CRITICAL: Failed to import DhanHQ library. Error 1: {e1}, Error 2: {e2}")
# #         # inspect what IS available to help debugging next time
# #         import dhanhq as _d
# #         print(f"dhanhq module contents: {dir(_d)}")
# #         sys.exit(1)

# # # --- Configuration ---
# # r = redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)

# # INSTRUMENTS_TO_SUBSCRIBE: List[tuple] = []

# # def get_dhan_context(client_id: str, token: str) -> Optional[Any]:
# #     if not token: return None
# #     try:
# #         return DhanContext(client_id, token)
# #     except Exception as e:
# #         print(f"Error creating context: {e}")
# #         return None

# # def build_subscription_list() -> List[tuple]:
# #     """
# #     Constructs the subscription list directly from settings.SECURITY_ID_MAP.
# #     """
# #     subscription_list = []
# #     try:
# #         # Load map from Django settings
# #         instrument_map = settings.SECURITY_ID_MAP
        
# #         for symbol, security_id in instrument_map.items():
# #             # Dhan MarketFeed expects: (ExchangeSegment, SecurityID, Mode)
# #             # Hardcoding constants to avoid AttributeError if class constants are missing
# #             # 1 = NSE Equity
# #             # 4 = Full Packet
# #             subscription_list.append((
# #                 1, 
# #                 str(security_id), 
# #                 4
# #             ))
            
# #         print(f"[{datetime.now()}] Configured {len(subscription_list)} instruments from Settings.")
# #         return subscription_list

# #     except Exception as e:
# #         print(f"[{datetime.now()}] ERROR building subscription list: {e}")
# #         return []

# # # --- STREAM PRODUCERS (XADD) ---

# # def on_market_feed_message(instance, message):
# #     """Pushes market data to Redis Stream."""
# #     try:
# #         if message:
# #             r.xadd(
# #                 settings.REDIS_STREAM_MARKET, 
# #                 {'p': json.dumps(message)}, 
# #                 maxlen=20000, 
# #                 approximate=True
# #             )
# #     except Exception as e:
# #         print(f"Stream Write Error (Market): {e}")

# # def run_market_feed_worker(dhan_context):
# #     while True:
# #         try:
# #             print(f"[{datetime.now()}] MarketFeed: Connecting to LIVE Dhan WebSocket...")
# #             market_client = MarketFeed(dhan_context, INSTRUMENTS_TO_SUBSCRIBE, version="v2")
# #             market_client.on_message = on_market_feed_message
# #             market_client.run_forever()
# #         except Exception as e:
# #             print(f"[{datetime.now()}] MarketFeed DOWN: {e}. Retry in 5s...")
# #             time.sleep(5)

# # def on_order_update_message(order_data):
# #     """Pushes Order Updates to Redis Stream."""
# #     try:
# #         payload = order_data.get('Data', order_data)
# #         if payload:
# #             r.xadd(
# #                 settings.REDIS_STREAM_ORDERS, 
# #                 {'p': json.dumps(payload)}
# #             )
# #             print(f"[{datetime.now()}] Order Update pushed to Stream.")
# #     except Exception as e:
# #         print(f"Stream Write Error (Order): {e}")

# # def run_order_update_worker(dhan_context):
# #     while True:
# #         try:
# #             print(f"[{datetime.now()}] OrderUpdate: Connecting to LIVE Dhan WebSocket...")
# #             order_client = OrderUpdate(dhan_context)
# #             order_client.on_update = on_order_update_message
# #             order_client.connect_to_dhan_websocket_sync()
# #         except Exception as e:
# #             print(f"[{datetime.now()}] OrderUpdate DOWN: {e}. Retry in 5s...")
# #             time.sleep(5)

# # # --- Main ---

# # def main_worker_loop():
# #     global INSTRUMENTS_TO_SUBSCRIBE
# #     r.set(settings.REDIS_STATUS_DATA_ENGINE, 'STARTING')
    
# #     token = r.get(settings.REDIS_DHAN_TOKEN_KEY)
# #     while not token:
# #         print("Waiting for Access Token in Redis...")
# #         time.sleep(5)
# #         token = r.get(settings.REDIS_DHAN_TOKEN_KEY)

# #     dhan_context = get_dhan_context(settings.DHAN_CLIENT_ID, token)
    
# #     # Build list
# #     INSTRUMENTS_TO_SUBSCRIBE = build_subscription_list()
    
# #     if not INSTRUMENTS_TO_SUBSCRIBE:
# #         r.set(settings.REDIS_STATUS_DATA_ENGINE, 'FATAL_ERROR_NO_INSTRUMENTS')
# #         print("No instruments found in settings map.")
# #         return

# #     # Start Threads
# #     market_thread = threading.Thread(target=run_market_feed_worker, args=(dhan_context,), daemon=True)
# #     order_thread = threading.Thread(target=run_order_update_worker, args=(dhan_context,), daemon=True)

# #     market_thread.start()
# #     order_thread.start()

# #     r.set(settings.REDIS_STATUS_DATA_ENGINE, 'RUNNING')
# #     print("Data Engine Running (REAL LIVE MODE).")
    
# #     market_thread.join()
# #     order_thread.join()

# # if __name__ == '__main__':
# #     main_worker_loop()


# # dhan_workers.py - Runs on the Worker Dyno
# import redis
# import json
# import os
# import time
# import threading
# import sys
# from datetime import datetime
# from typing import Dict, List, Any, Optional

# # --- Django Environment Setup ---
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'algotrader.settings')

# import django
# django.setup()
# from django.conf import settings

# # --- LIBRARY VERSION CHECK ---
# import dhanhq as dhan_lib
# print(f"[{datetime.now()}] INSTALLED DHANHQ VERSION: {getattr(dhan_lib, '__version__', 'Unknown')}")

# # --- V2.1+ IMPORT ---
# # We now expect this to work because requirements.txt enforces >=2.1.0
# try:
#     from dhanhq import DhanContext, dhanhq, MarketFeed, OrderUpdate
# except ImportError as e:
#     print(f"CRITICAL ERROR: DhanHQ library components missing. Ensure dhanhq>=2.1.0 is installed. Error: {e}")
#     sys.exit(1)

# # --- Configuration ---
# r = redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)

# INSTRUMENTS_TO_SUBSCRIBE: List[tuple] = []

# def get_dhan_context(client_id: str, token: str) -> Optional[DhanContext]:
#     if not token: return None
#     try:
#         return DhanContext(client_id, token)
#     except Exception as e:
#         print(f"Error creating DhanContext: {e}")
#         return None

# def build_subscription_list() -> List[tuple]:
#     """Constructs subscription list from settings.SECURITY_ID_MAP."""
#     subscription_list = []
#     try:
#         instrument_map = settings.SECURITY_ID_MAP
        
#         # Try to use library constants if available, else hardcode
#         try:
#             EXCH_NSE = MarketFeed.NSE
#             MODE_FULL = MarketFeed.Full
#         except AttributeError:
#             EXCH_NSE = 1
#             MODE_FULL = 4

#         for symbol, security_id in instrument_map.items():
#             subscription_list.append((EXCH_NSE, str(security_id), MODE_FULL))
            
#         print(f"[{datetime.now()}] Configured {len(subscription_list)} instruments from Settings.")
#         return subscription_list

#     except Exception as e:
#         print(f"[{datetime.now()}] ERROR building subscription list: {e}")
#         return []

# # --- WORKERS ---

# def on_market_feed_message(instance, message):
#     """Pushes market data to Redis Stream."""
#     try:
#         if message:
#             r.xadd(settings.REDIS_STREAM_MARKET, {'p': json.dumps(message)}, maxlen=20000, approximate=True)
#     except Exception as e:
#         print(f"Stream Write Error (Market): {e}")

# def run_market_feed_worker(dhan_context):
#     while True:
#         try:
#             print(f"[{datetime.now()}] MarketFeed: Connecting to LIVE Dhan WebSocket...")
#             # v2.1+ syntax: Pass context directly
#             market_client = MarketFeed(dhan_context, INSTRUMENTS_TO_SUBSCRIBE, version="v2")
#             market_client.on_message = on_market_feed_message
#             market_client.run_forever()
#         except Exception as e:
#             print(f"[{datetime.now()}] MarketFeed Connection Error: {e}. Reconnecting in 5s...")
#             time.sleep(5)

# def on_order_update_message(order_data):
#     """Pushes Order Updates to Redis Stream."""
#     try:
#         payload = order_data.get('Data', order_data)
#         if payload:
#             r.xadd(settings.REDIS_STREAM_ORDERS, {'p': json.dumps(payload)})
#             print(f"[{datetime.now()}] LIVE ORDER UPDATE pushed to stream.")
#     except Exception as e:
#         print(f"Stream Write Error (Order): {e}")

# def run_order_update_worker(dhan_context):
#     while True:
#         try:
#             print(f"[{datetime.now()}] OrderUpdate: Connecting to LIVE Dhan WebSocket...")
#             # v2.1+ syntax: Pass context directly
#             order_client = OrderUpdate(dhan_context)
#             order_client.on_update = on_order_update_message
#             order_client.connect_to_dhan_websocket_sync()
#         except Exception as e:
#             print(f"[{datetime.now()}] OrderUpdate Connection Error: {e}. Reconnecting in 5s...")
#             time.sleep(5)

# # --- MAIN ---

# def main_worker_loop():
#     global INSTRUMENTS_TO_SUBSCRIBE
#     r.set(settings.REDIS_STATUS_DATA_ENGINE, 'STARTING')
    
#     token = r.get(settings.REDIS_DHAN_TOKEN_KEY)
#     while not token:
#         print("Waiting for Access Token in Redis (Paste in Dashboard)...")
#         time.sleep(5)
#         token = r.get(settings.REDIS_DHAN_TOKEN_KEY)

#     dhan_context = get_dhan_context(settings.DHAN_CLIENT_ID, token)
#     if not dhan_context:
#         print("Failed to create Dhan Context. Check Client ID.")
#         return

#     INSTRUMENTS_TO_SUBSCRIBE = build_subscription_list()
#     if not INSTRUMENTS_TO_SUBSCRIBE:
#         r.set(settings.REDIS_STATUS_DATA_ENGINE, 'FATAL_ERROR_NO_INSTRUMENTS')
#         return

#     # Start Threads
#     market_thread = threading.Thread(target=run_market_feed_worker, args=(dhan_context,), daemon=True)
#     order_thread = threading.Thread(target=run_order_update_worker, args=(dhan_context,), daemon=True)

#     market_thread.start()
#     order_thread.start()

#     r.set(settings.REDIS_STATUS_DATA_ENGINE, 'RUNNING')
#     print("Data Engine Running (REAL LIVE MODE - v2.1+).")
    
#     market_thread.join()
#     order_thread.join()

# if __name__ == '__main__':
#     main_worker_loop()

# dhan_workers.py - Runs on the Worker Dyno
# import redis
# import json
# import os
# import time
# import threading
# import sys
# import asyncio # <--- Essential for fixing the event loop error
# from datetime import datetime
# from typing import Dict, List, Any, Optional

# # --- Django Setup ---
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'algotrader.settings')

# import django
# django.setup()
# from django.conf import settings

# # --- Robust Import ---
# try:
#     from dhanhq import DhanContext, dhanhq, MarketFeed, OrderUpdate
# except ImportError:
#     try:
#         from dhanhq.dhanhq import DhanContext, dhanhq
#         from dhanhq.marketfeed import MarketFeed
#         from dhanhq.order_update import OrderUpdate
#     except ImportError:
#         print("CRITICAL: DhanHQ library not found or incompatible.")
#         sys.exit(1)

# # --- Configuration ---
# r = redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)
# IST = settings.IST

# SECURITY_ID_TO_SYMBOL = {str(v): k for k, v in settings.SECURITY_ID_MAP.items()}

# INSTRUMENTS_TO_SUBSCRIBE: List[tuple] = []

# # --- CANDLE AGGREGATOR CLASS ---
# class LiveCandleAggregator:
#     def __init__(self, redis_conn):
#         self.r = redis_conn
#         self.aggregators: Dict[str, Dict[str, Any]] = {} 
#         self.last_ltp: Dict[str, float] = {}

#     def process_tick(self, tick_data: Dict[str, Any]):
#         security_id = str(tick_data.get('securityId', ''))
#         ltp = float(tick_data.get('LTP') or tick_data.get('last_price') or tick_data.get('lp') or 0.0)
        
#         ts_raw = tick_data.get('exchange_time') or tick_data.get('LTT')
#         if ts_raw:
#             try:
#                 if int(ts_raw) > 10000000000: timestamp = datetime.fromtimestamp(int(ts_raw) / 1000, tz=IST)
#                 else: timestamp = datetime.fromtimestamp(int(ts_raw), tz=IST)
#             except: timestamp = datetime.now(IST)
#         else: timestamp = datetime.now(IST)

#         if not security_id or ltp == 0: return

#         self.last_ltp[security_id] = ltp
        
#         candle_ts = timestamp.replace(second=0, microsecond=0)
        
#         if security_id in self.aggregators:
#             current = self.aggregators[security_id]
#             if candle_ts > current['ts']:
#                 self.finalize_candle(current)
#                 self.aggregators[security_id] = self._new_candle(security_id, candle_ts, ltp)
#             else:
#                 current['high'] = max(current['high'], ltp)
#                 current['low'] = min(current['low'], ltp)
#                 current['close'] = ltp
#         else:
#             self.aggregators[security_id] = self._new_candle(security_id, candle_ts, ltp)

#     def _new_candle(self, sec_id, ts, price):
#         return {'security_id': sec_id, 'ts': ts, 'open': price, 'high': price, 'low': price, 'close': price}

#     def finalize_candle(self, candle):
#         symbol = SECURITY_ID_TO_SYMBOL.get(candle['security_id'])
#         if not symbol: return

#         payload = {
#             'symbol': symbol,
#             'security_id': candle['security_id'],
#             'ts': candle['ts'].isoformat(),
#             'open': candle['open'],
#             'high': candle['high'],
#             'low': candle['low'],
#             'close': candle['close']
#         }
#         payload_json = json.dumps(payload)

#         history_key = f"{settings.HISTORY_KEY_PREFIX}:{candle['security_id']}:1m"
#         self.r.rpush(history_key, payload_json)
#         self.r.ltrim(history_key, -400, -1) 

#         try:
#             self.r.xadd(settings.REDIS_STREAM_CANDLES, {'p': payload_json})
#         except Exception as e:
#             print(f"Stream Error: {e}")

# # --- Worker Logic ---

# aggregator = LiveCandleAggregator(r)

# def get_dhan_context(client_id: str, token: str) -> Optional[DhanContext]:
#     if not token: return None
#     try:
#         return DhanContext(client_id, token)
#     except: return None

# def build_subscription_list() -> List[tuple]:
#     lst = []
#     try:
#         for symbol, security_id in settings.SECURITY_ID_MAP.items():
#             lst.append((1, str(security_id), 4)) 
#         print(f"[{datetime.now()}] Subscribing to {len(lst)} instruments.")
#         return lst
#     except Exception as e:
#         print(f"Error building list: {e}")
#         return []

# def on_market_feed_message(instance, message):
#     try:
#         if message:
#             aggregator.process_tick(message)
#     except Exception:
#         pass

# def run_market_feed_worker(dhan_context):
#     """Runs the MarketFeed in a dedicated thread with its own event loop."""
    
#     # CRITICAL FIX: Create a new event loop for this thread
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
    
#     while True:
#         try:
#             print(f"[{datetime.now()}] MarketFeed: Connecting...")
#             client = MarketFeed(dhan_context, INSTRUMENTS_TO_SUBSCRIBE, version="v2")
#             client.on_message = on_market_feed_message
#             client.run_forever()
#         except Exception as e:
#             print(f"MarketFeed Error: {e}. Retry in 5s...")
#             time.sleep(5)

# def on_order_update_message(order_data):
#     try:
#         payload = order_data.get('Data', order_data)
#         if payload:
#             r.xadd(settings.REDIS_STREAM_ORDERS, {'p': json.dumps(payload)})
#             print(f"[{datetime.now()}] Order Update pushed.")
#     except Exception as e:
#         print(f"Order Stream Error: {e}")

# def run_order_update_worker(dhan_context):
#     """Runs OrderUpdate in a dedicated thread with its own event loop."""
    
#     # CRITICAL FIX: Create a new event loop for this thread
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)

#     while True:
#         try:
#             print(f"[{datetime.now()}] OrderUpdate: Connecting...")
#             client = OrderUpdate(dhan_context)
#             client.on_update = on_order_update_message
#             client.connect_to_dhan_websocket_sync()
#         except Exception as e:
#             print(f"OrderUpdate Error: {e}. Retry in 5s...")
#             time.sleep(5)

# def main_worker_loop():
#     global INSTRUMENTS_TO_SUBSCRIBE
#     r.set(settings.REDIS_STATUS_DATA_ENGINE, 'STARTING')
    
#     token = r.get(settings.REDIS_DHAN_TOKEN_KEY)
#     while not token:
#         print("Waiting for Access Token in Redis...")
#         time.sleep(5)
#         token = r.get(settings.REDIS_DHAN_TOKEN_KEY)

#     dhan_context = get_dhan_context(settings.DHAN_CLIENT_ID, token)
#     if not dhan_context:
#         r.set(settings.REDIS_STATUS_DATA_ENGINE, 'FATAL_ERROR_CONTEXT')
#         return

#     INSTRUMENTS_TO_SUBSCRIBE = build_subscription_list()
#     if not INSTRUMENTS_TO_SUBSCRIBE:
#         r.set(settings.REDIS_STATUS_DATA_ENGINE, 'FATAL_ERROR_NO_INSTRUMENTS')
#         return

#     # Start Threads
#     t1 = threading.Thread(target=run_market_feed_worker, args=(dhan_context,), daemon=True)
#     t2 = threading.Thread(target=run_order_update_worker, args=(dhan_context,), daemon=True)
#     t1.start()
#     t2.start()

#     r.set(settings.REDIS_STATUS_DATA_ENGINE, 'RUNNING')
#     print("Data Worker: Aggregating Candles & Streaming Orders.")
    
#     t1.join()
#     t2.join()

# if __name__ == '__main__':
#     main_worker_loop()

# dhan_workers.py - Runs on the Worker Dyno
import redis
import json
import os
import time
import threading
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

# --- Django Environment Setup ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'algotrader.settings')

import django
django.setup()
from django.conf import settings

# --- 1. ROBUST REAL IMPORT ---
try:
    # Try importing from top level (v2.1+ standard)
    from dhanhq import DhanContext, dhanhq, MarketFeed, OrderUpdate
except ImportError:
    try:
        # Try submodule imports (Common in v2.0.x)
        from dhanhq import DhanContext, dhanhq
        from dhanhq.marketfeed import MarketFeed
        from dhanhq.order_update import OrderUpdate
    except ImportError as e:
        print(f"CRITICAL ERROR: Could not import DhanHQ library. {e}")
        sys.exit(1)

# --- 2. CONSTANT DISCOVERY (Fixes Invalid Request Mode) ---
try:
    # Try to get constants from the class
    EXCH_NSE = getattr(MarketFeed, 'NSE', 1)
    
    # Try to find the 'Full' or 'Quote' mode constant
    # The library might name it Full, FULL, Quote, etc.
    if hasattr(MarketFeed, 'Full'):
        MODE_FULL = MarketFeed.Full
    elif hasattr(MarketFeed, 'FULL'):
        MODE_FULL = MarketFeed.FULL
    elif hasattr(MarketFeed, 'Quote'):
        MODE_FULL = MarketFeed.Quote # Fallback if Full not found
    else:
        # Hard fallback for v2 (usually 17 for Quote/Full)
        MODE_FULL = 17 
        
    print(f"[{datetime.now()}] LIB DETECTED: NSE={EXCH_NSE}, MODE={MODE_FULL}")

except Exception as e:
    print(f"Error detecting constants: {e}")
    EXCH_NSE = 1
    MODE_FULL = 17 

# --- Configuration ---
r = redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)
IST = settings.IST

# Reverse Map for Symbol Lookup (Needed for tagging candles)
SECURITY_ID_TO_SYMBOL = {str(v): k for k, v in settings.SECURITY_ID_MAP.items()}

INSTRUMENTS_TO_SUBSCRIBE: List[tuple] = []

# --- 3. CANDLE AGGREGATOR CLASS ---
class LiveCandleAggregator:
    """
    Aggregates live ticks into 1-minute candles and pushes them to 
    Redis Streams (for Algo) and Redis Lists (for History).
    """
    def __init__(self, redis_conn):
        self.r = redis_conn
        self.aggregators: Dict[str, Dict[str, Any]] = {} 
        self.last_ltp: Dict[str, float] = {}

    def process_tick(self, tick_data: Dict[str, Any]):
        # Extract Data
        security_id = str(tick_data.get('securityId', ''))
        ltp = float(tick_data.get('LTP') or tick_data.get('last_price') or tick_data.get('lp') or 0.0)
        
        # Timestamp logic
        ts_raw = tick_data.get('exchange_time') or tick_data.get('LTT')
        if ts_raw:
            try:
                if int(ts_raw) > 10000000000: timestamp = datetime.fromtimestamp(int(ts_raw) / 1000, tz=IST)
                else: timestamp = datetime.fromtimestamp(int(ts_raw), tz=IST)
            except: timestamp = datetime.now(IST)
        else: timestamp = datetime.now(IST)

        if not security_id or ltp == 0: return

        # Update Live Snapshot (For Dashboard/Monitor)
        self.last_ltp[security_id] = ltp
        
        # Candle Construction
        candle_ts = timestamp.replace(second=0, microsecond=0)
        
        if security_id in self.aggregators:
            current = self.aggregators[security_id]
            if candle_ts > current['ts']:
                # Minute changed: Finalize old candle
                self.finalize_candle(current)
                # Start new candle
                self.aggregators[security_id] = self._new_candle(security_id, candle_ts, ltp)
            else:
                # Update current
                current['high'] = max(current['high'], ltp)
                current['low'] = min(current['low'], ltp)
                current['close'] = ltp
        else:
            self.aggregators[security_id] = self._new_candle(security_id, candle_ts, ltp)

    def _new_candle(self, sec_id, ts, price):
        return {'security_id': sec_id, 'ts': ts, 'open': price, 'high': price, 'low': price, 'close': price}

    def finalize_candle(self, candle):
        """
        1. Stores candle in Redis List (History).
        2. Pushes candle to Redis Stream (Real-time Algo).
        """
        symbol = SECURITY_ID_TO_SYMBOL.get(candle['security_id'])
        if not symbol: return

        # Format Payload
        payload = {
            'symbol': symbol,
            'security_id': candle['security_id'],
            'ts': candle['ts'].isoformat(),
            'open': candle['open'],
            'high': candle['high'],
            'low': candle['low'],
            'close': candle['close']
        }
        payload_json = json.dumps(payload)

        # A. HISTORY: Push to Redis List (Right Push)
        history_key = f"{settings.HISTORY_KEY_PREFIX}:{candle['security_id']}:1m"
        try:
            self.r.rpush(history_key, payload_json)
            # Keep only 1 day of history (400 mins)
            self.r.ltrim(history_key, -400, -1) 
        except Exception: pass

        # B. STREAM: Push to Algo Stream
        try:
            self.r.xadd(settings.REDIS_STREAM_CANDLES, {'p': payload_json})
        except Exception as e:
            print(f"Stream Error: {e}")

# --- 4. WORKER LOGIC ---

# Global Aggregator Instance
aggregator = LiveCandleAggregator(r)

def get_dhan_context(client_id: str, token: str) -> Optional[DhanContext]:
    if not token: return None
    try:
        return DhanContext(client_id, token)
    except: return None

def build_subscription_list() -> List[tuple]:
    subscription_list = []
    try:
        instrument_map = settings.SECURITY_ID_MAP
        for symbol, security_id in instrument_map.items():
            subscription_list.append((
                EXCH_NSE, 
                str(security_id), 
                MODE_FULL # Using the discovered constant
            ))
        print(f"[{datetime.now()}] Configured {len(subscription_list)} instruments from Settings.")
        return subscription_list
    except Exception as e:
        print(f"[{datetime.now()}] ERROR building subscription list: {e}")
        return []

def on_market_feed_message(instance, message):
    """Feeds the Aggregator instead of raw streaming."""
    try:
        if message:
            # 1. Process locally for aggregation (The Primary Job)
            aggregator.process_tick(message)
            
            # 2. Also push raw ticks to market stream (Optional, for debugging/UI LTP)
            # We use a short limit to keep redis light
            r.xadd(
                settings.REDIS_STREAM_MARKET, 
                {'p': json.dumps(message)}, 
                maxlen=5000, 
                approximate=True
            )
    except Exception:
        pass

def run_market_feed_worker(dhan_context):
    while True:
        try:
            print(f"[{datetime.now()}] MarketFeed: Connecting with Mode {MODE_FULL}...")
            client = MarketFeed(dhan_context, INSTRUMENTS_TO_SUBSCRIBE, version="v2")
            client.on_message = on_market_feed_message
            client.run_forever()
        except Exception as e:
            print(f"MarketFeed Error: {e}. Retry in 5s...")
            time.sleep(5)

def on_order_update_message(order_data):
    """Pushes Order Updates to Stream."""
    try:
        payload = order_data.get('Data', order_data)
        if payload:
            r.xadd(settings.REDIS_STREAM_ORDERS, {'p': json.dumps(payload)})
            print(f"[{datetime.now()}] Order Update pushed.")
    except Exception as e:
        print(f"Order Stream Error: {e}")

def run_order_update_worker(dhan_context):
    while True:
        try:
            print(f"[{datetime.now()}] OrderUpdate: Connecting...")
            client = OrderUpdate(dhan_context)
            client.on_update = on_order_update_message
            client.connect_to_dhan_websocket_sync()
        except Exception as e:
            print(f"OrderUpdate Error: {e}. Retry in 5s...")
            time.sleep(5)

# --- MAIN ---

def main_worker_loop():
    global INSTRUMENTS_TO_SUBSCRIBE
    r.set(settings.REDIS_STATUS_DATA_ENGINE, 'STARTING')
    
    token = r.get(settings.REDIS_DHAN_TOKEN_KEY)
    while not token:
        print("Waiting for Access Token in Redis...")
        time.sleep(5)
        token = r.get(settings.REDIS_DHAN_TOKEN_KEY)

    dhan_context = get_dhan_context(settings.DHAN_CLIENT_ID, token)
    if not dhan_context:
        r.set(settings.REDIS_STATUS_DATA_ENGINE, 'FATAL_ERROR_CONTEXT')
        return

    INSTRUMENTS_TO_SUBSCRIBE = build_subscription_list()
    if not INSTRUMENTS_TO_SUBSCRIBE:
        r.set(settings.REDIS_STATUS_DATA_ENGINE, 'FATAL_ERROR_NO_INSTRUMENTS')
        return

    t1 = threading.Thread(target=run_market_feed_worker, args=(dhan_context,), daemon=True)
    t2 = threading.Thread(target=run_order_update_worker, args=(dhan_context,), daemon=True)

    t1.start()
    t2.start()

    r.set(settings.REDIS_STATUS_DATA_ENGINE, 'RUNNING')
    print("Data Worker: Aggregating Candles & Streaming Orders (LIVE).")
    
    t1.join()
    t2.join()

if __name__ == '__main__':
    main_worker_loop()