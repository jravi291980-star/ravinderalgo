from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
import redis
import json
import time
import requests
import logging
from typing import Optional, Dict, Any

# --- Robust/Lazy Import of Dhan SDK components ---
# Import the client function and context conditionally to prevent module-level crashes
try:
    from dhanhq import DhanContext, dhanhq 
except ImportError:
    # Define placeholder class/function if import fails early 
    class DhanContext:
        def __init__(self, client_id, access_token):
            self.client_id = client_id
            self.access_token = access_token
    dhanhq = lambda ctx: None

# --- Import Models and Forms ---
from .models import DhanCredentials, StrategySettings, CashBreakoutTrade 
from .forms import DhanCredentialsForm, StrategySettingsForm

logger = logging.getLogger(__name__)

# --- Global Redis Connection ---
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

# --- Dhan SDK Client Helper ---
def get_dhan_rest_client(client_id: str, access_token: str) -> Optional[object]:
    """Initializes and returns the Dhan REST client using the most compatible pattern."""
    if not access_token or not client_id:
        return None
    
    try:
        # Preferred/documented v2 import
        from dhanhq import DhanContext, dhanhq 
        dhan_context = DhanContext(client_id, access_token) 
        dhan = dhanhq(dhan_context) 
        return dhan
    except ImportError:
        # Fallback import for older library versions
        try:
            import dhanhq
            dhan = dhanhq.dhanhq(client_id, access_token)
            return dhan
        except Exception as e:
            logger.error(f"Dhan Client Initialization Failed (Fallback): {e}")
            return None
    except Exception as e:
        logger.error(f"Dhan Client Initialization Failed (Context): {e}")
        return None


# --- Main Views ---

def dashboard_view(request):
    """Main dashboard for credentials, settings, and trade monitoring."""
    global r
    if r is None: r = initialize_redis() # Retry connection if it failed previously

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
        logger.critical(f"DATABASE ERROR during StrategySettings lookup: {e}")
        return render(request, 'dashboard/index.html', {'error_message': f"Critical DB Error: Tables missing ({e}). Run migrations."})

    # 2. Handle Credentials Management (Single Instance Persistence)
    # We use .first() or get_or_create to ensure we always edit the SAME credentials object
    credentials = DhanCredentials.objects.first()
    if not credentials:
        credentials = DhanCredentials.objects.create(client_id=settings.DHAN_CLIENT_ID or 'Enter Client ID')

    
    # --- POST Handler ---
    if request.method == 'POST':
        
        # A. Handle Credentials / Manual Token Activation
        # We check specific button names to know which action to take
        
        if 'update_credentials' in request.POST:
            form = DhanCredentialsForm(request.POST, instance=credentials)
            if form.is_valid():
                form.save()
                messages.success(request, "Dhan Client ID updated.")
            else:
                messages.error(request, "Error saving credentials.")
            return redirect('dashboard')

        elif 'activate_token' in request.POST:
            # Manual Token Activation Logic
            manual_token = request.POST.get('manual_access_token', '').strip()
            
            if not manual_token:
                messages.error(request, "Please paste a valid Access Token.")
                return redirect('dashboard')

            # 1. Update Database
            credentials.access_token = manual_token
            credentials.token_generation_time = timezone.now()
            credentials.save()
            
            # 2. Distribute to Workers via Redis
            if r:
                # Save to persistent key for workers to read on startup
                r.set(settings.REDIS_DHAN_TOKEN_KEY, manual_token)
                # Publish event for running workers to hot-reload
                r.publish(settings.REDIS_AUTH_CHANNEL, json.dumps({
                    'action': 'TOKEN_REFRESH', 
                    'token': manual_token
                }))
            
            messages.success(request, f"Trading session activated! Token distributed to workers.")
            return redirect('dashboard')

        # B. Handle Strategy Settings Update
        elif 'update_strategy' in request.POST:
            strategy_form = StrategySettingsForm(request.POST, instance=strategy)
            if strategy_form.is_valid():
                strategy_form.save()
                messages.success(request, f"Strategy '{strategy.name}' settings updated.")
                
                # Notify Algo Engine via Redis to reload settings
                if r:
                    r.publish(settings.REDIS_CONTROL_CHANNEL, json.dumps({'action': 'UPDATE_CONFIG'}))
                
                return redirect('dashboard')
            else:
                messages.error(request, "Error saving strategy settings.")
        
        # C. Manual Trade Actions (Square Off / Cancel Entry)
        elif 'manual_square_off' in request.POST or 'manual_cancel_entry' in request.POST:
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
                                exchange_segment=dhan.NSE, 
                                transaction_type=dhan.SELL,
                                quantity=abs(trade.quantity),
                                order_type=dhan.MARKET,
                                product_type=dhan.INTRA,
                                price=0
                            )
                            
                            if response.get('orderId'):
                                trade.status = 'PENDING_EXIT'
                                trade.exit_order_id = response['orderId']
                                trade.exit_reason = 'MANUAL SQUARE OFF'
                                trade.save()
                                messages.warning(request, f"Manual Square Off order placed for {trade.symbol}.")
                            else:
                                err_msg = response.get('message', 'Unknown Error')
                                messages.error(request, f"API Error squaring off {trade.symbol}: {err_msg}")
                                
                        elif 'manual_cancel_entry' in request.POST and trade.status == 'PENDING_ENTRY' and trade.entry_order_id:
                            # Cancel the pending SLM entry order
                            response = dhan.cancel_order(trade.entry_order_id)
                            
                            if response.get('status') == 'success' or 'success' in str(response).lower():
                                trade.status = 'EXPIRED'
                                trade.exit_reason = 'MANUAL CANCELLED'
                                trade.save()
                                messages.success(request, f"Pending entry for {trade.symbol} cancelled.")
                            else:
                                messages.error(request, f"API Error cancelling {trade.symbol}: {response}")

                        # Notify algo engines to update their internal state immediately
                        r.publish(settings.REDIS_CONTROL_CHANNEL, json.dumps({'action': 'UPDATE_CONFIG'}))

                    else:
                        messages.error(request, "Dhan Client not initialized. Check Access Token.")

                except CashBreakoutTrade.DoesNotExist:
                    messages.error(request, "Trade not found.")
                except Exception as e:
                    messages.error(request, f"Manual Action Failed: {e}")
            
            return redirect('dashboard')

    # --- GET Request Context Preparation ---

    # Initialize forms with current DB instances
    form = DhanCredentialsForm(instance=credentials)
    strategy_form = StrategySettingsForm(instance=strategy)
    
    # Live Trade Monitoring (Latest first)
    live_trades = CashBreakoutTrade.objects.filter(
        status__in=['PENDING_ENTRY', 'OPEN', 'PENDING_EXIT']
    ).order_by('-created_at')
    
    # Global Status Check (from Redis keys set by workers)
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