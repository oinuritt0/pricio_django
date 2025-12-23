from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegisterForm


def register(request):
    """User registration view."""
    if request.user.is_authenticated:
        return redirect('products:home')
    
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Аккаунт создан! Добро пожаловать, {user.username}!')
            return redirect('products:home')
    else:
        form = UserRegisterForm()
    
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile(request):
    """User profile page."""
    return render(request, 'accounts/profile.html')


@login_required
def link_telegram(request):
    """Link Telegram account using code from bot."""
    from .models import TelegramLinkCode, UserProfile
    from django.utils import timezone
    
    if request.method == 'POST':
        action = request.POST.get('action', 'link')
        
        if action == 'unlink':
            # Unlink Telegram
            profile = request.user.profile
            if profile.telegram_chat_id:
                profile.telegram_chat_id = None
                profile.telegram_username = ''
                profile.save()
                messages.success(request, 'Telegram аккаунт отвязан.')
            else:
                messages.warning(request, 'Telegram не был привязан.')
        else:
            # Link using code from Telegram bot
            code = request.POST.get('code', '').strip().upper()
            
            if not code:
                messages.error(request, 'Введите код привязки.')
                return redirect('accounts:profile')
            
            # Clean up expired codes
            TelegramLinkCode.objects.filter(expires_at__lt=timezone.now()).delete()
            
            # Find valid code
            try:
                link_code = TelegramLinkCode.objects.get(
                    code=code,
                    is_used=False,
                    expires_at__gt=timezone.now(),
                    telegram_chat_id__isnull=False
                )
            except TelegramLinkCode.DoesNotExist:
                messages.error(request, 'Неверный или истёкший код привязки.')
                return redirect('accounts:profile')
            
            # Check if this Telegram is already linked to another account
            existing = UserProfile.objects.filter(
                telegram_chat_id=link_code.telegram_chat_id
            ).exclude(user=request.user).first()
            
            if existing:
                messages.error(request, f'Этот Telegram уже привязан к аккаунту {existing.user.username}.')
                return redirect('accounts:profile')
            
            # Link Telegram to user
            profile = request.user.profile
            profile.telegram_chat_id = link_code.telegram_chat_id
            profile.save()
            
            # Mark code as used
            link_code.is_used = True
            link_code.user = request.user
            link_code.save()
            
            messages.success(request, 'Telegram успешно привязан! Теперь вы будете получать уведомления.')
    
    return redirect('accounts:profile')
