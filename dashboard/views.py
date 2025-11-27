from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib import messages
from .models import DhanCredentials, StrategySettings, LiveTrade
from .forms import DhanCredentialsForm, StrategySettingsForm
import redis
import json
import time

# Initialize Redis connection for reading/writing status
try:
    # Use the REDIS_URL from settings
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception as e:
    # Handle connection error gracefully
    print(f"REDIS CONNECTION ERROR: {e}")
    r = None  # Set to None if connection fails


def dashboard_view(request):
    """Main dashboard for credentials, settings, and trade monitoring."""

    # 1. Handle Credentials Management
    try:
        credentials = DhanCredentials.objects.get(is_active=True)
    except DhanCredentials.DoesNotExist:
        credentials = None

    if request.method == 'POST' and 'update_credentials' in request.POST:
        if credentials:
            form = DhanCredentialsForm(request.POST, instance=credentials)
        else:
            form = DhanCredentialsForm(request.POST)

        if form.is_valid():
            creds = form.save(commit=False)
            creds.is_active = True
            creds.save()
            messages.success(request, "Dhan Credentials updated successfully.")
            return redirect('dashboard')
        else:
            messages.error(request, "Error saving credentials.")
    else:
        form = DhanCredentialsForm(instance=credentials)

    # 2. Handle Strategy Settings
    try:
        strategy = StrategySettings.objects.get(name='MY_FIRST_ALGO')
    except StrategySettings.DoesNotExist:
        # Create a default strategy instance if it doesn't exist
        strategy = StrategySettings.objects.create(name='MY_FIRST_ALGO')

    if request.method == 'POST' and 'update_strategy' in request.POST:
        strategy_form = StrategySettingsForm(request.POST, instance=strategy)
        if strategy_form.is_valid():
            strategy_form.save()
            messages.success(request, f"Strategy '{strategy.name}' settings updated.")

            # --- NOTIFY ALGO ENGINES VIA REDIS ---
            if r:
                r.publish('strategy_control_channel', json.dumps({
                    'strategy_id': strategy.id,
                    'action': 'UPDATE_CONFIG'
                }))

            return redirect('dashboard')
        else:
            messages.error(request, "Error saving strategy settings.")
    else:
        strategy_form = StrategySettingsForm(instance=strategy)

    # 3. Live Trade Status and Monitoring
    live_trades = LiveTrade.objects.filter(status__in=['PENDING', 'OPEN']).order_by('-timestamp')

    # 4. Global Status Check (from Redis)
    data_engine_status = r.get('data_engine_status') if r else 'N/A'
    algo_engine_status = r.get('algo_engine_status') if r else 'N/A'

    # 5. Token Generation (Placeholder function)
    if request.method == 'POST' and 'generate_token' in request.POST and credentials:
        # NOTE: In a real app, this would trigger a background task
        # using the dhanhq library to generate/refresh the access_token
        # using the credentials.

        # Placeholder logic:
        new_token = f"TOKEN-{int(time.time())}"  # Mock token
        credentials.access_token = new_token
        credentials.token_generation_time = timezone.now()
        credentials.save()

        # Publish token update to all workers
        if r:
            r.set('dhan_access_token', new_token)
            r.publish('auth_channel', json.dumps({'action': 'TOKEN_REFRESH', 'token': new_token}))

        messages.success(request, f"Access Token generated and distributed to workers.")
        return redirect('dashboard')

    context = {
        'form': form,
        'credentials': credentials,
        'strategy_form': strategy_form,
        'live_trades': live_trades,
        'data_engine_status': data_engine_status,
        'algo_engine_status': algo_engine_status,
    }
    return render(request, 'dashboard/index.html', context)


# Remember to import timezone if needed for token generation:
from django.utils import timezone