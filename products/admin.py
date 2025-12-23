from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from .models import Store, Category, Product, PriceHistory, Favorite, PriceAlert
import subprocess
import threading
import os


# Custom Admin Site with Scraper Management
class PricioAdminSite(admin.AdminSite):
    site_header = 'Pricio Администрирование'
    site_title = 'Pricio Admin'
    index_title = 'Управление сайтом'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('scrapers/', self.admin_view(self.scrapers_view), name='scrapers'),
            path('scrapers/run/', self.admin_view(self.run_scraper_view), name='run_scraper'),
            path('scrapers/status/', self.admin_view(self.scraper_status_view), name='scraper_status'),
        ]
        return custom_urls + urls
    
    def scrapers_view(self, request):
        """Scraper management page."""
        context = {
            **self.each_context(request),
            'title': 'Управление скраперами',
            'stores': [
                {'id': '5ka', 'name': 'Пятёрочка', 'products': Product.objects.filter(store_id='5ka').count()},
                {'id': 'magnit', 'name': 'Магнит', 'products': Product.objects.filter(store_id='magnit').count()},
            ],
            'scraper_running': getattr(self, '_scraper_running', False),
            'scraper_store': getattr(self, '_scraper_store', None),
        }
        return render(request, 'admin/scrapers.html', context)
    
    def run_scraper_view(self, request):
        """Run scraper via AJAX."""
        if request.method != 'POST':
            return JsonResponse({'error': 'POST required'}, status=400)
        
        store = request.POST.get('store', 'magnit')
        mode = request.POST.get('mode', 'demo')  # demo or full
        
        # Check if scraper is already running
        if getattr(self, '_scraper_running', False):
            return JsonResponse({
                'success': False,
                'message': f'Скрапер уже запущен для {self._scraper_store}'
            })
        
        # Run scraper in background thread
        def run_scraper():
            self._scraper_running = True
            self._scraper_store = store
            try:
                cmd = ['python', 'manage.py', 'scrape', store]
                if mode == 'full':
                    cmd.append('--full')
                else:
                    cmd.append('--demo')
                
                # Run in project directory
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
                self._scraper_result = {
                    'success': result.returncode == 0,
                    'output': result.stdout[-2000:] if result.stdout else '',
                    'error': result.stderr[-1000:] if result.stderr else ''
                }
            except Exception as e:
                self._scraper_result = {'success': False, 'error': str(e)}
            finally:
                self._scraper_running = False
                self._scraper_store = None
        
        thread = threading.Thread(target=run_scraper, daemon=True)
        thread.start()
        
        store_name = 'Пятёрочка' if store == '5ka' else 'Магнит'
        mode_name = 'полный' if mode == 'full' else 'демо'
        
        return JsonResponse({
            'success': True,
            'message': f'Скрапер {store_name} ({mode_name}) запущен!'
        })
    
    def scraper_status_view(self, request):
        """Get scraper status."""
        return JsonResponse({
            'running': getattr(self, '_scraper_running', False),
            'store': getattr(self, '_scraper_store', None),
            'result': getattr(self, '_scraper_result', None)
        })


# Create custom admin site instance
pricio_admin = PricioAdminSite(name='admin')

# Import auth models for registration
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin

# Register auth models
pricio_admin.register(User, UserAdmin)
pricio_admin.register(Group, GroupAdmin)


# Model Admin classes
class StoreAdminConfig(admin.ModelAdmin):
    list_display = ['store_id', 'name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'store_id']


class CategoryAdminConfig(admin.ModelAdmin):
    list_display = ['name', 'store', 'slug']
    list_filter = ['store']
    search_fields = ['name']


class ProductAdminConfig(admin.ModelAdmin):
    list_display = ['name', 'store', 'current_price', 'category_name', 'last_updated']
    list_filter = ['store', 'category_name']
    search_fields = ['name', 'product_id', 'brand']
    readonly_fields = ['first_seen', 'last_updated']


class PriceHistoryAdminConfig(admin.ModelAdmin):
    list_display = ['product', 'price', 'previous_price', 'recorded_at']
    list_filter = ['recorded_at']
    search_fields = ['product__name']
    date_hierarchy = 'recorded_at'


class FavoriteAdminConfig(admin.ModelAdmin):
    list_display = ['user', 'product', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__username', 'product__name']


class PriceAlertAdminConfig(admin.ModelAdmin):
    list_display = ['user', 'product', 'target_price', 'is_active', 'created_at']
    list_filter = ['is_active', 'notify_any_decrease']
    search_fields = ['user__username', 'product__name']


# Register models with custom admin
pricio_admin.register(Store, StoreAdminConfig)
pricio_admin.register(Category, CategoryAdminConfig)
pricio_admin.register(Product, ProductAdminConfig)
pricio_admin.register(PriceHistory, PriceHistoryAdminConfig)
pricio_admin.register(Favorite, FavoriteAdminConfig)
pricio_admin.register(PriceAlert, PriceAlertAdminConfig)


# Also register with default admin for backwards compatibility
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
