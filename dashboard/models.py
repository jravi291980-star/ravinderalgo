from django.db import models

# Create your models here.
from django.db import models


class DhanCredentials(models.Model):
    """Stores Dhan API credentials (Client ID) and the current access token."""

    client_id = models.CharField(max_length=100, unique=True, verbose_name="Dhan Client ID")

    # We store the latest generated token here for persistence and worker loading.
    access_token = models.CharField(max_length=512, blank=True, null=True, verbose_name="Current Access Token")
    token_generation_time = models.DateTimeField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Dhan Credentials"

    def __str__(self):
        return f"Credentials for {self.client_id}"


class StrategySettings(models.Model):
    """Settings for a single trading strategy instance."""

    # Placeholder for multiple strategies later
    STRATEGY_CHOICES = [
        ('CASH_ALGO_1', 'Cash Momentum Strategy'),
    ]

    name = models.CharField(max_length=100, unique=True)
    strategy_type = models.CharField(max_length=50, choices=STRATEGY_CHOICES, default='CASH_ALGO_1')
    is_enabled = models.BooleanField(default=False, verbose_name="Enable Trading Logic")

    # --- Strategy Parameters (Placeholders) ---
    security_id = models.CharField(max_length=20, default='1333', verbose_name="NSE Security ID (e.g., HDFC Bank)")
    symbol = models.CharField(max_length=20, default='HDFCBANK', verbose_name="Trading Symbol")
    quantity = models.IntegerField(default=10, verbose_name="Trade Quantity (in lots/shares)")

    # Example logic parameters
    lookback_period = models.IntegerField(default=5, verbose_name="Lookback Period (Minutes)")
    entry_signal_threshold = models.FloatField(default=0.1, verbose_name="Entry Threshold (%)")

    # Manual Control Flag (When TRUE, algo stops placing new orders)
    manual_override = models.BooleanField(default=False,
                                          verbose_name="Manual Trade Control Override (Disable Algo Entry/Exit)")

    def __str__(self):
        return self.name


class LiveTrade(models.Model):
    """Tracks live trades executed by the algo engine for dashboard monitoring."""

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
        ('CANCELLED', 'Cancelled'),
        ('ERROR', 'Error'),
    ]

    strategy = models.ForeignKey(StrategySettings, on_delete=models.SET_NULL, null=True)
    symbol = models.CharField(max_length=20)
    entry_price = models.FloatField(blank=True, null=True)
    exit_price = models.FloatField(blank=True, null=True)
    quantity = models.IntegerField()
    # Unique ID from Dhan
    dhan_order_id = models.CharField(max_length=50, blank=True, null=True, unique=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        # We assume only one open position per symbol/strategy for simplicity
        unique_together = (('strategy', 'symbol', 'status'),)

    def __str__(self):
        return f"{self.strategy.name} - {self.symbol} ({self.status})"