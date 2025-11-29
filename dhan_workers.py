# dhan_workers.py - Runs on the Worker Dyno
import redis
import json
import os
import time
import threading
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project root to sys.path to allow importing settings
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'algotrader.settings')

import django
django.setup()
from django.conf import settings

# --- Robust Import ---
try:
    from dhanhq import DhanContext, dhanhq, MarketFeed, OrderUpdate
except ImportError:
    class DhanContext:
        def __init__(self, client_id, access_token): pass
    MarketFeed = lambda: None
    OrderUpdate = lambda: None

# --- Configuration ---
r = redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)

INSTRUMENTS_TO_SUBSCRIBE: List[tuple] = []

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
            subscription_list.append((1, str(security_id), MarketFeed.Full))
        print(f"[{datetime.now()}] Configured {len(subscription_list)} instruments from Settings.")
        return subscription_list
    except Exception as e:
        print(f"[{datetime.now()}] ERROR building subscription list: {e}")
        return []

# --- STREAM PRODUCERS (XADD) ---

def on_market_feed_message(instance, message):
    """
    Pushes market data to Redis Stream.
    We use maxlen=20000 to keep only recent history and prevent Redis memory overflow.
    """
    try:
        # XADD key ID field string-value ...
        # We store the JSON payload under the field 'p' (payload)
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
            print(f"[{datetime.now()}] MarketFeed: Connecting...")
            market_client = MarketFeed(dhan_context, INSTRUMENTS_TO_SUBSCRIBE, version="v2")
            market_client.on_message = on_market_feed_message
            market_client.run_forever()
        except Exception as e:
            print(f"[{datetime.now()}] MarketFeed DOWN: {e}. Retry in 5s...")
            time.sleep(5)

def on_order_update_message(order_data):
    """
    Pushes Order Updates to Redis Stream.
    NO maxlen here. Order updates are critical and must be persisted until consumed.
    """
    try:
        r.xadd(
            settings.REDIS_STREAM_ORDERS, 
            {'p': json.dumps(order_data)}
        )
        print(f"[{datetime.now()}] Order Update pushed to Stream.")
    except Exception as e:
        print(f"Stream Write Error (Order): {e}")

def run_order_update_worker(dhan_context):
    while True:
        try:
            print(f"[{datetime.now()}] OrderUpdate: Connecting...")
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
    
    INSTRUMENTS_TO_SUBSCRIBE = build_subscription_list()
    if not INSTRUMENTS_TO_SUBSCRIBE:
        r.set(settings.REDIS_STATUS_DATA_ENGINE, 'FATAL_ERROR_NO_INSTRUMENTS')
        return

    # Start Threads
    market_thread = threading.Thread(target=run_market_feed_worker, args=(dhan_context,), daemon=True)
    order_thread = threading.Thread(target=run_order_update_worker, args=(dhan_context,), daemon=True)

    market_thread.start()
    order_thread.start()

    r.set(settings.REDIS_STATUS_DATA_ENGINE, 'RUNNING')
    print("Data Engine Running (Streaming Mode).")
    
    market_thread.join()
    order_thread.join()

if __name__ == '__main__':
    main_worker_loop()