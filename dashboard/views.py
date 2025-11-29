import csv
import io
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
import redis
import json
import time
import requests
from typing import Dict, Optional, Any
from django.db import transaction

# --- Model and Form Imports ---
from .models import DhanCredentials, StrategySettings, CashBreakoutTrade 
from .forms import DhanCredentialsForm, StrategySettingsForm, InstrumentUploadForm

# --- Global Redis Connection ---
# We use a global variable 'r' and initialize it once, ensuring SSL skip for Heroku Redis
r = None
try:
    r = redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)
    r.ping()
except Exception as e:
    print(f"CRITICAL REDIS CONNECTION ERROR: {e}. Dashboard functionality limited.")

# --- Dhan SDK Client Helper ---
def get_dhan_rest_client(client_id: str, access_token: str) -> Optional[object]:
    """Initializes the Dhan REST client robustly, handling import version differences."""
    if not access_token or not client_id:
        return None
    
    try:
        # Preferred/documented v2 import
        from dhanhq import DhanContext, dhanhq 
        dhan_context = DhanContext(client_id, access_token) 
        dhan = dhanhq(dhan_context)
        return dhan
    except ImportError:
        # This fallback is for safety, but the primary import structure should be relied upon
        try:
            import dhanhq
            dhan = dhanhq.dhanhq(client_id, access_token)
            return dhan
        except Exception as e:
            print(f"Dhan Client Initialization Failed: {e}")
            return None
    except Exception as e:
        print(f"Dhan Client Initialization Failed (Invalid Token/Context): {e}")
        return None


# --- CSV Handling Helper (Uses specific CSV headers) ---
def _process_uploaded_csv(csv_file) -> Dict[str, Dict[str, str]]:
    """
    Reads the uploaded Dhan Scrip Master CSV, filters for Nifty 500,
    and returns a map: {SYMBOL_NAME: {security_id, exchange_segment, symbol}}.
    """
    instrument_map: Dict[str, Dict[str, str]] = {}
    
    # Read the file content
    file_data = csv_file.read().decode('utf-8')
    f = io.StringIO(file_data)
    reader = csv.DictReader(f)
    
    target_symbols = set(settings.NIFTY_500_STOCKS)

    for row in reader:
        try:
            # Use the exact uppercase column names identified from the CSV provided by the user
            symbol = row['SYMBOL_NAME'] 
            security_id = row['SECURITY_ID']
            exchange_segment = row['SEGMENT'] # Using SEGMENT as the exchange segment identifier
            
            if symbol and security_id and exchange_segment and symbol in target_symbols:
                instrument_map[symbol] = {
                    'security_id': str(security_id),
                    'exchange_segment': exchange_segment,
                    'symbol': symbol,
                }
        except KeyError:
            # Handle cases where expected headers might be missing (should be rare with known CSV structure)
            continue
        except Exception:
            # Skip invalid rows
            continue
            
    return instrument_map


# --- Main Views ---

def dashboard_view(request):
    """Main dashboard for credentials, settings, and trade monitoring."""
    global r

    # 1. Ensure Strategy Settings exist
    try:
        strategy, created = StrategySettings.objects.get_or_create(
            name='Cash Breakout Strategy',
            defaults={
                'is_enabled': False,
                'name': 'Cash Breakout Strategy',
            }
        )
    except Exception as e:
        messages.error(request, f"Database Error during initialization. Run migrations: {e}")
        strategy = None 
        return render(request, 'dashboard/index.html', {'error_message': 'Critical Database Error: Tables not found.'})

    # 2. Handle Credentials Management
    try:
        credentials = DhanCredentials.objects.get(is_active=True)
    except DhanCredentials.DoesNotExist:
        credentials = DhanCredentials(client_id=settings.DHAN_CLIENT_ID or 'Enter Client ID')
    
    
    # --- POST Handlers ---
    if request.method == 'POST':
        
        # A. Handle CSV Upload and Instrument Caching
        if 'upload_instruments' in request.POST:
            upload_form = InstrumentUploadForm(request.POST, request.FILES)
            if upload_form.is_valid() and request.FILES.get('instrument_csv'):
                try:
                    instrument_map = _process_uploaded_csv(request.FILES['instrument_csv'])
                    
                    if not instrument_map:
                        messages.error(request, "CSV processing failed: Could not find any matching Nifty 500 symbols.")
                    elif r:
                        r.set(settings.SYMBOL_ID_MAP_KEY, json.dumps(instrument_map))
                        messages.success(request, f"Successfully cached {len(instrument_map)} Nifty instruments to Redis.")
                    else:
                        messages.error(request, "Redis is unavailable. Cannot cache instrument map.")
                except Exception as e:
                    messages.error(request, f"CSV Upload Failed: {e}")
            else:
                messages.error(request, "Invalid form submission for instrument upload.")
            return redirect('dashboard')
            
        # B. Handle Credentials Update
        if 'update_credentials' in request.POST:
            form = DhanCredentialsForm(request.POST, instance=credentials)
            if form.is_valid():
                creds = form.save(commit=False)
                creds.is_active = True
                creds.save()
                messages.success(request, "Dhan Client ID updated.")
            else:
                messages.error(request, "Error saving credentials.")
            return redirect('dashboard')
            
        # C. Handle Manual Access Token Activation
        if 'activate_token' in request.POST:
            token_to_save = request.POST.get('manual_access_token', '').strip()
            
            if not token_to_save or token_to_save == credentials.access_token:
                messages.error(request, "Please paste a new, valid Access Token.")
                return redirect('dashboard')

            # --- Activation Logic ---
            credentials.access_token = token_to_save
            credentials.token_generation_time = timezone.now()
            credentials.save()
            
            # Publish token update to all workers and save to a persistent Redis key
            if r:
                r.set(settings.REDIS_DHAN_TOKEN_KEY, token_to_save)
                # Signal workers to re-initialize client
                r.publish(settings.REDIS_AUTH_CHANNEL, json.dumps({'action': 'TOKEN_REFRESH', 'token': token_to_save}))
            
            messages.success(request, f"Access Token activated and distributed to workers. Token: {token_to_save[:15]}...")
            return redirect('dashboard')

        # D. Handle Strategy Settings Update
        if 'update_strategy' in request.POST:
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
                # Fall through to re-render form with errors
        
        # E. Manual Trade Actions (Square Off / Cancel Entry)
        trade_id = request.POST.get('trade_id')
        if trade_id and r:
            try:
                trade = CashBreakoutTrade.objects.get(pk=trade_id)
                dhan = get_dhan_rest_client(credentials.client_id, credentials.access_token)
                
                if dhan:
                    if 'manual_square_off' in request.POST and trade.status == 'OPEN':
                        # Place Market SELL order to exit long position
                        response = dhan.place_order(
                            security_id=trade.security_id,
                            exchange_segment=dhan.NSE, # Assuming NSE equity for cash market
                            transaction_type=dhan.SELL,
                            quantity=abs(trade.quantity),
                            order_type=dhan.MARKET,
                            product_type=dhan.INTRA
                        )
                        if response.get('orderId'):
                            trade.status = 'PENDING_EXIT'
                            trade.exit_order_id = response['orderId']
                            trade.exit_reason = 'MANUAL SQUARE OFF'
                            trade.save()
                            messages.warning(request, f"Manual Square Off order placed for {trade.symbol}. Waiting for fill status.")
                        else:
                            messages.error(request, f"API Error squaring off {trade.symbol}: {response.get('message', 'Unknown')}")
                            
                    elif 'manual_cancel_entry' in request.POST and trade.status == 'PENDING_ENTRY' and trade.entry_order_id:
                        # Cancel the pending SLM entry order
                        response = dhan.cancel_order(trade.entry_order_id)
                        
                        if response.get('status') == 'success' or 'cancel order success' in response.get('message', '').lower():
                            trade.status = 'EXPIRED'
                            trade.exit_reason = 'MANUAL CANCELLED'
                            trade.save()
                            messages.success(request, f"Pending entry for {trade.symbol} cancelled.")
                        else:
                            messages.error(request, f"API Error cancelling {trade.symbol}: {response.get('message', 'Unknown')}")

                    # Notify algo engines to update state
                    r.publish(settings.REDIS_CONTROL_CHANNEL, json.dumps({'action': 'UPDATE_CONFIG'}))

                else:
                    messages.error(request, "Dhan Client not initialized. Check Access Token and Client ID.")

            except CashBreakoutTrade.DoesNotExist:
                messages.error(request, "Trade not found.")
            except Exception as e:
                messages.error(request, f"Manual Action Failed: {e}")
            
            return redirect('dashboard')
            
    # --- GET Context Preparation ---

    # Initialize forms based on current DB state
    form = DhanCredentialsForm(instance=credentials)
    strategy_form = StrategySettingsForm(instance=strategy)
    upload_form = InstrumentUploadForm() # Always fresh for GET request
    
    # Live Trade Status and Monitoring
    live_trades = CashBreakoutTrade.objects.filter(
        status__in=['PENDING_ENTRY', 'OPEN', 'PENDING_EXIT']
    ).order_by('-created_at')
    
    # Global Status Check (from Redis)
    data_engine_status = r.get(settings.REDIS_STATUS_DATA_ENGINE) if r else 'N/A (Redis Down)'
    algo_engine_status = r.get(settings.REDIS_STATUS_ALGO_ENGINE) if r else 'N/A (Redis Down)'
    
    context = {
        'form': form,
        'credentials': credentials,
        'strategy_form': strategy_form,
        'upload_form': upload_form,
        'live_trades': live_trades,
        'data_engine_status': data_engine_status,
        'algo_engine_status': algo_engine_status,
    }
    return render(request, 'dashboard/index.html', context)