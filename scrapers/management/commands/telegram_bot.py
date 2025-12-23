# -*- coding: utf-8 -*-
"""
Django management command for running Telegram bot.
Usage: python manage.py telegram_bot

Команды бота:
/start - Начало работы, получение кода привязки
/link - Получить новый код привязки
/unlink - Отвязка аккаунта
/status - Статус подписок
/help - Помощь
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from asgiref.sync import sync_to_async
from accounts.models import UserProfile, TelegramLinkCode
from products.models import PriceAlert
from datetime import timedelta
import secrets
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run Telegram notification bot'

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        
        if not token:
            self.stdout.write(self.style.ERROR(
                "TELEGRAM_BOT_TOKEN not set!\n"
                "Set it in settings.py or as environment variable."
            ))
            return
        
        self.stdout.write(f"Starting Telegram bot @{settings.TELEGRAM_BOT_USERNAME}...")
        self.run_bot_sync(token)

    def run_bot_sync(self, token):
        try:
            from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
            from telegram.ext import Application, CommandHandler
        except ImportError:
            self.stdout.write(self.style.ERROR(
                "python-telegram-bot not installed. Run: pip install python-telegram-bot"
            ))
            return
        
        # Build application
        application = Application.builder().token(token).build()
        
        # Command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("link", link_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("unlink", unlink_command))
        application.add_handler(CommandHandler("help", help_command))
        
        self.stdout.write(self.style.SUCCESS("Bot started! Press Ctrl+C to stop."))
        
        # Run with run_polling (handles event loop internally)
        application.run_polling(allowed_updates=Update.ALL_TYPES)


# ============================================================================
# DATABASE ACCESS FUNCTIONS
# ============================================================================

@sync_to_async
def get_profile_by_chat_id(chat_id):
    """Get user profile by Telegram chat_id."""
    try:
        return UserProfile.objects.select_related('user').get(telegram_chat_id=str(chat_id))
    except UserProfile.DoesNotExist:
        return None


@sync_to_async
def generate_linking_code(chat_id):
    """Generate linking code and save to database."""
    code = secrets.token_hex(4).upper()  # 8-character code
    expires_at = timezone.now() + timedelta(minutes=10)
    
    # Delete old codes for this chat_id
    TelegramLinkCode.objects.filter(telegram_chat_id=str(chat_id)).delete()
    
    # Save new code
    TelegramLinkCode.objects.create(
        code=code,
        telegram_chat_id=str(chat_id),
        expires_at=expires_at
    )
    
    return code


@sync_to_async
def get_user_alerts_count(profile):
    """Get count of active price alerts for user."""
    return PriceAlert.objects.filter(user=profile.user, is_active=True).count()


@sync_to_async
def get_user_favorites_count(profile):
    """Get count of user favorites."""
    return profile.user.favorites.count()


@sync_to_async
def unlink_account(profile):
    """Unlink Telegram from user account."""
    username = profile.user.username
    profile.telegram_chat_id = None
    profile.telegram_username = ''
    profile.save()
    return username


@sync_to_async
def get_user_alerts_list(profile, limit=10):
    """Get list of active price alerts."""
    alerts = PriceAlert.objects.filter(
        user=profile.user, 
        is_active=True
    ).select_related('product', 'product__store').order_by('-created_at')[:limit]
    
    return [(a.product.name, a.product.store.name if a.product.store else 'Unknown', 
             float(a.last_price) if a.last_price else 0) for a in alerts]


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

async def start_command(update, context):
    """Handle /start command."""
    chat_id = update.effective_chat.id
    
    profile = await get_profile_by_chat_id(chat_id)
    
    if profile:
        # User is already linked
        alerts_count = await get_user_alerts_count(profile)
        await update.message.reply_text(
            f"👋 Привет, {profile.user.username}!\n\n"
            f"✅ Ваш аккаунт Pricio привязан.\n"
            f"🔔 Активных подписок: {alerts_count}\n\n"
            f"📱 Вы будете получать уведомления о снижении цен на отслеживаемые товары.\n\n"
            f"Команды:\n"
            f"/status - Статус подписок\n"
            f"/unlink - Отвязать аккаунт\n"
            f"/help - Помощь"
        )
    else:
        # New user - generate linking code
        code = await generate_linking_code(chat_id)
        
        message_text = (
            f"👋 Добро пожаловать в Pricio Notify Bot!\n\n"
            f"Этот бот отправляет уведомления о снижении цен на товары, "
            f"которые вы отслеживаете на сайте.\n\n"
            f"📌 Для привязки аккаунта:\n"
            f"1. Войдите в свой аккаунт на сайте Pricio\n"
            f"2. Перейдите в Профиль\n"
            f"3. Введите этот код привязки:\n\n"
            f"🔑 <code>{code}</code>\n\n"
            f"⏰ Код действителен 10 минут.\n\n"
            f"Используйте /link для получения нового кода."
        )
        
        await update.message.reply_text(
            message_text,
            parse_mode='HTML'
        )


async def link_command(update, context):
    """Handle /link command - get new linking code."""
    chat_id = update.effective_chat.id
    
    # Check if already linked
    profile = await get_profile_by_chat_id(chat_id)
    if profile:
        await update.message.reply_text(
            f"✅ Ваш Telegram уже привязан к аккаунту: {profile.user.username}\n\n"
            f"Для смены аккаунта сначала отвяжите текущий: /unlink"
        )
        return
    
    # Generate new code
    code = await generate_linking_code(chat_id)
    await update.message.reply_text(
        f"📌 Ваш код привязки:\n\n"
        f"🔑 <code>{code}</code>\n\n"
        f"Введите этот код в настройках профиля на сайте Pricio.\n"
        f"⏰ Код действителен 10 минут.",
        parse_mode='HTML'
    )


async def status_command(update, context):
    """Handle /status command - show subscriptions status."""
    chat_id = update.effective_chat.id
    
    profile = await get_profile_by_chat_id(chat_id)
    
    if not profile:
        await update.message.reply_text(
            "❌ Аккаунт не привязан. Используйте /start для привязки."
        )
        return
    
    alerts_count = await get_user_alerts_count(profile)
    favorites_count = await get_user_favorites_count(profile)
    
    if alerts_count == 0:
        await update.message.reply_text(
            f"👤 Аккаунт: {profile.user.username}\n\n"
            f"❤️ В избранном: {favorites_count}\n"
            f"📭 У вас нет активных подписок на товары.\n\n"
            f"Добавьте товары в отслеживание на сайте Pricio!"
        )
        return
    
    alerts = await get_user_alerts_list(profile)
    
    text = f"👤 Аккаунт: {profile.user.username}\n"
    text += f"❤️ В избранном: {favorites_count}\n"
    text += f"🔔 Активных подписок: {alerts_count}\n\n"
    
    for i, (name, store, last_price) in enumerate(alerts, 1):
        # Truncate long names
        display_name = name[:40] + '...' if len(name) > 40 else name
        text += f"{i}. {display_name}\n"
        text += f"   🏪 {store} | 💰 {last_price:.2f}₽\n\n"
    
    if len(alerts) == 10:
        text += "...\n(показаны первые 10 подписок)"
    
    await update.message.reply_text(text)


async def unlink_command(update, context):
    """Handle /unlink command - unlink account."""
    chat_id = update.effective_chat.id
    
    profile = await get_profile_by_chat_id(chat_id)
    
    if not profile:
        await update.message.reply_text(
            "❌ Ваш Telegram не привязан ни к одному аккаунту.\n"
            "Используйте /start для привязки."
        )
        return
    
    username = await unlink_account(profile)
    await update.message.reply_text(
        f"✅ Аккаунт {username} успешно отвязан.\n\n"
        f"Вы больше не будете получать уведомления о ценах.\n"
        f"Для повторной привязки используйте /start"
    )


async def help_command(update, context):
    """Handle /help command."""
    await update.message.reply_text(
        "🤖 <b>Pricio Notify Bot</b>\n\n"
        "Бот для получения уведомлений о снижении цен на товары.\n\n"
        "<b>Команды:</b>\n"
        "/start - Начало работы, получение кода привязки\n"
        "/link - Получить новый код привязки\n"
        "/unlink - Отвязать аккаунт Pricio\n"
        "/status - Статус ваших подписок\n"
        "/help - Эта справка\n\n"
        "<b>Как это работает:</b>\n"
        "1. Зарегистрируйтесь на сайте Pricio\n"
        "2. Привяжите Telegram через настройки профиля\n"
        "3. Добавляйте товары в отслеживание\n"
        "4. Получайте уведомления при снижении цен! 📉",
        parse_mode='HTML'
    )
