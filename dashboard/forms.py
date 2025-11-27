from django import forms
from .models import DhanCredentials, StrategySettings

class DhanCredentialsForm(forms.ModelForm):
    """Form to input and update Dhan API credentials."""
    class Meta:
        model = DhanCredentials
        fields = ['client_id', 'api_key'] # api_key is used here for the full key/token

class StrategySettingsForm(forms.ModelForm):
    """Form to update the strategy settings."""
    class Meta:
        model = StrategySettings
        # Exclude read-only fields or IDs, include all adjustable parameters
        fields = ['name', 'strategy_type', 'is_enabled', 'symbol', 'quantity',
                  'take_profit_percent', 'stop_loss_percent', 'manual_override']