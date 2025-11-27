from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from datetime import datetime
import redis
import json
import time
import requests
from typing import Optional, Dict, Any
import logging

# --- FIX: Robust/Lazy Import of Dhan SDK components ---
# Import the client function and context conditionally to prevent module-level crashes
try:
    from dhanhq import DhanContext, dhanhq, DhanHQ # Attempt to import all necessary classes
except ImportError:
    # Define placeholder class/function if import fails early (used by get_dhan_rest_client)
    class DhanContext:
        def __init__(self, client_id, access_token):
            self.client_id = client_id
            self.access_token = access_token
    dhanhq = lambda ctx: None
    DhanHQ = lambda client_id, access_token: None # Placeholder for older versions

# --- Import Models and Forms ---
from .models import DhanCredentials, StrategySettings, CashBreakoutTrade 
from .forms import DhanCredentialsForm, StrategySettingsForm

logger = logging.getLogger(__name__)

# Initialize Redis connection (read-only for dashboard status)
def initialize_redis():
    """Initializes Redis connection with Heroku SSL fix."""
    try:
        # CRITICAL FIX: Add ssl_cert_reqs=None and decode_responses=True for Heroku Redis SSL connection
        r = redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)
        r.ping()
        return r
    except Exception as e:
        logger.error(f"REDIS CONNECTION ERROR: {e}")
        return None 

r = initialize_redis()

# --- Global Helper for Dhan Client Initialization (LAZY IMPORT + FALLBACK) ---
def get_dhan_rest_client(client_id: str, access_token: str) -> Optional[object]:
    """Initializes and returns the Dhan REST client using the most compatible pattern."""
    dhan = None
    try:
        # Re-import inside function body to catch any post-startup installs
        from dhanhq import DhanContext, dhanhq 
        dhan_context = DhanContext(client_id, access_token) 
        dhan = dhanhq(dhan_context) 
        return dhan
    except Exception as e:
        logger.error(f"Dhan Client Initialization FAILED: {e}")
        return None

# --- Core Token Exchange Logic ---

def exchange_token_id_for_access_token(client_id: str, token_id: str) -> Optional[str]:
    """
    Simulates the REST API call to exchange the temporary tokenId for the 
    permanent access_token, using the client_id and API_SECRET.
    
    NOTE: Dhan's actual API URL for token exchange is used here for concept.
    """
    api_secret = settings.DHAN_API_SECRET
    
    if not api_secret:
        logger.error("DHAN_API_SECRET not set in environment variables. Cannot exchange token.")
        return None

    # This is the actual endpoint for token generation in Dhan's flow
    TOKEN_EXCHANGE_URL = "https://api.dhan.co/access_token"
    
    headers = {
        'Content-Type': 'application/json',
    }
    payload = {
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'client_secret': api_secret,
        'token_id': token_id, 
        # Note: Some brokers might require 'redirect_uri' even here
    }
    
    try:
        response = requests.post(TOKEN_EXCHANGE_URL, headers=headers, json=payload)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        
        # Check if the API returned the token structure successfully
        if 'access_token' in data and data.get('status') == 'success':
            logger.info("Successfully exchanged Token ID for Access Token.")
            return data['access_token']
        elif 'message' in data:
            logger.error(f"Dhan API Exchange Failed: {data.get('message')}")
            return None
        else:
            logger.error(f"Dhan API Exchange Failed with unexpected response: {data}")
            return None

    except requests.exceptions.RequestException as e:
        logger.critical(f"Token Exchange REST Call Failed: {e}")
        return None

# --- Django Views ---

def dashboard_view(request):
    """Main dashboard for credentials, settings, and trade monitoring."""
    global r
    if r is None: r = initialize_redis() # Try reconnecting redis if down
    
    # 1. Strategy Settings (Critical for app load, handles initial setup)
    try:
        strategy, created = StrategySettings.objects.get_or_create(
            name='Cash Breakout Strategy',
            defaults={
                'is_enabled': False,
                'name': 'Cash Breakout Strategy',
            }
        )
    except Exception as e:
        logger.critical(f"DATABASE ERROR during StrategySettings lookup: {e}")
        return render(request, 'dashboard/index.html', {'error_message': f"Critical DB Error: Tables missing ({e}). Run migrations."})

    # 2. Handle Credentials Management (Save Client ID)
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

    # 3. Handle Strategy Settings Update
    if request.method == 'POST' and 'update_strategy' in request.POST:
        strategy_form = StrategySettingsForm(request.POST, instance=strategy)
        if strategy_form.is_valid():
            strategy_form.save()
            messages.success(request, f"Strategy '{strategy.name}' settings updated.")
            
            # NOTIFY ALGO ENGINES VIA REDIS
            if r:
                r.publish(settings.REDIS_CONTROL_CHANNEL, json.dumps({'action': 'UPDATE_CONFIG'}))
            
            return redirect('dashboard')
        else:
            messages.error(request, "Error saving strategy settings.")
    else:
        strategy_form = StrategySettingsForm(instance=strategy)


    # 4. Live Trade Status and Monitoring
    live_trades = CashBreakoutTrade.objects.filter(
        status__in=['PENDING_ENTRY', 'OPEN', 'PENDING_EXIT']
    ).order_by('-created_at')
    
    # 5. Global Status Check (from Redis)
    data_engine_status = r.get(settings.REDIS_STATUS_DATA_ENGINE) if r else 'N/A (Redis Down)'
    algo_engine_status = r.get(settings.REDIS_STATUS_ALGO_ENGINE) if r else 'N/A (Redis Down)'
    
    context = {
        'form': form,
        'credentials': credentials,
        'strategy_form': strategy_form,
        'live_trades': live_trades,
        'data_engine_status': data_engine_status,
        'algo_engine_status': algo_engine_status,
        'dhan_auth_url': f"https://api.dhan.co/auth/signin?client_id={credentials.client_id}&redirect_uri={settings.DHAN_REDIRECT_URI}&state={credentials.client_id}",
    }
    return render(request, 'dashboard/index.html', context)


def dhan_callback_view(request):
    """
    Handles the redirect from the Dhan authorization flow. 
    Exchanges the temporary tokenId (auth code) for the permanent access_token.
    """
    global r
    if r is None: r = initialize_redis()

    token_id = request.GET.get('tokenId')
    client_id = request.GET.get('client_id') # Dhan often returns the client_id/state
    
    if not token_id:
        messages.error(request, "Dhan login failed or did not return a tokenId (authorization code).")
        return redirect('dashboard')

    try:
        credentials = DhanCredentials.objects.get(client_id=client_id, is_active=True)
    except DhanCredentials.DoesNotExist:
        messages.error(request, f"Client ID {client_id} not found or inactive.")
        return redirect('dashboard')
        
    # --- STEP 1: Exchange tokenId for Access Token (REST API Call) ---
    new_access_token = exchange_token_id_for_access_token(credentials.client_id, token_id)

    if new_access_token:
        # --- STEP 2: Save & Distribute Live Token ---
        credentials.access_token = new_access_token
        credentials.token_generation_time = timezone.now()
        credentials.save()
        
        # Publish token update to all workers (Data and Algo dynos)
        if r:
            r.set(settings.REDIS_DHAN_TOKEN_KEY, new_access_token)
            r.publish(settings.REDIS_AUTH_CHANNEL, json.dumps({'action': 'TOKEN_REFRESH', 'token': new_access_token}))
        
        messages.success(request, f"LIVE Access Token acquired and distributed. Ready for trading!")
    else:
        messages.error(request, "Failed to exchange Authorization Code (tokenId) for live Access Token. Check API Secret/Dhan logs.")

    return redirect('dashboard')