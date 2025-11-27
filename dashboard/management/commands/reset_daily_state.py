# dashboard/management/commands/reset_daily_state.py
import json
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from dashboard.models import CashBreakoutTrade  # Import the specific model
import redis


class Command(BaseCommand):
    help = 'Manually resets the daily Redis trading state (trade counters, active sets, PNL) and forces all trades to CLOSE in the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-db-close',
            action='store_true',
            help='Close all OPEN/PENDING DB trades by setting status to CLOSED (simulates end-of-day square off).',
        )
        parser.add_argument(
            '--client-id',
            type=str,
            help='Optional: Specify a client ID to target the reset.',
            default=settings.DHAN_CLIENT_ID
        )

    def handle(self, *args, **options):
        client_id = options['client-id']
        force_db_close = options['force_db_close']
        today_str = datetime.now(settings.IST).date().isoformat()

        try:
            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to connect to Redis: {e}"))
            return

        # Define all dynamic keys based on the strategy logic
        keys_to_delete = [
            f"breakout_limit_reached:{client_id}:{today_str}",
            f"breakout_trade_count:{client_id}:{today_str}",
            f"cb_daily_realized_pnl:{client_id}:{today_str}",
            f"breakout_active_entries:{client_id}",
            f"breakout_exiting_trades:{client_id}",
            f"cb_daily_reset_done:{client_id}:{today_str}",
            f"cb_pending_trades:{client_id}",
            settings.REDIS_STATUS_DATA_ENGINE,
            settings.REDIS_STATUS_ALGO_ENGINE,
        ]

        # Execute Redis deletion
        deleted_count = r.delete(*keys_to_delete)
        self.stdout.write(
            self.style.SUCCESS(f"Successfully deleted {deleted_count} Redis state keys for client {client_id}."))

        if force_db_close:
            self.stdout.write(self.style.WARNING("Attempting to close all OPEN/PENDING trades in DB..."))

            try:
                with transaction.atomic():
                    # Close OPEN and PENDING trades for safety/simulation
                    updated_trades = CashBreakoutTrade.objects.filter(
                        status__in=['OPEN', 'PENDING_EXIT', 'PENDING_ENTRY']
                    ).update(
                        status='CLOSED',
                        exit_reason='MANUAL_RESET_COMMAND (FORCE SQUARE OFF)',
                        exit_time=timezone.now()
                    )
                    self.stdout.write(self.style.SUCCESS(f"Force-closed {updated_trades} trades in the database."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Database update failed: {e}"))

        self.stdout.write(self.style.NOTICE("Daily state reset is complete. Engines must be restarted to synchronize."))