# algo_engine.py - Runs on an Algo Dyno
import redis
import json
import os
import time
import sys
from datetime import datetime, timedelta
from math import floor
from typing import Dict, Any, Optional

# --- Django Environment Setup ---
# This allows the standalone script to access Django models and settings
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'algotrader.settings')

import django
django.setup()

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from dashboard.models import CashBreakoutTrade, StrategySettings

# --- Robust Dhan SDK Import ---
try:
    from dhanhq import DhanContext, dhanhq
except ImportError:
    # Fallback placeholders to prevent startup crash if lib has issues
    # The loop will simply fail to trade if this happens, rather than crashing entirely
    class DhanContext:
        def __init__(self, c, t): pass
    dhanhq = lambda ctx: None

# --- Configuration & Constants ---
# Using ssl_cert_reqs=None is critical for Heroku Redis connection stability
r = redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)
IST = settings.IST

# --- Reverse Map Construction ---
# We invert the settings map {Symbol: ID} -> {ID: Symbol} for fast lookup 
# when processing incoming ticks (which only have IDs).
SECURITY_ID_TO_SYMBOL = {str(v): k for k, v in settings.SECURITY_ID_MAP.items()}

# --- Global State ---
DHAN_CLIENT = None

# --- STREAM SETUP HELPER ---
def setup_consumer_groups():
    """Ensures consumer groups exist for all streams."""
    streams = [settings.REDIS_STREAM_MARKET, settings.REDIS_STREAM_ORDERS, settings.REDIS_STREAM_CONTROL]
    for stream in streams:
        try:
            # Create group starting from the end ($) so we only process new messages on startup
            # mkstream=True creates the stream if it doesn't exist yet
            r.xgroup_create(stream, settings.REDIS_CONSUMER_GROUP, id='$', mkstream=True)
            print(f"Created/Verified consumer group for {stream}")
        except redis.exceptions.ResponseError as e:
            # "BUSYGROUP Consumer Group name already exists" is expected and fine
            if "BUSYGROUP" not in str(e):
                print(f"Error creating group for {stream}: {e}")

def get_dhan_client(token: str) -> Optional[object]:
    """Initializes the Dhan REST client using the token."""
    try:
        if not token: return None
        return dhanhq(DhanContext(settings.DHAN_CLIENT_ID, token))
    except Exception as e:
        print(f"Client Init Error: {e}")
        return None

# --- Component 1: Candle Aggregator ---

class StrategyCandleAggregator:
    """
    Ingests ticks, builds 1-minute candles, and executes the strategy logic directly.
    """
    def __init__(self, redis_conn):
        self.r = redis_conn
        self.aggregators: Dict[str, Dict[str, Any]] = {} # security_id -> candle_data
        self.last_ltp: Dict[str, float] = {}
        # This function pointer will be set by the main loop to link Aggregator -> Strategy
        self.eject_candle_callback = None 

    def process_tick(self, tick_data: Dict[str, Any]):
        """
        Processes a single tick. Dhan ticks structure varies (Ticker vs Full).
        We handle the common fields.
        """
        # Extract Security ID and LTP robustly
        security_id = str(tick_data.get('securityId', ''))
        
        # LTP might be 'LTP', 'last_price', or 'lp' depending on packet type
        ltp = float(tick_data.get('LTP') or tick_data.get('last_price') or tick_data.get('lp') or 0.0)
        
        # Timestamp: 'exchange_time', 'ltt', or current time if missing
        ts_raw = tick_data.get('exchange_time') or tick_data.get('LTT')
        if ts_raw:
            try:
                # Assuming epoch seconds or milliseconds
                if int(ts_raw) > 10000000000: # Milliseconds
                    timestamp = datetime.fromtimestamp(int(ts_raw) / 1000, tz=IST)
                else:
                    timestamp = datetime.fromtimestamp(int(ts_raw), tz=IST)
            except:
                timestamp = datetime.now(IST)
        else:
            timestamp = datetime.now(IST)

        if not security_id or ltp == 0:
            return

        # 1. Update Live Snapshot (Used by strategy monitor/dashboard)
        self.last_ltp[security_id] = ltp
        # Optimization: You might persist this to Redis key LIVE_OHLC_KEY periodically here
        
        # 2. Candle Logic
        candle_ts = timestamp.replace(second=0, microsecond=0)
        
        if security_id in self.aggregators:
            current_candle = self.aggregators[security_id]
            
            # Check if we moved to a new minute
            if candle_ts > current_candle['ts']:
                # EJECT the finished candle to the strategy
                self.eject_candle(current_candle)
                # Start new candle
                self.aggregators[security_id] = self._new_candle(security_id, candle_ts, ltp)
            else:
                # Update existing candle
                current_candle['high'] = max(current_candle['high'], ltp)
                current_candle['low'] = min(current_candle['low'], ltp)
                current_candle['close'] = ltp
        else:
            # First tick for this symbol
            self.aggregators[security_id] = self._new_candle(security_id, candle_ts, ltp)

    def _new_candle(self, sec_id, ts, price):
        return {
            'security_id': sec_id,
            'ts': ts,
            'open': price,
            'high': price,
            'low': price,
            'close': price
        }

    def eject_candle(self, candle):
        """Passes the completed candle to the strategy callback."""
        if self.eject_candle_callback:
            # Resolve Symbol using the Reverse Map
            symbol = SECURITY_ID_TO_SYMBOL.get(candle['security_id'])
            if symbol:
                candle['symbol'] = symbol
                # Direct In-Memory transfer for lowest latency
                self.eject_candle_callback(candle)


# --- Component 2: Cash Breakout Strategy ---

class CashBreakoutStrategy:
    """
    Core Logic: PDH Breakout, Entry/Exit Execution, Risk Management.
    """
    def __init__(self):
        # Load initial settings from DB
        self.settings = StrategySettings.objects.first()
        if not self.settings:
            print("WARNING: StrategySettings not found. Strategy disabled.")
            self.running = False
        else:
            self.running = self.settings.is_enabled
            
        self.active_trades = {} # In-memory tracker for speed
        self.load_trades()
        
        # Load global counters for limits
        today_str = datetime.now(IST).strftime('%Y-%m-%d')
        self.trade_count_key = f"trade_count:{today_str}"
        self.daily_pnl_key = f"daily_pnl:{today_str}"

    def load_trades(self):
        """Syncs in-memory state with Database (on startup or refresh)."""
        open_trades = CashBreakoutTrade.objects.filter(
            status__in=['OPEN', 'PENDING_ENTRY', 'PENDING_EXIT']
        )
        self.active_trades = {t.symbol: t for t in open_trades}
        print(f"Strategy: Loaded {len(self.active_trades)} active trades.")

    def get_prev_day_high(self, symbol):
        """Fetches T-1 High from Redis cache (populated by management command)."""
        try:
            raw = r.hget(settings.PREV_DAY_HASH, symbol)
            if raw:
                data = json.loads(raw)
                return float(data.get('high', 0))
        except: pass
        return None

    def process_candle(self, candle):
        """Called when a 1-minute candle is completed."""
        if not self.running or not DHAN_CLIENT: return
        
        symbol = candle['symbol']
        
        # 1. Skip if already active
        if symbol in self.active_trades: return
        
        # 2. Get PDH
        pdh = self.get_prev_day_high(symbol)
        if not pdh: return

        # 3. Breakout Logic
        open_p = candle['open']
        close_p = candle['close']
        high_p = candle['high']
        low_p = candle['low']
        
        # Condition A: Bullish Candle closing above Open
        if close_p <= open_p: return
        # Condition B: Opened BELOW PDH, Closed ABOVE PDH (Clean Breakout)
        if not (open_p < pdh < close_p): return
        
        # 4. Parameters & Limits
        entry_price = high_p * (1.0 + settings.ENTRY_OFFSET_PCT)
        stop_loss = low_p * (1.0 - settings.STOP_OFFSET_PCT)
        
        risk_per_share = entry_price - stop_loss
        if risk_per_share <= 0: return
        
        # Target R:R
        target = entry_price + (settings.RISK_MULTIPLIER * risk_per_share)
        
        # Calculate Qty based on Risk Amount
        qty = floor(self.settings.per_trade_sl_amount / risk_per_share)
        if qty <= 0: return

        # Check Global Limits (Atomic Redis Increment)
        current_count = r.incr(self.trade_count_key)
        if current_count > self.settings.max_total_trades:
            r.decr(self.trade_count_key) # Revert count if limit hit
            return
            
        # Check per-stock limit (simplified check against DB history omitted for speed, relies on active_trades)

        # 5. Place Entry Order (SL-M)
        try:
            print(f"SIGNAL: {symbol} Breakout. Placing Buy Order {qty} @ {entry_price:.2f}")
            response = DHAN_CLIENT.place_order(
                security_id=candle['security_id'],
                exchange_segment=DHAN_CLIENT.NSE,
                transaction_type=DHAN_CLIENT.BUY,
                quantity=qty,
                order_type=DHAN_CLIENT.SLM, # Stop Loss Market Trigger
                product_type=DHAN_CLIENT.INTRA,
                price=0,
                trigger_price=round(entry_price, 2)
            )
            
            if response.get('status') == 'success' or response.get('orderId'):
                # Create DB Record
                with transaction.atomic():
                    trade = CashBreakoutTrade.objects.create(
                        strategy=self.settings,
                        symbol=symbol,
                        security_id=candle['security_id'],
                        quantity=qty,
                        status='PENDING_ENTRY',
                        entry_level=entry_price,
                        stop_level=stop_loss,
                        target_level=target,
                        candle_ts=candle['ts'],
                        prev_day_high=pdh,
                        entry_order_id=response.get('orderId')
                    )
                    self.active_trades[symbol] = trade
            else:
                r.decr(self.trade_count_key) # Revert limit if API failed
                print(f"Order Failed for {symbol}: {response}")

        except Exception as e:
            r.decr(self.trade_count_key)
            print(f"Exception placing order for {symbol}: {e}")

    def monitor_trades(self, live_ltp_map):
        """Checks open trades for Exit conditions (SL/Target/TSL) based on live LTP."""
        if not self.running: return
        
        # Time Exit Check
        if datetime.now(IST).time() >= self.settings.end_time:
            self.close_all_positions("End of Day")
            return

        for symbol, trade in list(self.active_trades.items()):
            if trade.status != 'OPEN': continue
            
            ltp = live_ltp_map.get(trade.security_id, 0)
            if ltp == 0: continue
            
            # A. Target Hit
            if ltp >= trade.target_level:
                self.exit_trade(trade, "Target Hit")
                continue
            
            # B. Stop Loss Hit
            if ltp <= trade.stop_level:
                self.exit_trade(trade, "Stop Loss Hit")
                continue
                
            # C. Trailing SL (Breakeven)
            if trade.stop_level < trade.entry_level:
                risk = trade.entry_level - trade.stop_level
                # Trigger point to move SL to Breakeven
                trigger = trade.entry_level + (settings.BREAKEVEN_TRIGGER_R * risk)
                
                if ltp >= trigger:
                    trade.stop_level = trade.entry_level
                    trade.save()
                    print(f"TSL: Moved {symbol} SL to Breakeven.")

    def exit_trade(self, trade, reason):
        """Places Market Exit Order."""
        if not DHAN_CLIENT: return
        try:
            DHAN_CLIENT.place_order(
                security_id=trade.security_id,
                exchange_segment=DHAN_CLIENT.NSE,
                transaction_type=DHAN_CLIENT.SELL,
                quantity=trade.quantity,
                order_type=DHAN_CLIENT.MARKET,
                product_type=DHAN_CLIENT.INTRA,
                price=0
            )
            # We DO NOT update DB status to 'CLOSED' here. 
            # We set it to PENDING_EXIT and wait for the WebSocket Order Update 
            # to confirm the fill. This prevents race conditions.
            trade.status = 'PENDING_EXIT'
            trade.exit_reason = reason
            trade.save()
            print(f"EXIT: Sent Sell for {trade.symbol}. Reason: {reason}")
        except Exception as e:
            print(f"Exit Failed for {trade.symbol}: {e}")

    def close_all_positions(self, reason):
        for t in self.active_trades.values():
            if t.status == 'OPEN':
                self.exit_trade(t, reason)


# --- Component 3: Reconciliation (Event Driven via Stream) ---

def handle_order_update(order_data, strategy):
    """Updates trade status based on WebSocket Order Update events from Stream."""
    
    order_id = order_data.get('orderId') or order_data.get('OrderNo')
    status = order_data.get('orderStatus') or order_data.get('OrderStatus')
    
    if not order_id or not status: return

    # Check if this order belongs to any active trade
    trade = None
    is_entry = False
    
    # Search in-memory first for speed
    for t in strategy.active_trades.values():
        if t.entry_order_id == order_id:
            trade = t
            is_entry = True
            break
        elif t.exit_order_id == order_id:
            trade = t
            is_entry = False
            break
            
    # If not in memory (e.g. after restart), check DB
    if not trade:
        try:
            trade = CashBreakoutTrade.objects.filter(entry_order_id=order_id).first()
            if trade: is_entry = True
            else:
                trade = CashBreakoutTrade.objects.filter(exit_order_id=order_id).first()
                is_entry = False
        except: pass
        
    if not trade: return # Order not related to our algo

    # -- Process Status --
    if status == 'TRADED':
        fill_price = float(order_data.get('tradedPrice') or order_data.get('TradedPrice') or 0)
        
        if is_entry and trade.status == 'PENDING_ENTRY':
            # ENTRY FILLED
            trade.status = 'OPEN'
            trade.entry_price = fill_price
            trade.entry_time = timezone.now()
            trade.save()
            strategy.active_trades[trade.symbol] = trade # Ensure in memory
            print(f"CONFIRMED: Entry Filled for {trade.symbol} @ {fill_price}")
            
        elif not is_entry and trade.status in ['OPEN', 'PENDING_EXIT']:
            # EXIT FILLED
            trade.status = 'CLOSED'
            trade.exit_price = fill_price
            trade.exit_time = timezone.now()
            trade.pnl = (trade.exit_price - trade.entry_price) * trade.quantity
            trade.save()
            
            # Remove from active monitoring
            if trade.symbol in strategy.active_trades:
                del strategy.active_trades[trade.symbol]
            
            # Update PnL in Redis for dashboard
            r.incrbyfloat(strategy.daily_pnl_key, trade.pnl)
            print(f"CONFIRMED: Exit Filled for {trade.symbol}. PnL: {trade.pnl}")

    elif status in ['CANCELLED', 'REJECTED', 'EXPIRED']:
        if is_entry:
            trade.status = 'FAILED_ENTRY'
            trade.save()
            if trade.symbol in strategy.active_trades:
                del strategy.active_trades[trade.symbol]
            # Revert trade count since entry failed
            r.decr(strategy.trade_count_key)
            print(f"ORDER CANCELLED/REJECTED for {trade.symbol}")


# --- MAIN ENGINE LOOP (STREAMS) ---

def run_algo_engine():
    global DHAN_CLIENT
    r.set(settings.REDIS_STATUS_ALGO_ENGINE, 'STARTING')
    print(f"[{datetime.now()}] Algo Engine Starting in STREAM Mode...")
    
    # 1. Setup Redis Consumer Groups
    setup_consumer_groups()
    
    # 2. Initialize Components
    aggregator = StrategyCandleAggregator(r)
    strategy = CashBreakoutStrategy()
    
    # Hook aggregator output directly to strategy
    aggregator.eject_candle_callback = strategy.process_candle

    # 3. Load Initial Token
    token = r.get(settings.REDIS_DHAN_TOKEN_KEY)
    if token:
        DHAN_CLIENT = get_dhan_client(token)
        print("Dhan Client Initialized.")
    else:
        print("Waiting for Token from Dashboard...")

    r.set(settings.REDIS_STATUS_ALGO_ENGINE, 'RUNNING')

    # 4. Stream Processing Loop
    while True:
        try:
            # Read from all streams using Consumer Group
            # '>' means read only new messages that have arrived since last read
            streams = {
                settings.REDIS_STREAM_MARKET: '>',
                settings.REDIS_STREAM_ORDERS: '>',
                settings.REDIS_STREAM_CONTROL: '>'
            }
            
            # Block for 100ms to reduce CPU usage if empty
            response = r.xreadgroup(
                settings.REDIS_CONSUMER_GROUP, 
                settings.REDIS_CONSUMER_NAME, 
                streams, 
                count=100, 
                block=100
            )

            if not response:
                # Idle Loop: Monitor Open Trades (approx 10 times per second)
                if strategy.active_trades and aggregator.last_ltp:
                    strategy.monitor_trades(aggregator.last_ltp)
                continue

            for stream_name, messages in response:
                for message_id, data in messages:
                    try:
                        # Parse the 'p' (payload) field
                        payload_str = data.get('p')
                        if not payload_str: 
                            r.xack(stream_name, settings.REDIS_CONSUMER_GROUP, message_id)
                            continue
                            
                        payload = json.loads(payload_str)

                        if stream_name == settings.REDIS_STREAM_MARKET:
                            # MARKET DATA -> Aggregator
                            aggregator.process_tick(payload)
                            # Monitor trades frequently on tick arrival as well
                            strategy.monitor_trades(aggregator.last_ltp)
                        
                        elif stream_name == settings.REDIS_STREAM_ORDERS:
                            # ORDER UPDATE -> Reconciliation
                            handle_order_update(payload, strategy)
                        
                        elif stream_name == settings.REDIS_STREAM_CONTROL:
                            # CONTROL SIGNAL -> Settings/Auth
                            if payload.get('action') == 'UPDATE_CONFIG':
                                strategy.settings.refresh_from_db()
                                strategy.running = strategy.settings.is_enabled
                                strategy.load_trades()
                                print(f"Settings Reloaded. Enabled: {strategy.running}")
                            elif payload.get('action') == 'TOKEN_REFRESH':
                                DHAN_CLIENT = get_dhan_client(payload.get('token'))
                                print("Token Refreshed via Control Stream.")

                        # Acknowledge message processed
                        r.xack(stream_name, settings.REDIS_CONSUMER_GROUP, message_id)

                    except Exception as e:
                        print(f"Error processing message {message_id} from {stream_name}: {e}")
                        # Ack even on error to prevent infinite loops on bad data
                        r.xack(stream_name, settings.REDIS_CONSUMER_GROUP, message_id)

        except Exception as e:
            print(f"Main Loop Error: {e}")
            time.sleep(1) # Backoff slightly on redis connection errors

if __name__ == '__main__':
    run_algo_engine()