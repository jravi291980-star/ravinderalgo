import csv
import io
import json
import logging
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any

import redis
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone

# Import requests for making HTTP requests (used by CSV upload)
import requests 

# --- FIX: Robust/Lazy Import of Dhan SDK components ---
# Import the client function and context conditionally to prevent module-level crashes
try:
    from dhanhq import DhanContext, dhanhq
except ImportError:
    # Define placeholder class/function if import fails early 
    class DhanContext:
        def __init__(self, client_id, access_token): pass
    dhanhq = lambda ctx: None
    
# --- Import Models and Forms ---
from .models import DhanCredentials, StrategySettings, CashBreakoutTrade 
from .forms import DhanCredentialsForm, StrategySettingsForm

logger = logging.getLogger(__name__)

# --- Redis Initialization ---
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

# --- Django Views ---

def dashboard_view(request):
    """Main dashboard for credentials, settings, and trade monitoring, and all POST handlers."""
    global r
    if r is None: r = initialize_redis() # Try reconnecting redis if down
    
    # 1. Strategy Settings (Critical for app load, handles initial setup)
    try:
        strategy, created = StrategySettings.objects.get_or_create(
            name='Cash Breakout Strategy',
            defaults={'is_enabled': False, 'name': 'Cash Breakout Strategy'}
        )
    except Exception as e:
        logger.critical(f"DATABASE ERROR during StrategySettings lookup: {e}")
        return render(request, 'dashboard/index.html', {'error_message': f"Critical DB Error: Tables missing ({e}). Run migrations."})

    # 2. Handle Credentials Management
    try:
        credentials = DhanCredentials.objects.get(is_active=True)
    except DhanCredentials.DoesNotExist:
        credentials = DhanCredentials(client_id=settings.DHAN_CLIENT_ID or 'Enter Client ID')

    # --- POST Handlers ---
    if request.method == 'POST':
        form = DhanCredentialsForm(request.POST, instance=credentials)
        
        if 'update_credentials' in request.POST:
            # Handler for saving Client ID
            if form.is_valid():
                creds = form.save(commit=False)
                creds.is_active = True
                creds.save()
                messages.success(request, "Dhan Client ID updated.")
                return redirect('dashboard')
            else:
                messages.error(request, "Error saving credentials.")

        elif 'activate_token' in request.POST:
            # Handler for Manual Token Activation
            manual_token = request.POST.get('manual_access_token')
            client_id = request.POST.get('client_id')
            
            if not manual_token or not client_id:
                messages.error(request, "Client ID and Access Token must be provided for activation.")
                return redirect('dashboard')
            
            # 1. Save Token to DB
            credentials.access_token = manual_token.strip()
            credentials.token_generation_time = timezone.now()
            credentials.client_id = client_id.strip() 
            credentials.save()
            
            # 2. Distribute Token via Redis
            if r:
                r.set(settings.REDIS_DHAN_TOKEN_KEY, credentials.access_token)
                r.publish(settings.REDIS_AUTH_CHANNEL, json.dumps({
                    'action': 'TOKEN_REFRESH', 
                    'token': credentials.access_token
                }))
                
            messages.success(request, "Trading session activated! Token distributed to workers.")
            return redirect('dashboard')
            
        elif 'update_strategy' in request.POST:
            # Handler for Strategy Settings Update
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
                
        elif 'upload_instruments' in request.POST:
            # --- Handler for CSV Instrument Upload and Caching ---
            if 'instrument_csv' not in request.FILES:
                messages.error(request, "No CSV file was uploaded.")
                return redirect('dashboard')

            csv_file = request.FILES['instrument_csv']
            
            if not csv_file.name.endswith('.csv'):
                messages.error(request, "File must be a CSV format.")
                return redirect('dashboard')

            try:
                # Read file content into a string buffer
                file_data = csv_file.read().decode('utf-8')
                io_string = io.StringIO(file_data)
                
                # Use Django's settings list for filtering
                target_symbols = set(settings.NIFTY_500_STOCKS) 
                instrument_map: Dict[str, Dict[str, str]] = {}
                
                # Use DictReader for easy column access
                reader = csv.DictReader(io_string)

                for row in reader:
                    # Robustly handle common field names from Dhan CSV
                    symbol = row.get("tradingSymbol") or row.get("symbol")
                    security_id = row.get("securityId") or row.get("security_id")
                    exchange_segment = row.get("exchangeSegment") or row.get("exchange_segment")

                    if symbol and security_id and exchange_segment and symbol in target_symbols:
                        instrument_map[symbol] = {
                            "security_id": str(security_id),
                            "exchange_segment": exchange_segment,
                            "symbol": symbol,
                        }
                
                if instrument_map and r:
                    # Cache Results in Redis
                    r.set(settings.SYMBOL_ID_MAP_KEY, json.dumps(instrument_map))
                    messages.success(request, f"Successfully cached {len(instrument_map)} Nifty instruments from CSV!")
                    
                    # Log missing symbols for user feedback (optional)
                    missing_count = len(target_symbols) - len(instrument_map)
                    if missing_count > 0:
                        messages.warning(request, f"{missing_count} symbols from the Nifty list were not found in the CSV.")

                elif not instrument_map:
                    messages.error(request, "CSV processing failed: Could not find any matching Nifty 500 symbols.")
                    
            except Exception as e:
                logger.error(f"CSV Processing Error: {e}")
                messages.error(request, f"Failed to process CSV file: {e}")
                
            return redirect('dashboard')

    else: # GET request
        form = DhanCredentialsForm(instance=credentials)
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
        # NOTE: The instrument upload form is handled by the main POST, but we need
        # the forms defined for successful GET rendering.
    }
    return render(request, 'dashboard/index.html', context)