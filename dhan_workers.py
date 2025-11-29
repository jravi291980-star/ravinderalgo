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

# --- ROBUST REAL IMPORT (FIXED) ---
# We try specific submodule paths which are more reliable than top-level imports
DhanContext = None
dhanhq = None
MarketFeed = None
OrderUpdate = None

try:
    # Attempt 1: Top-level import (Standard Documentation)
    from dhanhq import DhanContext, dhanhq, MarketFeed, OrderUpdate
    print("Imported DhanHQ from top-level.")
except ImportError as e1:
    print(f"Top-level import failed ({e1}). Trying submodules...")
    try:
        # Attempt 2: Explicit Submodules (Fix for 'cannot import name' errors)
        # The core classes often live in 'dhanhq.dhanhq' or similar paths
        from dhanhq.dhanhq import DhanContext, dhanhq
        from dhanhq.marketfeed import MarketFeed
        from dhanhq.order_update import OrderUpdate
        print("Imported DhanHQ from submodules.")
    except ImportError as e2:
        print(f"CRITICAL: Failed to import DhanHQ library. Error 1: {e1}, Error 2: {e2}")
        # inspect what IS available to help debugging next time
        import dhanhq as _d
        print(f"dhanhq module contents: {dir(_d)}")
        sys.exit(1)

# --- Configuration ---
r = redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)

INSTRUMENTS_TO_SUBSCRIBE: List[tuple] = []

def get_dhan_context(client_id: str, token: str) -> Optional[Any]:
    if not token: return None
    try:
        return DhanContext(client_id, token)
    except Exception as e:
        print(f"Error creating context: {e}")
        return None

def build_subscription_list() -> List[tuple]:
    """
    Constructs the subscription list directly from settings.SECURITY_ID_MAP.
    """
    subscription_list = []
    try:
        # Load map from Django settings
        instrument_map = settings.SECURITY_ID_MAP
        
        for symbol, security_id in instrument_map.items():
            # Dhan MarketFeed expects: (ExchangeSegment, SecurityID, Mode)
            # Hardcoding constants to avoid AttributeError if class constants are missing
            # 1 = NSE Equity
            # 4 = Full Packet
            subscription_list.append((
                1, 
                str(security_id), 
                4
            ))
            
        print(f"[{datetime.now()}] Configured {len(subscription_list)} instruments from Settings.")
        return subscription_list

    except Exception as e:
        print(f"[{datetime.now()}] ERROR building subscription list: {e}")
        return []

# --- STREAM PRODUCERS (XADD) ---

def on_market_feed_message(instance, message):
    """Pushes market data to Redis Stream."""
    try:
        if message:
            r.xadd(
                settings.REDIS_STREAM_MARKET, 
                {'p': json.dumps(message)}, 
                maxlen=20000, 
                approximate=True
            )
    except Exception as e:
        print(f"Stream Write Error (Market): {e}")

def run_market_feed_worker(dhan_context):
    while True:
        try:
            print(f"[{datetime.now()}] MarketFeed: Connecting to LIVE Dhan WebSocket...")
            market_client = MarketFeed(dhan_context, INSTRUMENTS_TO_SUBSCRIBE, version="v2")
            market_client.on_message = on_market_feed_message
            market_client.run_forever()
        except Exception as e:
            print(f"[{datetime.now()}] MarketFeed DOWN: {e}. Retry in 5s...")
            time.sleep(5)

def on_order_update_message(order_data):
    """Pushes Order Updates to Redis Stream."""
    try:
        payload = order_data.get('Data', order_data)
        if payload:
            r.xadd(
                settings.REDIS_STREAM_ORDERS, 
                {'p': json.dumps(payload)}
            )
            print(f"[{datetime.now()}] Order Update pushed to Stream.")
    except Exception as e:
        print(f"Stream Write Error (Order): {e}")

def run_order_update_worker(dhan_context):
    while True:
        try:
            print(f"[{datetime.now()}] OrderUpdate: Connecting to LIVE Dhan WebSocket...")
            order_client = OrderUpdate(dhan_context)
            order_client.on_update = on_order_update_message
            order_client.connect_to_dhan_websocket_sync()
        except Exception as e:
            print(f"[{datetime.now()}] OrderUpdate DOWN: {e}. Retry in 5s...")
            time.sleep(5)

# --- Main ---

def main_worker_loop():
    global INSTRUMENTS_TO_SUBSCRIBE
    r.set(settings.REDIS_STATUS_DATA_ENGINE, 'STARTING')
    
    token = r.get(settings.REDIS_DHAN_TOKEN_KEY)
    while not token:
        print("Waiting for Access Token in Redis...")
        time.sleep(5)
        token = r.get(settings.REDIS_DHAN_TOKEN_KEY)

    dhan_context = get_dhan_context(settings.DHAN_CLIENT_ID, token)
    
    # Build list
    INSTRUMENTS_TO_SUBSCRIBE = build_subscription_list()
    
    if not INSTRUMENTS_TO_SUBSCRIBE:
        r.set(settings.REDIS_STATUS_DATA_ENGINE, 'FATAL_ERROR_NO_INSTRUMENTS')
        print("No instruments found in settings map.")
        return

    # Start Threads
    market_thread = threading.Thread(target=run_market_feed_worker, args=(dhan_context,), daemon=True)
    order_thread = threading.Thread(target=run_order_update_worker, args=(dhan_context,), daemon=True)

    market_thread.start()
    order_thread.start()

    r.set(settings.REDIS_STATUS_DATA_ENGINE, 'RUNNING')
    print("Data Engine Running (REAL LIVE MODE).")
    
    market_thread.join()
    order_thread.join()

if __name__ == '__main__':
    main_worker_loop()