from django.contrib import admin
from .models import UserProfile, TelegramLinkCode


class UserProfileAdminConfig(admin.ModelAdmin):
    list_display = ['user', 'telegram_chat_id', 'telegram_username', 'notifications_enabled']
    list_filter = ['notifications_enabled']
    search_fields = ['user__username', 'telegram_username']


class TelegramLinkCodeAdminConfig(admin.ModelAdmin):
    list_display = ['user', 'code', 'created_at', 'expires_at', 'is_used']
    list_filter = ['is_used']
    search_fields = ['user__username', 'code']


# Register with default admin
admin.site.register(UserProfile, UserProfileAdminConfig)
admin.site.register(TelegramLinkCode, TelegramLinkCodeAdminConfig)


# Register with custom pricio_admin
def register_with_pricio_admin():
    """Register accounts models with custom admin site."""
    from products.admin import pricio_admin
    pricio_admin.register(UserProfile, UserProfileAdminConfig)
    pricio_admin.register(TelegramLinkCode, TelegramLinkCodeAdminConfig)


# Call registration
try:
    register_with_pricio_admin()
except Exception:
    pass  # Will be registered when admin loads
