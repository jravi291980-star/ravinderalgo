from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
import redis
import json
import time

# --- FIX: Renamed LiveTrade to CashBreakoutTrade ---
from .models import DhanCredentials, StrategySettings, CashBreakoutTrade
from .forms import DhanCredentialsForm, StrategySettingsForm

# Initialize Redis connection (read-only for dashboard status)
try:
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception as e:
    print(f"REDIS CONNECTION ERROR (Dashboard): {e}")
    r = None


def dashboard_view(request):
    """Main dashboard for credentials, settings, and trade monitoring."""

    # 1. Ensure Strategy Settings exist
    strategy, created = StrategySettings.objects.get_or_create(
        name='Cash Breakout Strategy',
        defaults={'is_enabled': False}
    )

    # 2. Handle Credentials Management
    try:
        credentials = DhanCredentials.objects.get(is_active=True)
    except DhanCredentials.DoesNotExist:
        credentials = DhanCredentials(client_id=settings.DHAN_CLIENT_ID or 'Enter Client ID')

    if request.method == 'POST' and 'update_credentials' in request.POST:
        form = DhanCredentialsForm(request.POST, instance=credentials)
        if form.is_valid():
            creds = form.save(commit=False)
            creds.is_active = True
            creds.save()
            messages.success(request, "Dhan Client ID updated.")
            return redirect('dashboard')
        else:
            messages.error(request, "Error saving credentials.")
    else:
        form = DhanCredentialsForm(instance=credentials)

    # 3. Handle Strategy Settings
    if request.method == 'POST' and 'update_strategy' in request.POST:
        strategy_form = StrategySettingsForm(request.POST, instance=strategy)
        if strategy_form.is_valid():
            strategy_form.save()
            messages.success(request, f"Strategy '{strategy.name}' settings updated.")

            # --- NOTIFY ALGO ENGINES VIA REDIS ---
            if r:
                r.publish(settings.REDIS_CONTROL_CHANNEL, json.dumps({
                    'action': 'UPDATE_CONFIG'
                }))

            return redirect('dashboard')
        else:
            messages.error(request, "Error saving strategy settings.")
    else:
        strategy_form = StrategySettingsForm(instance=strategy)

    # 4. Token Generation (Placeholder function)
    if request.method == 'POST' and 'generate_token' in request.POST and credentials.client_id:
        # In a real app, this requires a REST call to Dhan to generate the token

        if not credentials.client_id or credentials.client_id == 'Enter Client ID':
            messages.error(request, "Please enter a valid Client ID before attempting token generation.")
        else:
            # --- MOCK TOKEN GENERATION & DISTRIBUTION ---
            new_token = f"DHAN_MOCK_TOKEN_{int(time.time())}"
            credentials.access_token = new_token
            credentials.token_generation_time = timezone.now()
            credentials.save()

            # Publish token update to all workers
            if r:
                r.set(settings.REDIS_DHAN_TOKEN_KEY, new_token)
                r.publish(settings.REDIS_AUTH_CHANNEL, json.dumps({'action': 'TOKEN_REFRESH', 'token': new_token}))

            messages.success(request, f"Access Token generated and distributed to workers. Token: {new_token[:10]}...")
        return redirect('dashboard')

    # 5. Live Trade Status and Monitoring
    # --- FIX: Using CashBreakoutTrade model ---
    live_trades = CashBreakoutTrade.objects.filter(
        status__in=['PENDING_ENTRY', 'OPEN', 'PENDING_EXIT']
    ).order_by('-created_at')

    # 6. Global Status Check (from Redis)
    data_engine_status = r.get(settings.REDIS_STATUS_DATA_ENGINE) if r else 'N/A'
    algo_engine_status = r.get(settings.REDIS_STATUS_ALGO_ENGINE) if r else 'N/A'

    context = {
        'form': form,
        'credentials': credentials,
        'strategy_form': strategy_form,
        'live_trades': live_trades,
        'data_engine_status': data_engine_status,
        'algo_engine_status': algo_engine_status,
    }
    return render(request, 'dashboard/index.html', context)