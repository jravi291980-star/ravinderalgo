from django import forms
from .models import DhanCredentials, StrategySettings

class DhanCredentialsForm(forms.ModelForm):
    """
    Form to input Dhan Client ID and display the Access Token status.
    This version includes a dedicated field for pasting the manually generated Access Token.
    """
    
    # NEW FIELD: Field for pasting the manually generated Access Token (not saved to the model directly)
    manual_access_token = forms.CharField(
        max_length=512, 
        required=False, 
        label="Paste 24hr Access Token Here",
        help_text="Generate the token from the Dhan Developer Portal and paste it here. Click 'Activate' to distribute to workers."
    )

    class Meta:
        model = DhanCredentials
        # Fields must match existing Model fields
        fields = ['client_id', 'access_token'] 
        widgets = {
            # Keep access_token field read-only for display purposes
            'access_token': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'bg-gray-100 cursor-not-allowed', 'placeholder': 'Generated upon successful activation.'}),
        }

class StrategySettingsForm(forms.ModelForm):
    """Form to update the main strategy settings."""
    class Meta:
        model = StrategySettings
        fields = [
            # Master Controls
            'name', 
            'is_enabled', 
            'manual_override',
            
            # Limits
            'max_trades_per_stock', 
            'max_total_trades',
            
            # Risk & Filters
            'per_trade_sl_amount', 
            'entry_offset_pct', 
            'stop_offset_pct', 
            'max_candle_pct',
            
            # Time & P&L Exits
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

class InstrumentUploadForm(forms.Form):
    """
    Form dedicated to receiving the Dhan Scrip Master CSV file upload.
    This form does not use a Model as it only handles file input.
    """
    instrument_csv = forms.FileField(
        label="Dhan Scrip Master CSV",
        help_text="Upload the full scrip master file to map Nifty 500 symbols to required Security IDs.",
        widget=forms.FileInput(attrs={'accept': '.csv'})
    )