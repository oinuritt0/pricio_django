from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Store(models.Model):
    """Store model (Pyaterochka, Magnit, etc.)"""
    store_id = models.CharField(max_length=50, unique=True, primary_key=True)
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=20, default='#22c55e')
    icon = models.CharField(max_length=10, default='S')
    base_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Store'
        verbose_name_plural = 'Stores'
    
    def __str__(self):
        return self.name


class Category(models.Model):
    """Product category."""
    name = models.CharField(max_length=200)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='categories')
    slug = models.SlugField(max_length=200, blank=True)
    
    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        unique_together = ['name', 'store']
    
    def __str__(self):
        return f"{self.store.name} - {self.name}"


class Product(models.Model):
    """Product model with price tracking."""
    product_id = models.CharField(max_length=100)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=500)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    category_name = models.CharField(max_length=200, blank=True)
    
    # Price fields
    current_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Product attributes
    brand = models.CharField(max_length=100, blank=True)
    volume_ml = models.FloatField(null=True, blank=True)
    weight_g = models.FloatField(null=True, blank=True)
    fat_percent = models.FloatField(null=True, blank=True)
    quantity = models.IntegerField(null=True, blank=True)
    
    # Metadata
    image_url = models.URLField(max_length=500, blank=True)
    url = models.URLField(max_length=500, blank=True)
    
    # Timestamps
    first_seen = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        unique_together = ['product_id', 'store']
        indexes = [
            models.Index(fields=['store', 'category_name']),
            models.Index(fields=['name']),
            models.Index(fields=['current_price']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.store.store_id})"


class PriceHistory(models.Model):
    """Price history for a product."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_history')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    previous_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Price History'
        verbose_name_plural = 'Price History'
        ordering = ['-recorded_at']
    
    def __str__(self):
        return f"{self.product.name}: {self.price}"


class Favorite(models.Model):
    """User's favorite products."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorited_by')
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Favorite'
        verbose_name_plural = 'Favorites'
        unique_together = ['user', 'product']
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class PriceAlert(models.Model):
    """Price drop alerts for products."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='price_alerts')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='alerts')
    target_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notify_any_decrease = models.BooleanField(default=True)
    last_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Price Alert'
        verbose_name_plural = 'Price Alerts'
        unique_together = ['user', 'product']
    
    def __str__(self):
        return f"{self.user.username} alert for {self.product.name}"
