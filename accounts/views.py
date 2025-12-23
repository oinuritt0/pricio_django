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
    """Link Telegram account."""
    if request.method == 'POST':
        # TODO: Implement Telegram linking
        messages.info(request, 'Функция привязки Telegram в разработке.')
    return redirect('accounts:profile')
