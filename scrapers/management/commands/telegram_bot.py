"""
Django management command for running Telegram bot.
Usage: python manage.py telegram_bot
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from accounts.models import UserProfile, TelegramLinkCode
from datetime import timedelta
import secrets
import asyncio
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
        
        self.stdout.write("Starting Telegram bot...")
        asyncio.run(self.run_bot(token))

    async def run_bot(self, token):
        try:
            from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
            from telegram.ext import Application, CommandHandler, ContextTypes
        except ImportError:
            self.stdout.write(self.style.ERROR(
                "python-telegram-bot not installed. Run: pip install python-telegram-bot"
            ))
            return
        
        application = Application.builder().token(token).build()
        
        # Command handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("link", self.link_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("unlink", self.unlink_command))
        application.add_handler(CommandHandler("help", self.help_command))
        
        self.stdout.write(self.style.SUCCESS("Bot started! Press Ctrl+C to stop."))
        await application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def start_command(self, update, context):
        """Handle /start command."""
        chat_id = str(update.effective_chat.id)
        
        # Check if already linked
        try:
            profile = UserProfile.objects.get(telegram_chat_id=chat_id)
            await update.message.reply_text(
                f"✅ Привет, {profile.user.username}!\n\n"
                f"Ваш Telegram уже привязан к аккаунту.\n"
                f"Используйте /status для просмотра подписок.\n"
                f"Используйте /unlink для отвязки аккаунта."
            )
            return
        except UserProfile.DoesNotExist:
            pass
        
        await update.message.reply_text(
            "👋 Привет! Я бот Pricio.\n\n"
            "Я помогу отслеживать цены на товары.\n\n"
            "Чтобы привязать аккаунт:\n"
            "1. Зайдите на сайт в раздел Профиль\n"
            "2. Получите код привязки\n"
            "3. Отправьте мне: /link КОД\n\n"
            "Используйте /help для списка команд."
        )

    async def link_command(self, update, context):
        """Handle /link <code> command."""
        chat_id = str(update.effective_chat.id)
        
        if not context.args:
            await update.message.reply_text(
                "❌ Укажите код привязки.\n"
                "Пример: /link ABC123"
            )
            return
        
        code = context.args[0].upper()
        
        try:
            link_code = TelegramLinkCode.objects.get(
                code=code,
                is_used=False,
                expires_at__gt=timezone.now()
            )
            
            # Link the account
            profile = link_code.user.profile
            profile.telegram_chat_id = chat_id
            profile.save()
            
            # Mark code as used
            link_code.is_used = True
            link_code.save()
            
            await update.message.reply_text(
                f"✅ Аккаунт успешно привязан!\n\n"
                f"Пользователь: {link_code.user.username}\n"
                f"Теперь вы будете получать уведомления о снижении цен."
            )
            
        except TelegramLinkCode.DoesNotExist:
            await update.message.reply_text(
                "❌ Неверный или просроченный код.\n"
                "Получите новый код на сайте."
            )

    async def status_command(self, update, context):
        """Handle /status command."""
        chat_id = str(update.effective_chat.id)
        
        try:
            profile = UserProfile.objects.get(telegram_chat_id=chat_id)
            alerts_count = profile.user.price_alerts.filter(is_active=True).count()
            favorites_count = profile.user.favorites.count()
            
            await update.message.reply_text(
                f"📊 Статус аккаунта\n\n"
                f"👤 Пользователь: {profile.user.username}\n"
                f"❤️ В избранном: {favorites_count}\n"
                f"🔔 Отслеживается: {alerts_count}\n"
            )
        except UserProfile.DoesNotExist:
            await update.message.reply_text(
                "❌ Аккаунт не привязан.\n"
                "Используйте /start для инструкций."
            )

    async def unlink_command(self, update, context):
        """Handle /unlink command."""
        chat_id = str(update.effective_chat.id)
        
        try:
            profile = UserProfile.objects.get(telegram_chat_id=chat_id)
            username = profile.user.username
            profile.telegram_chat_id = None
            profile.save()
            
            await update.message.reply_text(
                f"✅ Аккаунт {username} отвязан.\n"
                f"Вы больше не будете получать уведомления."
            )
        except UserProfile.DoesNotExist:
            await update.message.reply_text("❌ Аккаунт не привязан.")

    async def help_command(self, update, context):
        """Handle /help command."""
        await update.message.reply_text(
            "📖 Команды бота:\n\n"
            "/start - Начать работу\n"
            "/link КОД - Привязать аккаунт\n"
            "/status - Статус подписок\n"
            "/unlink - Отвязать аккаунт\n"
            "/help - Эта справка"
        )

