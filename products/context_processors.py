from django.conf import settings


def stores_processor(request):
    """Add stores configuration with product counts to all templates."""
    from .models import Product
    
    # Get product counts for each store
    stores_with_counts = {}
    for store_id, store_info in settings.STORES.items():
        count = Product.objects.filter(store_id=store_id).count()
        stores_with_counts[store_id] = {
            **store_info,
            'count': count,
        }
    
    return {
        'stores': stores_with_counts,
    }

