from django.db import models
from django.utils import timezone
from datetime import datetime
import pytz # <-- CORRECTED IMPORT: pytz must be imported directly

# Ensure IST timezone is available for use in default values
IST = pytz.timezone("Asia/Kolkata")



class DhanCredentials(models.Model):
    """Stores Dhan API credentials (Client ID) and the dynamic Access Token."""

    # Static credential
    client_id = models.CharField(max_length=100, unique=True, verbose_name="Dhan Client ID")

    # The session access token, generated daily/sessionally
    access_token = models.CharField(max_length=512, blank=True, null=True, verbose_name="Current Access Token")
    token_generation_time = models.DateTimeField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Dhan Credentials"

    def __str__(self):
        return f"Credentials for {self.client_id}"


class StrategySettings(models.Model):
    """Configuration for the Cash Breakout Strategy, replacing the old Account attributes."""

    STRATEGY_CHOICES = [
        ('CASH_ALGO_1', 'Cash Breakout Strategy'),
    ]

    name = models.CharField(max_length=100, unique=True)
    strategy_type = models.CharField(max_length=50, choices=STRATEGY_CHOICES, default='CASH_ALGO_1')
    is_enabled = models.BooleanField(default=False, verbose_name="Enable Trading Logic (Master Switch)")

    # --- Trade Universe Configuration ---
    # The engine will trade all stocks found in the cached instrument list.
    max_trades_per_stock = models.IntegerField(default=2, verbose_name="Max Closed Trades per Symbol (Daily)")
    max_total_trades = models.IntegerField(default=10, verbose_name="Max Total Trades (Daily)")

    # --- Strategy Parameters (from your original logic) ---
    entry_offset_pct = models.FloatField(default=0.0001, verbose_name="Entry Buffer % (above High)")
    stop_offset_pct = models.FloatField(default=0.0002, verbose_name="SL Buffer % (below Low)")
    max_candle_pct = models.FloatField(default=0.007, verbose_name="Max Candle Size % Filter")
    per_trade_sl_amount = models.FloatField(default=2000.00, verbose_name="Max Rupee Risk per Trade")

    # --- Time & P&L Exits ---
    start_time = models.TimeField(default=timezone.make_aware(datetime.strptime('09:20:00', '%H:%M:%S'), IST).time(),
                                  verbose_name="Strategy Start Time (IST)")
    end_time = models.TimeField(default=timezone.make_aware(datetime.strptime('15:00:00', '%H:%M:%S'), IST).time(),
                                verbose_name="Strategy End Time (IST - Force Square Off)")

    pnl_exit_enabled = models.BooleanField(default=False, verbose_name="Enable Daily P&L Limits")
    pnl_profit_target = models.FloatField(default=5000.00, verbose_name="Daily Profit Target (₹)")
    pnl_stop_loss = models.FloatField(default=2500.00, verbose_name="Daily Stop Loss Limit (₹)")

    # --- Manual Control Flag ---
    manual_override = models.BooleanField(default=False,
                                          verbose_name="Manual Trade Control Override (Disable Algo Entries)")

    class Meta:
        verbose_name_plural = "Strategy Settings"

    def __str__(self):
        return self.name


class CashBreakoutTrade(models.Model):
    """Tracks the detailed state of every trade executed by the breakout engine."""

    STATUS_CHOICES = [
        ('PENDING_ENTRY', 'Pending Entry Order'),
        ('OPEN', 'Open Position'),
        ('PENDING_EXIT', 'Pending Exit Order'),
        ('CLOSED', 'Closed/Squared Off'),
        ('EXPIRED', 'Pending Entry Expired (6 min/SL)'),
        ('FAILED_ENTRY', 'Entry Order Failed/Rejected'),
    ]

    strategy = models.ForeignKey(StrategySettings, on_delete=models.SET_NULL, null=True)
    symbol = models.CharField(max_length=20)
    security_id = models.CharField(max_length=20)  # Dhan Security ID for fast reference
    quantity = models.IntegerField(default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_ENTRY')
    exit_reason = models.CharField(max_length=255, blank=True, null=True)

    # Price Levels (Set upon entry signal generation)
    prev_day_high = models.FloatField(blank=True, null=True)
    entry_level = models.FloatField(verbose_name="Target Entry Price (Trigger)")
    stop_level = models.FloatField(verbose_name="Stop Loss Price")
    target_level = models.FloatField(verbose_name="Target Price (2.5R)")

    # Execution Details (Filled by Order Update WebSocket)
    entry_price = models.FloatField(blank=True, null=True)
    exit_price = models.FloatField(blank=True, null=True)

    # Broker Order IDs
    entry_order_id = models.CharField(max_length=50, blank=True, null=True)
    exit_order_id = models.CharField(max_length=50, blank=True, null=True)

    # Time Stamps
    candle_ts = models.DateTimeField(verbose_name="Candle Signal Time")
    entry_time = models.DateTimeField(blank=True, null=True)
    exit_time = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # PnL
    pnl = models.FloatField(default=0.00, verbose_name="Realized PnL")

    # Candle Details (for record keeping/debugging)
    candle_high = models.FloatField(blank=True, null=True)
    candle_low = models.FloatField(blank=True, null=True)
    volume_price = models.FloatField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Cash Breakout Trades"

    def __str__(self):
        return f"{self.symbol} ({self.status}) @ {self.entry_price or 'N/A'}"