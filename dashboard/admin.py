from django.contrib import admin
from .models import DhanCredentials, StrategySettings, CashBreakoutTrade

@admin.register(DhanCredentials)
class DhanCredentialsAdmin(admin.ModelAdmin):
    list_display = ('client_id', 'is_active', 'token_status', 'token_generation_time')
    readonly_fields = ('token_generation_time',)
    list_filter = ('is_active',)
    search_fields = ('client_id',)

    def token_status(self, obj):
        if obj.access_token:
            return "Token Present"
        return "No Token"
    token_status.short_description = "Access Token Status"

@admin.register(StrategySettings)
class StrategySettingsAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_enabled', 'manual_override', 'max_total_trades', 'pnl_exit_enabled')
    list_editable = ('is_enabled', 'manual_override')
    fieldsets = (
        ('Master Controls', {
            'fields': ('name', 'strategy_type', 'is_enabled', 'manual_override')
        }),
        ('Risk & Limits', {
            'fields': ('max_trades_per_stock', 'max_total_trades', 'per_trade_sl_amount')
        }),
        ('Entry & Exit Logic', {
            'fields': ('entry_offset_pct', 'stop_offset_pct', 'max_candle_pct')
        }),
        ('Time & PnL Limits', {
            'fields': ('start_time', 'end_time', 'pnl_exit_enabled', 'pnl_profit_target', 'pnl_stop_loss')
        }),
    )

@admin.register(CashBreakoutTrade)
class CashBreakoutTradeAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'status', 'quantity', 'entry_price', 'pnl', 'created_at')
    list_filter = ('status', 'created_at', 'strategy')
    search_fields = ('symbol', 'entry_order_id', 'exit_order_id')
    readonly_fields = ('created_at', 'candle_ts', 'entry_time', 'exit_time', 'entry_order_id', 'exit_order_id')
    
    fieldsets = (
        ('Trade Info', {
            'fields': ('strategy', 'symbol', 'security_id', 'status', 'exit_reason')
        }),
        ('Quantity & PnL', {
            'fields': ('quantity', 'pnl')
        }),
        ('Planned Levels', {
            'fields': ('entry_level', 'stop_level', 'target_level', 'prev_day_high')
        }),
        ('Execution Details', {
            'fields': ('entry_price', 'exit_price', 'entry_order_id', 'exit_order_id')
        }),
        ('Timestamps', {
            'fields': ('candle_ts', 'entry_time', 'exit_time', 'created_at')
        }),
        ('Candle Data (Debug)', {
            'fields': ('candle_high', 'candle_low', 'volume_price'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ('-created_at',)