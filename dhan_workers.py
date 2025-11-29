# # dhan_workers.py - Runs on the Worker Dyno
# import redis
# import json
# import os
# import time
# import threading
# import sys
# from datetime import datetime
# from typing import Dict, List, Any, Optional

# # Add project root to sys.path to allow importing settings
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'algotrader.settings')

# import django
# django.setup()
# from django.conf import settings

# # --- ROBUST IMPORT LOGIC ---
# DhanContext = None
# dhanhq = None
# MarketFeed = None
# OrderUpdate = None

# try:
#     # 1. Try importing everything from top level (v2.1+ standard)
#     from dhanhq import DhanContext, dhanhq, MarketFeed, OrderUpdate
# except ImportError:
#     try:
#         # 2. Try submodule imports (Common in v2.0.x)
#         from dhanhq import DhanContext, dhanhq
#         from dhanhq.marketfeed import MarketFeed
#         from dhanhq.order_update import OrderUpdate
#     except ImportError:
#         print("CRITICAL: Failed to import DhanHQ library components. Using Fallback Mocks.")
        
#         # 3. Define Safe Fallbacks (Prevents 'AttributeError' crash)
#         class DhanContext:
#             def __init__(self, client_id, access_token): pass
            
#         class MarketFeed:
#             # Define constants expected by the code
#             Ticker = 1
#             Quote = 2
#             Depth = 3
#             Full = 4 # <--- This fixes the 'no attribute Full' error
            
#             def __init__(self, context, instruments, version): 
#                 self.context = context
#                 self.instruments = instruments
#             def on_message(self, msg): pass
#             def run_forever(self): 
#                 print("Mock MarketFeed running (no data)...")
#                 time.sleep(10)
                
#         class OrderUpdate:
#             def __init__(self, context): pass
#             def on_update(self, msg): pass
#             def connect_to_dhan_websocket_sync(self):
#                 print("Mock OrderUpdate running (no data)...")
#                 time.sleep(10)

# # --- Configuration ---
# # Use ssl_cert_reqs=None for Heroku Redis
# r = redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)

# INSTRUMENTS_TO_SUBSCRIBE: List[tuple] = []

# def get_dhan_context(client_id: str, token: str) -> Optional[DhanContext]:
#     if not token: return None
#     try:
#         return DhanContext(client_id, token)
#     except: return None

# def build_subscription_list() -> List[tuple]:
#     """
#     Constructs the subscription list directly from settings.SECURITY_ID_MAP.
#     """
#     subscription_list = []
#     try:
#         # Load map from Django settings
#         instrument_map = settings.SECURITY_ID_MAP
        
#         for symbol, security_id in instrument_map.items():
#             # Dhan MarketFeed expects: (ExchangeSegment, SecurityID, Mode)
#             # We assume NSE_EQ (1) for all symbols in the map.
#             # We use MarketFeed.Full (Constant value 4)
#             subscription_list.append((
#                 1, 
#                 str(security_id), 
#                 MarketFeed.Full
#             ))
            
#         print(f"[{datetime.now()}] Configured {len(subscription_list)} instruments from Settings.")
#         return subscription_list

#     except Exception as e:
#         print(f"[{datetime.now()}] ERROR building subscription list: {e}")
#         return []

# # --- STREAM PRODUCERS (XADD) ---

# def on_market_feed_message(instance, message):
#     """Pushes market data to Redis Stream."""
#     try:
#         # 'p' key holds the JSON payload
#         r.xadd(
#             settings.REDIS_STREAM_MARKET, 
#             {'p': json.dumps(message)}, 
#             maxlen=20000, 
#             approximate=True
#         )
#     except Exception as e:
#         print(f"Stream Write Error (Market): {e}")

# def run_market_feed_worker(dhan_context):
#     while True:
#         try:
#             print(f"[{datetime.now()}] MarketFeed: Connecting...")
#             # Initialize with context, instruments list, and version
#             market_client = MarketFeed(dhan_context, INSTRUMENTS_TO_SUBSCRIBE, version="v2")
#             market_client.on_message = on_market_feed_message
#             market_client.run_forever()
#         except Exception as e:
#             print(f"[{datetime.now()}] MarketFeed DOWN: {e}. Retry in 5s...")
#             time.sleep(5)

# def on_order_update_message(order_data):
#     """Pushes Order Updates to Redis Stream."""
#     try:
#         r.xadd(
#             settings.REDIS_STREAM_ORDERS, 
#             {'p': json.dumps(order_data)}
#         )
#         print(f"[{datetime.now()}] Order Update pushed to Stream.")
#     except Exception as e:
#         print(f"Stream Write Error (Order): {e}")

# def run_order_update_worker(dhan_context):
#     while True:
#         try:
#             print(f"[{datetime.now()}] OrderUpdate: Connecting...")
#             order_client = OrderUpdate(dhan_context)
#             order_client.on_update = on_order_update_message
#             order_client.connect_to_dhan_websocket_sync()
#         except Exception as e:
#             print(f"[{datetime.now()}] OrderUpdate DOWN: {e}. Retry in 5s...")
#             time.sleep(5)

# # --- Main ---

# def main_worker_loop():
#     global INSTRUMENTS_TO_SUBSCRIBE
#     r.set(settings.REDIS_STATUS_DATA_ENGINE, 'STARTING')
    
#     token = r.get(settings.REDIS_DHAN_TOKEN_KEY)
#     while not token:
#         print("Waiting for Access Token in Redis...")
#         time.sleep(5)
#         token = r.get(settings.REDIS_DHAN_TOKEN_KEY)

#     dhan_context = get_dhan_context(settings.DHAN_CLIENT_ID, token)
    
#     # Build list (This triggered the previous error)
#     INSTRUMENTS_TO_SUBSCRIBE = build_subscription_list()
    
#     if not INSTRUMENTS_TO_SUBSCRIBE:
#         r.set(settings.REDIS_STATUS_DATA_ENGINE, 'FATAL_ERROR_NO_INSTRUMENTS')
#         print("No instruments found in settings map.")
#         return

#     # Start Threads
#     market_thread = threading.Thread(target=run_market_feed_worker, args=(dhan_context,), daemon=True)
#     order_thread = threading.Thread(target=run_order_update_worker, args=(dhan_context,), daemon=True)

#     market_thread.start()
#     order_thread.start()

#     r.set(settings.REDIS_STATUS_DATA_ENGINE, 'RUNNING')
#     print("Data Engine Running (Stream Mode).")
    
#     market_thread.join()
#     order_thread.join()

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
# Add project root to sys.path to allow importing settings
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'algotrader.settings')

import django
django.setup()
from django.conf import settings

# --- ROBUST REAL IMPORT (NO MOCKS) ---
try:
    # 1. Try Standard v2 Import (Recommended in docs)
    from dhanhq import DhanContext, dhanhq, MarketFeed, OrderUpdate
except ImportError:
    try:
        # 2. Try Submodule Import (Common in some v2.x installations)
        from dhanhq import DhanContext, dhanhq
        from dhanhq.marketfeed import MarketFeed
        from dhanhq.order_update import OrderUpdate
    except ImportError as e:
        print(f"CRITICAL ERROR: Could not import DhanHQ library. Error: {e}")
        # Crash immediately so you know the library is missing/broken
        sys.exit(1)

# --- Configuration ---
# Use ssl_cert_reqs=None for Heroku Redis
r = redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)

INSTRUMENTS_TO_SUBSCRIBE: List[tuple] = []

def get_dhan_context(client_id: str, token: str) -> Optional[DhanContext]:
    if not token: return None
    try:
        return DhanContext(client_id, token)
    except Exception as e:
        print(f"Error creating DhanContext: {e}")
        return None

def build_subscription_list() -> List[tuple]:
    """
    Constructs the subscription list directly from settings.SECURITY_ID_MAP.
    """
    subscription_list = []
    try:
        # Load map from Django settings
        instrument_map = settings.SECURITY_ID_MAP
        
        # Determine constants for subscription
        # Use class attributes if available, otherwise fallback to standard Integers
        # NSE Equity = 1
        # Full Packet = 4
        try:
            EXCH_NSE = MarketFeed.NSE
            MODE_FULL = MarketFeed.Full
        except AttributeError:
            # If the library version doesn't have these constants exposed, use hardcoded values
            EXCH_NSE = 1
            MODE_FULL = 4

        for symbol, security_id in instrument_map.items():
            # Structure: (ExchangeSegment, SecurityID, Mode)
            subscription_list.append((
                EXCH_NSE, 
                str(security_id), 
                MODE_FULL
            ))
            
        print(f"[{datetime.now()}] Configured {len(subscription_list)} instruments from Settings.")
        return subscription_list

    except Exception as e:
        print(f"[{datetime.now()}] ERROR building subscription list: {e}")
        return []

# --- STREAM PRODUCERS (XADD) ---

def on_market_feed_message(instance, message):
    """
    Callback for Real-Time Market Data.
    Pushes data to Redis Stream 'stream:dhan:market'.
    """
    try:
        if message:
            # 'p' key holds the JSON payload
            r.xadd(
                settings.REDIS_STREAM_MARKET, 
                {'p': json.dumps(message)}, 
                maxlen=20000, # Keep buffer manageable
                approximate=True
            )
    except Exception as e:
        print(f"Stream Write Error (Market): {e}")

def run_market_feed_worker(dhan_context):
    """Main loop for Market Data WebSocket."""
    while True:
        try:
            print(f"[{datetime.now()}] MarketFeed: Connecting to LIVE Dhan WebSocket...")
            
            # Initialize MarketFeed with Context, Instruments, and Version 'v2'
            market_client = MarketFeed(dhan_context, INSTRUMENTS_TO_SUBSCRIBE, version="v2")
            
            # Assign callback
            market_client.on_message = on_market_feed_message
            
            # Blocking call - this runs forever receiving data
            market_client.run_forever()
            
        except Exception as e:
            print(f"[{datetime.now()}] MarketFeed Connection Dropped: {e}. Reconnecting in 5s...")
            time.sleep(5)

def on_order_update_message(order_data):
    """
    Callback for Real-Time Order Updates.
    Pushes data to Redis Stream 'stream:dhan:orders'.
    """
    try:
        # Dhan sometimes wraps data in a 'Data' key
        payload = order_data.get('Data', order_data)
        
        if payload:
            r.xadd(
                settings.REDIS_STREAM_ORDERS, 
                {'p': json.dumps(payload)}
            )
            print(f"[{datetime.now()}] LIVE ORDER UPDATE received and pushed to stream.")
    except Exception as e:
        print(f"Stream Write Error (Order): {e}")

def run_order_update_worker(dhan_context):
    """Main loop for Order Update WebSocket."""
    while True:
        try:
            print(f"[{datetime.now()}] OrderUpdate: Connecting to LIVE Dhan WebSocket...")
            
            order_client = OrderUpdate(dhan_context)
            order_client.on_update = on_order_update_message
            
            # Blocking call
            order_client.connect_to_dhan_websocket_sync()
            
        except Exception as e:
            print(f"[{datetime.now()}] OrderUpdate Connection Dropped: {e}. Reconnecting in 5s...")
            time.sleep(5)

# --- Main Entry Point ---

def main_worker_loop():
    global INSTRUMENTS_TO_SUBSCRIBE
    r.set(settings.REDIS_STATUS_DATA_ENGINE, 'STARTING')
    
    # 1. Wait for Token
    token = r.get(settings.REDIS_DHAN_TOKEN_KEY)
    while not token:
        print("Waiting for Access Token in Redis (Paste in Dashboard)...")
        time.sleep(5)
        token = r.get(settings.REDIS_DHAN_TOKEN_KEY)

    # 2. Initialize Context
    dhan_context = get_dhan_context(settings.DHAN_CLIENT_ID, token)
    if not dhan_context:
        print("Failed to create Dhan Context. Check Client ID.")
        return

    # 3. Build Subscription List
    INSTRUMENTS_TO_SUBSCRIBE = build_subscription_list()
    if not INSTRUMENTS_TO_SUBSCRIBE:
        r.set(settings.REDIS_STATUS_DATA_ENGINE, 'FATAL_ERROR_NO_INSTRUMENTS')
        print("No instruments found in settings map.")
        return

    # 4. Start Threads
    # We use daemon=True so if the main program exits, threads close too.
    market_thread = threading.Thread(target=run_market_feed_worker, args=(dhan_context,), daemon=True)
    order_thread = threading.Thread(target=run_order_update_worker, args=(dhan_context,), daemon=True)

    market_thread.start()
    order_thread.start()

    r.set(settings.REDIS_STATUS_DATA_ENGINE, 'RUNNING')
    print("Data Engine Running (REAL LIVE MODE).")
    
    # Keep main thread alive
    market_thread.join()
    order_thread.join()

if __name__ == '__main__':
    main_worker_loop()