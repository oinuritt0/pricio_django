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
    from .models import Product
    from .search import smart_search
    
    if store_id not in settings.STORES:
        return render(request, '404.html', status=404)
    
    search_query = request.GET.get('search', '').strip()
    category = request.GET.get('category', '')
    page = int(request.GET.get('page', 1))
    per_page = 50
    
    # Get categories
    categories = Product.objects.filter(store_id=store_id).values_list(
        'category_name', flat=True
    ).distinct().order_by('category_name')
    categories = [c for c in categories if c]
    
    # Search or list products
    if search_query:
        search_results = smart_search(store_id, search_query, category)
        products = [p for p, score in search_results]
        total = len(products)
    else:
        queryset = Product.objects.filter(store_id=store_id)
        if category:
            queryset = queryset.filter(category_name=category)
        queryset = queryset.order_by('name')
        total = queryset.count()
        products = queryset[(page-1)*per_page : page*per_page]
    
    total_pages = (total + per_page - 1) // per_page
    
    context = {
        'store_id': store_id,
        'store': settings.STORES[store_id],
        'products': products,
        'categories': categories,
        'search_query': search_query,
        'current_category': category,
        'page': page,
        'total_pages': total_pages,
        'total': total,
        'active_store': store_id,
    }
    return render(request, 'products/store.html', context)


def product_detail(request, store_id, product_id):
    """Product detail page with price history."""
    from .models import Product, PriceHistory, Favorite, PriceAlert
    import json
    
    if store_id not in settings.STORES:
        return render(request, '404.html', status=404)
    
    product = get_object_or_404(Product, product_id=product_id, store_id=store_id)
    price_history = PriceHistory.objects.filter(product=product).order_by('-recorded_at')[:20]
    
    # Price history for chart (reversed for chronological order)
    price_history_json = json.dumps([
        {'date': h.recorded_at.strftime('%d.%m'), 'price': float(h.price)}
        for h in reversed(list(price_history))
    ])
    
    # Similar products (same category)
    similar_products = Product.objects.filter(
        store_id=store_id,
        category_name=product.category_name
    ).exclude(product_id=product_id)[:5]
    
    # Check user favorites/alerts
    is_favorite = False
    has_alert = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, product=product).exists()
        has_alert = PriceAlert.objects.filter(user=request.user, product=product, is_active=True).exists()
    
    context = {
        'store_id': store_id,
        'store': settings.STORES[store_id],
        'product': product,
        'price_history': price_history,
        'price_history_json': price_history_json,
        'similar_products': similar_products,
        'is_favorite': is_favorite,
        'has_alert': has_alert,
        'active_store': store_id,
    }
    return render(request, 'products/product.html', context)


@login_required
def favorites(request):
    """User's favorites and price alerts."""
    from .models import Favorite, PriceAlert
    
    user_favorites = Favorite.objects.filter(user=request.user).select_related('product', 'product__store')
    user_alerts = PriceAlert.objects.filter(user=request.user, is_active=True).select_related('product', 'product__store')
    
    return render(request, 'products/favorites.html', {
        'favorites': user_favorites,
        'alerts': user_alerts,
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
