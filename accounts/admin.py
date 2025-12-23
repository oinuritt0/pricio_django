from django.contrib import admin
from .models import UserProfile, TelegramLinkCode


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'telegram_chat_id', 'telegram_username', 'notifications_enabled']
    list_filter = ['notifications_enabled']
    search_fields = ['user__username', 'telegram_username']


@admin.register(TelegramLinkCode)
class TelegramLinkCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'created_at', 'expires_at', 'is_used']
    list_filter = ['is_used']
    search_fields = ['user__username', 'code']
