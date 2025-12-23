from django.contrib import admin
from .models import Store, Category, Product, PriceHistory, Favorite, PriceAlert


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['store_id', 'name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'store_id']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'slug']
    list_filter = ['store']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'current_price', 'category_name', 'last_updated']
    list_filter = ['store', 'category_name']
    search_fields = ['name', 'product_id', 'brand']
    readonly_fields = ['first_seen', 'last_updated']


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'price', 'previous_price', 'recorded_at']
    list_filter = ['recorded_at']
    search_fields = ['product__name']
    date_hierarchy = 'recorded_at'


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__username', 'product__name']


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'target_price', 'is_active', 'created_at']
    list_filter = ['is_active', 'notify_any_decrease']
    search_fields = ['user__username', 'product__name']
