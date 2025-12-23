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
    """Link Telegram account - generate code or unlink."""
    from .models import TelegramLinkCode
    from django.utils import timezone
    from datetime import timedelta
    import secrets
    
    if request.method == 'POST':
        action = request.POST.get('action', 'generate')
        
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
            # Generate new link code
            TelegramLinkCode.objects.filter(user=request.user, is_used=False).delete()
            
            code = secrets.token_hex(4).upper()
            TelegramLinkCode.objects.create(
                user=request.user,
                code=code,
                expires_at=timezone.now() + timedelta(minutes=10)
            )
            messages.success(request, f'Код привязки: {code} (действует 10 минут)')
    
    return redirect('accounts:profile')
