"""
Django management command for sending price drop notifications.
Usage: python manage.py notify_price_drops
       python manage.py notify_price_drops --daemon
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from products.models import PriceAlert
from accounts.models import UserProfile
import asyncio
import time
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check prices and send notifications for price drops'

    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run continuously as daemon'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=3600,
            help='Check interval in seconds (default: 3600)'
        )

    def handle(self, *args, **options):
        daemon = options['daemon']
        interval = options['interval']
        
        if daemon:
            self.stdout.write(f"Starting notification daemon (interval: {interval}s)...")
            while True:
                self.check_and_notify()
                self.stdout.write(f"Next check in {interval} seconds...")
                time.sleep(interval)
        else:
            self.check_and_notify()

    def check_and_notify(self):
        """Check all active alerts and send notifications."""
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            self.stdout.write(self.style.WARNING("TELEGRAM_BOT_TOKEN not set, skipping notifications"))
            return
        
        alerts = PriceAlert.objects.filter(is_active=True).select_related('user', 'product', 'product__store')
        
        self.stdout.write(f"Checking {alerts.count()} active alerts...")
        
        notifications_sent = 0
        
        for alert in alerts:
            product = alert.product
            current_price = product.current_price
            last_price = alert.last_price
            
            if last_price is None:
                alert.last_price = current_price
                alert.save()
                continue
            
            # Check if price dropped
            should_notify = False
            reason = ""
            
            if alert.notify_any_decrease and current_price < last_price:
                should_notify = True
                reason = "price decreased"
            elif alert.target_price and current_price <= alert.target_price:
                should_notify = True
                reason = f"reached target price {alert.target_price}"
            
            if should_notify:
                # Get user's Telegram chat_id
                try:
                    profile = alert.user.profile
                    if profile.telegram_chat_id:
                        # Send notification
                        success = asyncio.run(self.send_notification(
                            token,
                            profile.telegram_chat_id,
                            product,
                            last_price,
                            current_price,
                            reason
                        ))
                        
                        if success:
                            notifications_sent += 1
                            alert.last_notified_at = timezone.now()
                except UserProfile.DoesNotExist:
                    pass
            
            # Update last_price
            if current_price != last_price:
                alert.last_price = current_price
                alert.save()
        
        self.stdout.write(self.style.SUCCESS(f"Sent {notifications_sent} notifications"))

    async def send_notification(self, token, chat_id, product, old_price, new_price, reason):
        """Send Telegram notification."""
        try:
            from telegram import Bot
            
            bot = Bot(token=token)
            
            price_diff = float(old_price) - float(new_price)
            percent_diff = (price_diff / float(old_price)) * 100 if old_price else 0
            
            message = (
                f"🔔 <b>Цена снизилась!</b>\n\n"
                f"📦 <b>{product.name}</b>\n"
                f"🏪 {product.store.name}\n\n"
                f"💰 Было: <s>{old_price}₽</s>\n"
                f"✅ Стало: <b>{new_price}₽</b>\n\n"
                f"📉 Экономия: {price_diff:.2f}₽ ({percent_diff:.1f}%)"
            )
            
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )
            
            self.stdout.write(f"  Sent notification to {chat_id}: {product.name[:30]}...")
            return True
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Error sending to {chat_id}: {e}"))
            return False

