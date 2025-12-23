from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings


def home(request):
    """Home page - store selection."""
    return render(request, 'products/home.html', {
        'stores': settings.STORES,
    })


def store_products(request, store_id):
    """Products list for a specific store."""
    if store_id not in settings.STORES:
        return render(request, '404.html', status=404)
    
    # TODO: Get products from database
    products = []
    categories = []
    
    context = {
        'store_id': store_id,
        'store': settings.STORES[store_id],
        'products': products,
        'categories': categories,
        'active_store': store_id,
    }
    return render(request, 'products/store.html', context)


def product_detail(request, store_id, product_id):
    """Product detail page with price history."""
    if store_id not in settings.STORES:
        return render(request, '404.html', status=404)
    
    # TODO: Get product from database
    product = None
    
    context = {
        'store_id': store_id,
        'store': settings.STORES[store_id],
        'product': product,
        'active_store': store_id,
    }
    return render(request, 'products/product.html', context)


@login_required
def favorites(request):
    """User's favorites and price alerts."""
    # TODO: Get user's favorites
    return render(request, 'products/favorites.html', {
        'favorites': [],
        'alerts': [],
    })


def search(request):
    """Global search across all stores."""
    query = request.GET.get('q', '')
    # TODO: Implement search
    return render(request, 'products/search.html', {
        'query': query,
        'results': [],
    })


@login_required
def toggle_favorite(request, store_id, product_id):
    """Toggle product in favorites (AJAX)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # TODO: Implement toggle favorite
    return JsonResponse({'success': True, 'is_favorite': True})


@login_required
def toggle_alert(request, store_id, product_id):
    """Toggle price alert for product (AJAX)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # TODO: Implement toggle alert
    return JsonResponse({'success': True, 'has_alert': True})
