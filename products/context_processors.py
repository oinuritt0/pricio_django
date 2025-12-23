from django.conf import settings


def stores_processor(request):
    """Add stores configuration to all templates."""
    return {
        'stores': settings.STORES,
    }

