from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
import redis
import json
import time

# --- FIX: Using CashBreakoutTrade model instead of LiveTrade ---
from .models import DhanCredentials, StrategySettings, CashBreakoutTrade 
from .forms import DhanCredentialsForm, StrategySettingsForm

# Initialize Redis connection (read-only for dashboard status)
try:
    # CRITICAL FIX: Add ssl_cert_reqs=None and decode_responses=True for Heroku Redis SSL connection
    r = redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)
    # Ping to test connection immediately (this is where the previous error occurred)
    r.ping()
except Exception as e:
    print(f"REDIS CONNECTION ERROR (Dashboard): {e}")
    r = None 

def dashboard_view(request):
    """Main dashboard for credentials, settings, and trade monitoring."""
    
    # 1. Ensure Strategy Settings exist (Critical for app load, handles initial setup)
    try:
        strategy, created = StrategySettings.objects.get_or_create(
            name='Cash Breakout Strategy',
            defaults={
                'is_enabled': False,
                'name': 'Cash Breakout Strategy',
                # Populate other necessary fields based on defaults in models.py
            }
        )
    except Exception as e:
        # If this fails, it is highly likely the database migration failed.
        print(f"DATABASE ERROR during StrategySettings lookup: {e}")
        messages.error(request, f"Database table initialization failed. Run 'heroku run python manage.py migrate --app {settings.HEROKU_APP_NAME}'")
        strategy = None # Prevents further DB interaction if models fail to load

    if not strategy:
        # Render a simple error page if strategy object could not be retrieved
        return render(request, 'dashboard/index.html', {'error_message': 'Critical Database Error: Tables not found.'})


    # 2. Handle Credentials Management
    try:
        # Attempt to get the existing single credentials object
        credentials = DhanCredentials.objects.get(is_active=True)
    except DhanCredentials.DoesNotExist:
        # Create a new placeholder if none exists
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

    # 3. Handle Strategy Settings Update
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


    # 4. Token Generation Logic
    if request.method == 'POST' and 'generate_token' in request.POST and credentials.client_id:
        
        if not credentials.client_id or credentials.client_id == 'Enter Client ID':
            messages.error(request, "Please enter a valid Client ID before attempting token generation.")
        else:
            # NOTE: In a real environment, this function would involve a REST call to Dhan 
            # using the Client ID to exchange for a fresh Access Token.
            
            # --- MOCK TOKEN GENERATION & DISTRIBUTION ---
            new_token = f"DHAN_MOCK_TOKEN_{int(time.time())}_{credentials.client_id}" 
            credentials.access_token = new_token
            credentials.token_generation_time = timezone.now()
            credentials.save()
            
            # Publish token update to all workers and save to a persistent Redis key
            if r:
                r.set(settings.REDIS_DHAN_TOKEN_KEY, new_token)
                r.publish(settings.REDIS_AUTH_CHANNEL, json.dumps({'action': 'TOKEN_REFRESH', 'token': new_token}))
            
            messages.success(request, f"Access Token generated and distributed to workers. Token: {new_token[:15]}...")
        return redirect('dashboard')
        
    # 5. Live Trade Status and Monitoring
    live_trades = CashBreakoutTrade.objects.filter(
        status__in=['PENDING_ENTRY', 'OPEN', 'PENDING_EXIT']
    ).order_by('-created_at')
    
    # 6. Global Status Check (from Redis)
    data_engine_status = r.get(settings.REDIS_STATUS_DATA_ENGINE) if r else 'N/A (Redis Down)'
    algo_engine_status = r.get(settings.REDIS_STATUS_ALGO_ENGINE) if r else 'N/A (Redis Down)'
    
    context = {
        'form': form,
        'credentials': credentials,
        'strategy_form': strategy_form,
        'live_trades': live_trades,
        'data_engine_status': data_engine_status,
        'algo_engine_status': algo_engine_status,
    }
    return render(request, 'dashboard/index.html', context)