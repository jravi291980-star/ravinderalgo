from django import forms
from .models import DhanCredentials, StrategySettings

class DhanCredentialsForm(forms.ModelForm):
    """
    Form to input Dhan Client ID and display the Access Token status.
    This version includes a field for pasting the manually generated Access Token.
    """
    
    # NEW FIELD: Field for pasting the manually generated Access Token
    manual_access_token = forms.CharField(
        max_length=512, 
        required=False, 
        label="Paste 24hr Access Token Here",
        help_text="Generate the token from the Dhan Developer Portal and paste it here."
    )

    class Meta:
        model = DhanCredentials
        fields = ['client_id', 'access_token'] 
        widgets = {
            # Keep access_token field read-only for display purposes
            'access_token': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'bg-gray-100 cursor-not-allowed', 'placeholder': 'Paste token above and click generate.'}),
        }

class StrategySettingsForm(forms.ModelForm):
    """Form to update the main strategy settings."""
    class Meta:
        model = StrategySettings
        fields = [
            'name', 
            'is_enabled', 
            'manual_override',
            'max_trades_per_stock', 
            'max_total_trades',
            'per_trade_sl_amount', 
            'entry_offset_pct', 
            'stop_offset_pct', 
            'max_candle_pct',
            'start_time', 
            'end_time', 
            'pnl_exit_enabled',
            'pnl_profit_target',
            'pnl_stop_loss',
        ]
        widgets = {
            'start_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'end_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
        }