from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.home, name='home'),
    path('store/<str:store_id>/', views.store_products, name='store'),
    path('store/<str:store_id>/product/<str:product_id>/', views.product_detail, name='product'),
    path('favorites/', views.favorites, name='favorites'),
    path('search/', views.search, name='search'),
    
    # API endpoints
    path('api/favorite/<str:store_id>/<str:product_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('api/alert/<str:store_id>/<str:product_id>/', views.toggle_alert, name='toggle_alert'),
]

