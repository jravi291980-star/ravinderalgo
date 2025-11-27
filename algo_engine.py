# algo_engine.py - Runs on an Algo Dyno on Heroku
import redis
import json
import os
import time
import threading
from dhanhq import dhanhq, DhanContext  # Import necessary classes
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, Optional, Any, List
from math import floor
from tenacity import retry, stop_after_attempt, wait_fixed, RetryError

# --- Django Setup and Imports for Worker ---
# Note: This is critical for DB access on the worker dyno
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'algotrader.settings')
try:
    django.setup()
    from django.db import transaction, models
    from django.utils import timezone
    from django.conf import settings
    from dashboard.models import CashBreakoutTrade, StrategySettings

    # Initialize constants from settings
    REDIS_URL = settings.REDIS_URL
    REDIS_DATA_CHANNEL = settings.REDIS_DATA_CHANNEL
    REDIS_ORDER_UPDATE_CHANNEL = settings.REDIS_ORDER_UPDATE_CHANNEL
    REDIS_CANDLE_CHANNEL = settings.REDIS_CANDLE_CHANNEL
    REDIS_CONTROL_CHANNEL = settings.REDIS_CONTROL_CHANNEL
    REDIS_AUTH_CHANNEL = settings.REDIS_AUTH_CHANNEL
    REDIS_STATUS_ALGO_ENGINE = settings.REDIS_STATUS_ALGO_ENGINE
    REDIS_DHAN_TOKEN_KEY = settings.REDIS_DHAN_TOKEN_KEY
    PREV_DAY_HASH = settings.PREV_DAY_HASH
    LIVE_OHLC_KEY = settings.LIVE_OHLC_KEY
    RISK_MULTIPLIER = settings.RISK_MULTIPLIER
    BREAKEVEN_TRIGGER_R = settings.BREAKEVEN_TRIGGER_R
    MAX_MONITORING_MINUTES = settings.MAX_MONITORING_MINUTES
    RECONCILIATION_INTERVAL_SECONDS = settings.RECONCILIATION_INTERVAL_SECONDS

    CLIENT_ID = settings.DHAN_CLIENT_ID
except Exception as e:
    print(f"CRITICAL: Failed to load Django/Settings: {e}. Exiting.")
    time.sleep(60)
    exit()

# --- Redis & Dhan Client Setup ---
r = redis.from_url(REDIS_URL, decode_responses=True)
DHAN_CLIENT: Optional[dhanhq] = None
IST = timezone.pytz.timezone("Asia/Kolkata")

# Global variables/containers (populated by dhan_workers.py)
SYMBOL_TO_SECURITY_ID: Dict[str, str] = {}
SECURITY_ID_TO_SYMBOL: Dict[str, str] = {}


# --- Utility Functions (Adapted from old strategy) ---

def get_dhan_client(token):
    """Initializes and returns the Dhan REST client using DhanContext."""
    global DHAN_CLIENT
    try:
        dhan_context = DhanContext(CLIENT_ID, token)
        DHAN_CLIENT = dhanhq(dhan_context)
        print(f"[{datetime.now()}] Dhan REST client initialized with new token.")
    except Exception as e:
        print(f"ERROR initializing Dhan client: {e}")
        DHAN_CLIENT = None
    return DHAN_CLIENT


def _get_prev_day_high(symbol: str) -> Optional[float]:
    """Return the previous day high for `symbol` from Redis."""
    try:
        raw = r.hget(PREV_DAY_HASH, symbol)
        if not raw:
            return None
        # The data is expected to be {'high': 123.45}
        parsed = json.loads(raw)
        return float(parsed.get("high")) if parsed.get("high") is not None else None
    except Exception as e:
        print(f"ERROR: failed to read prev day high for {symbol}: {e}")
        return None


def _calculate_quantity(max_loss_amount: float, entry_price: float, sl_price: float) -> int:
    """Compute allowed quantity based on max risk amount, mirroring the original logic."""
    try:
        max_loss_amount = float(max_loss_amount)
    except Exception:
        return 0

    risk_per_share = abs(entry_price - sl_price)
    if risk_per_share <= 0.001:
        return 0

    qty = floor(max_loss_amount / risk_per_share)
    qty = max(0, int(qty))
    return qty


# --- Candle Aggregation and Ejection Logic ---

class StrategyCandleAggregator:
    """Aggregates tick data into 1-minute candles and publishes them."""

    def __init__(self):
        self.aggregators: Dict[str, Dict[str, Any]] = {}  # Security ID -> Candle Data
        self.LTP_SNAPSHOT: Dict[str, float] = {}  # Security ID -> LTP
        self.r = r
        self.candle_channel = REDIS_CANDLE_CHANNEL
        self.ohlc_key = LIVE_OHLC_KEY

    def aggregate_tick(self, tick_data):
        """Processes a single tick update (received via Redis Pub/Sub)."""

        # We assume the incoming tick_data uses Dhan's Security ID as the primary key
        security_id = str(tick_data.get('securityId'))
        ltp = tick_data.get('ltp')
        timestamp_ms = tick_data.get('lastTradeTime')

        if not security_id or not ltp or not timestamp_ms: return

        # 1. Update LTP Snapshot for real-time monitoring
        self.LTP_SNAPSHOT[security_id] = float(ltp)
        self.r.set(self.ohlc_key, json.dumps(self.LTP_SNAPSHOT))  # Persist snapshot

        # Determine the current 1-minute candle key
        tick_time = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=IST)
        candle_timestamp = tick_time.replace(second=0, microsecond=0)

        # 2. Candle Aggregation Logic
        if security_id in self.aggregators:
            current_candle = self.aggregators[security_id]
            current_ts = current_candle['ts']

            if candle_timestamp > current_ts:
                # Eject and Publish the Completed Candle
                self._eject_candle(security_id, current_candle)
                # Start the new candle
                self.aggregators[security_id] = self._create_new_candle(security_id, candle_timestamp, ltp)
            else:
                # Update the ongoing candle
                current_candle['high'] = max(current_candle['high'], float(ltp))
                current_candle['low'] = min(current_candle['low'], float(ltp))
                current_candle['close'] = float(ltp)
                # Volume update logic is omitted but assumed to be here if raw V data is available
        else:
            # Initialize the first candle
            self.aggregators[security_id] = self._create_new_candle(security_id, candle_timestamp, ltp)

    def _create_new_candle(self, security_id, timestamp, ltp):
        """Initializes a new candle dictionary."""
        price = float(ltp)
        return {
            'security_id': security_id,
            'ts': timestamp,
            'open': price,
            'high': price,
            'low': price,
            'close': price,
            'volume': 0
        }

    def _eject_candle(self, security_id, completed_candle):
        """Publishes a completed candle to Redis for the Strategy Engine to consume."""

        ts_str = completed_candle['ts'].isoformat()
        trading_symbol = SECURITY_ID_TO_SYMBOL.get(security_id, security_id)  # Resolve symbol for trade model

        payload = {
            'symbol': trading_symbol,
            'security_id': security_id,
            'ts': ts_str,
            'open': completed_candle['open'],
            'high': completed_candle['high'],
            'low': completed_candle['low'],
            'close': completed_candle['close'],
            'volume': completed_candle['volume'],
        }

        self.r.publish(self.candle_channel, json.dumps(payload))
        # print(f"[{datetime.now(IST).strftime('%H:%M:%S')}] EJECTED CANDLE for {trading_symbol}")


# --- Cash Breakout Strategy Implementation ---

class CashBreakoutStrategy:
    """Implements the Long Breakout logic for Dhan."""

    def __init__(self):
        self.r = r
        self.DHAN_CLIENT = DHAN_CLIENT
        self.settings = StrategySettings.objects.first()  # Should be only one instance
        if not self.settings:
            print("CRITICAL: StrategySettings not found in DB!")
            self.running = False
        else:
            self.running = self.settings.is_enabled

        self.active_trades: Dict[str, CashBreakoutTrade] = {}  # Symbol -> Trade object
        self.trade_count_key = f"breakout_trade_count:{CLIENT_ID}:{datetime.now(IST).date().isoformat()}"
        self.daily_pnl_key = f"cb_daily_realized_pnl:{CLIENT_ID}:{datetime.now(IST).date().isoformat()}"
        self.active_entries_set = f"breakout_active_entries:{CLIENT_ID}"
        self.exiting_trades_set = f"breakout_exiting_trades:{CLIENT_ID}"

        self.load_trades_from_db()

    def load_trades_from_db(self):
        """Refreshes active trades from the database for in-memory monitoring."""
        self.active_trades = {
            t.symbol: t for t in CashBreakoutTrade.objects.filter(
                status__in=['OPEN', 'PENDING_ENTRY', 'PENDING_EXIT']
            ).select_related('strategy')  # Prefetch strategy
        }

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(0.05))
    def _check_and_increment_trade_count(self) -> bool:
        """Atomically checks global limit and increments counter (Simplified)."""
        max_trades_total = self.settings.max_total_trades
        current_count = int(r.get(self.trade_count_key) or 0)

        if current_count >= max_trades_total:
            print(f"LIMIT REACHED: Max total trades ({max_trades_total}) exceeded.")
            return False

        r.incr(self.trade_count_key)
        r.expire(self.trade_count_key, 86400)
        return True

    def _rollback_trade_count(self) -> None:
        """Decrement the global daily trade count after an aborted entry attempt."""
        current_count = int(r.get(self.trade_count_key) or 0)
        if current_count > 0:
            r.decr(self.trade_count_key)

    def _dhan_place_order(self, security_id, symbol, quantity, txn_type, order_type, trigger_price=0.0):
        """Dhan-compatible order placement wrapper with required fields."""
        if not self.DHAN_CLIENT:
            return None

        try:
            exchange_segment = self.DHAN_CLIENT.NSE
            product_type = self.DHAN_CLIENT.INTRA  # Cash trading only

            response = self.DHAN_CLIENT.place_order(
                security_id=security_id,
                exchange_segment=exchange_segment,
                transaction_type=txn_type,
                quantity=quantity,
                order_type=order_type,
                product_type=product_type,
                price=0,
                trigger_price=round(trigger_price, 2) if order_type == self.DHAN_CLIENT.SLM else 0.0
            )

            # Dhan API returns orderId directly in the response dictionary on success
            if response and response.get('orderId'):
                return response
            else:
                print(f"ORDER FAILED (API): {response.get('message', 'Unknown Error')}")
                return None

        except Exception as e:
            print(f"ORDER FAILED (Exception) for {symbol}: {e}")
            return None

    def process_completed_candle(self, candle_payload: Dict[str, Any]):
        """
        Implements the Entry Signal Logic using the completed 1-minute candle.
        """
        if not self.settings.is_enabled: return

        symbol = candle_payload.get("symbol")
        security_id = candle_payload.get("security_id")

        # 1. Check if symbol is already active
        if symbol in self.active_trades: return

        prev_high = _get_prev_day_high(symbol)
        if prev_high is None: return

        # Extract candle data
        try:
            low = float(candle_payload.get("low") or 0.0)
            high = float(candle_payload.get("high") or 0.0)
            vol = int(candle_payload.get("volume") or 0)
            candle_open = float(candle_payload.get("open") or 0.0)
            candle_close = float(candle_payload.get("close") or 0.0)
            candle_ts = datetime.fromisoformat(candle_payload.get("ts")).astimezone(IST)
        except Exception:
            return

        ref_price = candle_close if candle_close > 0 else (high if high > 0 else 1.0)

        # --- Entry Filters (Core Breakout Logic) ---
        if not (candle_close > candle_open): return  # Bullish candle
        if not (low < prev_high < candle_close): return  # PDH must be crossed cleanly (entry candle)
        if not (candle_open < prev_high): return  # Must have opened below PDH

        size_pct = (high - low) / ref_price if ref_price else 0.0
        if size_pct > self.settings.max_candle_pct: return  # Max candle size filter

        # --- Compute PENDING entry / stop / target ---
        entry_level = high * (1.0 + self.settings.entry_offset_pct)
        stop_level = low - (low * self.settings.stop_offset_pct)
        stop_distance_prelim = entry_level - stop_level
        target_level_prelim = entry_level + (RISK_MULTIPLIER * stop_distance_prelim)

        # 2. Calculate Quantity and Check Limits
        quantity = _calculate_quantity(self.settings.per_trade_sl_amount, entry_level, stop_level)
        if quantity <= 0: return

        # Atomically check and increment global limit *before* placing order
        if not self._check_and_increment_trade_count(): return

        # 3. Place Stop-Limit Market Entry Order (SLM BUY)
        order_response = self._dhan_place_order(
            security_id=security_id,
            symbol=symbol,
            quantity=quantity,
            txn_type=self.DHAN_CLIENT.BUY,
            order_type=self.DHAN_CLIENT.SLM,
            trigger_price=entry_level  # Entry trigger price
        )

        if not order_response:
            self._rollback_trade_count()
            return

        # 4. Store PENDING_ENTRY trade to DB
        with transaction.atomic():
            trade = CashBreakoutTrade.objects.create(
                strategy=self.settings,
                symbol=symbol,
                security_id=security_id,
                quantity=quantity,
                status="PENDING_ENTRY",
                entry_order_id=order_response.get('orderId'),
                candle_ts=candle_ts,
                prev_day_high=prev_high,
                entry_level=round(entry_level, 6),
                stop_level=round(stop_level, 6),
                target_level=round(target_level_prelim, 6),
                candle_high=high,
                candle_low=low,
                volume_price=vol * ref_price
            )
            self.active_trades[symbol] = trade
            self.r.sadd(self.active_entries_set, symbol)
            print(f"PENDING TRADE REGISTERED: {symbol} @ {entry_level}")

    def monitor_open_trades(self):
        """
        Monitors open trades for SL/Target/TSL/Time exit conditions.
        Runs in the fast main loop.
        """
        if not self.settings.is_enabled: return

        try:
            raw_ohlc = self.r.get(LIVE_OHLC_KEY)
            live_ohlc = json.loads(raw_ohlc) if raw_ohlc else {}
        except Exception:
            live_ohlc = {}

        unrealized_pnl = 0.0
        now_time = datetime.now(IST).time()

        # --- Time Square Off Check ---
        if now_time >= self.settings.end_time:
            self.force_square_off("Breakout End Time Reached")
            return

        for trade in list(self.active_trades.values()):
            if trade.status != "OPEN":
                continue

            ltp = live_ohlc.get(trade.security_id, 0.0)
            if ltp == 0.0: continue

            if trade.entry_price:
                unrealized_pnl += (ltp - trade.entry_price) * trade.quantity
                risk_per_share = trade.entry_price - trade.stop_level
            else:
                risk_per_share = 0.0

            # --- Breakeven TSL (1:1.25 R:R) Logic ---
            if risk_per_share > 0 and trade.stop_level < trade.entry_price:
                breakeven_trigger_price = trade.entry_price + (BREAKEVEN_TRIGGER_R * risk_per_share)

                if ltp >= breakeven_trigger_price:
                    new_stop_level = trade.entry_price
                    if new_stop_level > trade.stop_level:
                        trade.stop_level = round(new_stop_level, 6)
                        trade.save(update_fields=['stop_level', 'updated_at'])
                        print(f"TSL MOVED for {trade.symbol} to Entry: {trade.stop_level}")

            # --- Exit Condition 1: Stop Loss Hit ---
            if ltp <= trade.stop_level:
                self.exit_trade(trade, "SL/TSL Hit")
                continue

            # --- Exit Condition 2: Target Hit (2.5R) ---
            if ltp >= trade.target_level:
                self.exit_trade(trade, f"Target Hit ({RISK_MULTIPLIER}R)")
                continue

        # Check Global P&L Limits
        self._check_pnl_exit_conditions(unrealized_pnl)

    def _check_pnl_exit_conditions(self, unrealized_pnl: float):
        """Checks global daily P&L against limits."""
        if not self.settings.pnl_exit_enabled: return

        realized_pnl = float(self.r.get(self.daily_pnl_key) or 0.0)
        net_pnl = realized_pnl + unrealized_pnl
        profit_target = self.settings.pnl_profit_target
        stop_loss = -self.settings.pnl_stop_loss

        if net_pnl >= profit_target or net_pnl <= stop_loss:
            reason = "Daily P&L Target Reached" if net_pnl >= profit_target else "Daily P&L Stop Loss Reached"
            print(f"P&L EXIT TRIGGERED: {reason}. Net PnL: {net_pnl:.2f}")
            self.force_square_off(reason)

    def exit_trade(self, trade: CashBreakoutTrade, reason: str):
        """Places a market exit order for an OPEN trade."""
        if trade.status != "OPEN": return
        if self.r.sismember(self.exiting_trades_set, trade.id): return

        order_response = self._dhan_place_order(
            security_id=trade.security_id,
            symbol=trade.symbol,
            quantity=abs(trade.quantity),
            txn_type=self.DHAN_CLIENT.SELL,
            order_type=self.DHAN_CLIENT.MARKET
        )

        if order_response and order_response.get('orderId'):
            with transaction.atomic():
                trade.status = "PENDING_EXIT"
                trade.exit_order_id = order_response['orderId']
                trade.exit_reason = reason
                trade.save()
                self.r.sadd(self.exiting_trades_set, trade.id)
                print(f"EXIT ORDER PLACED for {trade.symbol} reason={reason}")
        else:
            trade.status = "FAILED_EXIT"
            trade.exit_order_id = None
            trade.save()
            print(f"CRITICAL: Failed to place exit order for {trade.symbol}.")

    def force_square_off(self, reason: str):
        """Closes all currently OPEN positions."""
        for trade in list(self.active_trades.values()):
            if trade.status == "OPEN":
                self.exit_trade(trade, reason)
                time.sleep(0.1)


def run_pending_monitor(strategy: CashBreakoutStrategy):
    """
    Checks PENDING_ENTRY trades for the 6-minute time expiry or if LTP falls below stop.
    This logic runs in the fast loop, independent of candle closure.
    """
    now = datetime.now(IST)

    # Load latest LTP snapshot from Redis
    try:
        raw_ohlc = r.get(LIVE_OHLC_KEY)
        live_ohlc = json.loads(raw_ohlc) if raw_ohlc else {}
    except Exception:
        live_ohlc = {}

    # 1. First, retrieve all pending trades from the database for atomic updates
    pending_qs = CashBreakoutTrade.objects.filter(status='PENDING_ENTRY').select_for_update()

    for trade in pending_qs:
        cancel_reason = None

        # 1. 6-minute expiry check
        expiry_dt = trade.candle_ts + timedelta(minutes=MAX_MONITORING_MINUTES)
        if now > expiry_dt:
            cancel_reason = "Expired (6-minute limit reached)"

        # 2. LTP vs Stop Level check
        ltp = live_ohlc.get(trade.security_id, 0.0)
        if ltp != 0.0 and ltp < trade.stop_level:
            cancel_reason = cancel_reason or "LTP fell below stop level"

        if cancel_reason:
            # Attempt to cancel the order at Dhan
            if DHAN_CLIENT and trade.entry_order_id:
                try:
                    DHAN_CLIENT.cancel_order(trade.entry_order_id)
                except Exception:
                    # Ignore failure to send cancel signal, reconciliation handles status change
                    pass

            # Update DB to EXPIRED. Reconciliation loop will confirm if it filled/cancelled.
            with transaction.atomic():
                # We need to lock and refetch here because we are outside the main loop's control flow
                trade.status = 'EXPIRED'
                trade.save()
                strategy._rollback_trade_count()
                strategy.active_trades.pop(trade.symbol, None)
                r.srem(strategy.active_entries_set, trade.symbol)
                print(f"PENDING TRADE MARKED EXPIRED: {trade.symbol}")


# --- MAIN EXECUTION LOOP ---

def run_algo_engine():
    """Main loop to orchestrate data aggregation and strategy execution."""

    r.set(REDIS_STATUS_ALGO_ENGINE, 'STARTING')
    # Load the global symbol/ID maps from the Redis keys populated by dhan_workers.py
    global SYMBOL_TO_SECURITY_ID, SECURITY_ID_TO_SYMBOL
    try:
        SYMBOL_TO_SECURITY_ID = json.loads(r.get('SYMBOL_TO_SECURITY_ID') or '{}')
        SECURITY_ID_TO_SYMBOL = json.loads(r.get('SECURITY_ID_TO_SYMBOL') or '{}')
    except Exception:
        print("WARNING: Could not load initial security mappings from Redis.")
        pass

    token = r.get(REDIS_DHAN_TOKEN_KEY)
    if token:
        get_dhan_client(token)

    aggregator = StrategyCandleAggregator()
    strategy = CashBreakoutStrategy()

    r.set(REDIS_STATUS_ALGO_ENGINE, 'RUNNING')
    print(f"[{datetime.now()}] Algo Trading Engine Ready.")

    # Subscribe to ALL necessary Redis channels
    pubsub = r.pubsub()
    pubsub.subscribe(REDIS_DATA_CHANNEL, REDIS_ORDER_UPDATE_CHANNEL, REDIS_CANDLE_CHANNEL, REDIS_CONTROL_CHANNEL,
                     REDIS_AUTH_CHANNEL)

    last_monitor_time = time.time()

    for message in pubsub.listen():
        if message['type'] != 'message': continue

        channel = message['channel']
        try:
            data = json.loads(message['data'])
        except json.JSONDecodeError:
            continue

        # A. New Market Tick -> Aggregation (Ultra Low Latency Path)
        if channel == REDIS_DATA_CHANNEL:
            aggregator.aggregate_tick(data)

        # B. Completed Candle -> Strategy Entry Check
        elif channel == REDIS_CANDLE_CHANNEL:
            now_time = datetime.now(IST).time()
            if strategy.settings and now_time >= strategy.settings.start_time and now_time <= strategy.settings.end_time:
                strategy.process_completed_candle(data)

        # C. Live Order Update -> Instant Reconciliation (Critical Low Latency Path)
        elif channel == REDIS_ORDER_UPDATE_CHANNEL:
            handle_low_latency_reconciliation(data, strategy)

        # D. Control/Auth Channel Updates
        elif channel == REDIS_CONTROL_CHANNEL and data.get('action') == 'UPDATE_CONFIG':
            strategy.settings.refresh_from_db()
            strategy.running = strategy.settings.is_enabled
            strategy.load_trades_from_db()

        elif channel == REDIS_AUTH_CHANNEL and data.get('action') == 'TOKEN_REFRESH':
            get_dhan_client(data.get('token'))

        # E. Fast Loop Monitoring (Runs every RECONCILIATION_INTERVAL_SECONDS)
        if time.time() - last_monitor_time >= RECONCILIATION_INTERVAL_SECONDS:
            last_monitor_time = time.time()
            if strategy.running:
                strategy.monitor_open_trades()  # SL/Target/TSL check
                run_pending_monitor(strategy)  # 6-minute pending expiry check


def handle_low_latency_reconciliation(order_data: Dict[str, Any], strategy: CashBreakoutStrategy):
    """Processes real-time order status updates via Dhan WebSocket (replaces Kite polling)."""

    dhan_order_id = order_data.get('OrderNo')
    status = order_data.get('OrderStatus')
    traded_qty = order_data.get('TradedQty')
    traded_price = order_data.get('TradedPrice')

    if not dhan_order_id or not status: return

    try:
        trade = CashBreakoutTrade.objects.filter(entry_order_id=dhan_order_id).first()
        is_entry = True
        if not trade:
            trade = CashBreakoutTrade.objects.filter(exit_order_id=dhan_order_id).first()
            is_entry = False
        if not trade: return
    except Exception:
        return

    # Using select_for_update to handle concurrency if multiple algo engines run
    with transaction.atomic():
        trade = CashBreakoutTrade.objects.select_for_update().get(id=trade.id)

        if status == 'TRADED' and int(traded_qty or 0) > 0:
            if is_entry and trade.status == 'PENDING_ENTRY':
                # Entry Filled
                risk_per_share = float(traded_price) - trade.stop_level
                dynamic_target_level = float(traded_price) + (RISK_MULTIPLIER * risk_per_share)

                trade.status = 'OPEN'
                trade.entry_price = float(traded_price)
                trade.entry_time = timezone.now()
                trade.target_level = round(dynamic_target_level, 6)

                strategy.active_trades[trade.symbol] = trade
                print(f"ENTRY FILLED: {trade.symbol} @ {trade.entry_price}")

            elif not is_entry and trade.status == 'PENDING_EXIT':
                # Exit Filled
                trade.status = 'CLOSED'
                trade.exit_price = float(traded_price)
                trade.exit_time = timezone.now()
                pnl = (trade.exit_price - trade.entry_price) * trade.quantity
                trade.pnl = pnl

                r.incrbyfloat(strategy.daily_pnl_key, pnl)

                strategy.active_trades.pop(trade.symbol, None)
                r.srem(strategy.active_entries_set, trade.symbol)
                r.srem(strategy.exiting_trades_set, trade.id)
                print(f"EXIT FILLED: {trade.symbol}. PnL: {pnl:.2f}")

        elif status in ('CANCELLED', 'REJECTED', 'FAILED', 'EXPIRED'):
            if is_entry:
                if trade.status == 'PENDING_ENTRY':
                    trade.status = 'FAILED_ENTRY'
                    strategy._rollback_trade_count()
                    strategy.active_trades.pop(trade.symbol, None)
                    r.srem(strategy.active_entries_set, trade.symbol)
                    print(f"ENTRY CANCELLED/REJECTED: {trade.symbol}")
            elif not is_entry:
                if trade.status == 'PENDING_EXIT':
                    trade.status = 'OPEN'
                    trade.exit_order_id = None
                    r.srem(strategy.exiting_trades_set, trade.id)
                    print(f"EXIT FAILED: {trade.symbol}. Reverting to OPEN.")

        trade.save()


if __name__ == '__main__':
    run_algo_engine()