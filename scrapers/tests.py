# -*- coding: utf-8 -*-
"""
Unit tests for scrapers app.
Run: python manage.py test scrapers
"""
from django.test import TestCase
from unittest.mock import patch, MagicMock
from decimal import Decimal
from products.models import Store, Category, Product, PriceHistory


class ScraperDatabaseTest(TestCase):
    """Tests for scraper database operations."""
    
    def setUp(self):
        """Set up test stores."""
        self.store_5ka = Store.objects.create(
            store_id='5ka',
            name='Pyaterochka',
            color='#e30613'
        )
        self.store_magnit = Store.objects.create(
            store_id='magnit',
            name='Magnit',
            color='#e31e24'
        )
    
    def test_create_product(self):
        """Test creating a product from scraper data."""
        product = Product.objects.create(
            product_id='scraped_001',
            store=self.store_5ka,
            store_id='5ka',
            name='Молоко Простоквашино 3.2% 930мл',
            current_price=Decimal('89.99'),
            category_name='Молочные продукты'
        )
        
        self.assertEqual(product.name, 'Молоко Простоквашино 3.2% 930мл')
        self.assertEqual(product.current_price, Decimal('89.99'))
    
    def test_update_product_price(self):
        """Test updating product price."""
        product = Product.objects.create(
            product_id='scraped_002',
            store=self.store_magnit,
            store_id='magnit',
            name='Test Product',
            current_price=Decimal('100.00'),
            min_price=Decimal('100.00'),
            max_price=Decimal('100.00')
        )
        
        # Simulate price update
        new_price = Decimal('90.00')
        product.current_price = new_price
        product.min_price = min(product.min_price, new_price)
        product.save()
        
        product.refresh_from_db()
        self.assertEqual(product.current_price, Decimal('90.00'))
        self.assertEqual(product.min_price, Decimal('90.00'))
    
    def test_price_history_creation(self):
        """Test creating price history entries."""
        product = Product.objects.create(
            product_id='scraped_003',
            store=self.store_5ka,
            store_id='5ka',
            name='History Test Product',
            current_price=Decimal('150.00')
        )
        
        # Add price history
        PriceHistory.objects.create(product=product, price=Decimal('160.00'))
        PriceHistory.objects.create(product=product, price=Decimal('155.00'))
        PriceHistory.objects.create(product=product, price=Decimal('150.00'))
        
        history = PriceHistory.objects.filter(product=product)
        self.assertEqual(history.count(), 3)
    
    def test_category_creation(self):
        """Test category creation."""
        category = Category.objects.create(
            store=self.store_magnit,
            name='Молочные продукты'
        )
        
        self.assertEqual(category.name, 'Молочные продукты')
        self.assertEqual(category.store, self.store_magnit)
    
    def test_product_category_association(self):
        """Test associating product with category."""
        category = Category.objects.create(
            store=self.store_5ka,
            name='Бакалея'
        )
        
        product = Product.objects.create(
            product_id='scraped_004',
            store=self.store_5ka,
            store_id='5ka',
            name='Макароны 500г',
            current_price=Decimal('79.99'),
            category=category,
            category_name='Бакалея'
        )
        
        self.assertEqual(product.category, category)
        self.assertEqual(product.category_name, 'Бакалея')
    
    def test_bulk_product_creation(self):
        """Test bulk product creation (simulating scraper batch)."""
        products_data = [
            {'id': 'bulk_001', 'name': 'Product 1', 'price': '100.00'},
            {'id': 'bulk_002', 'name': 'Product 2', 'price': '200.00'},
            {'id': 'bulk_003', 'name': 'Product 3', 'price': '300.00'},
        ]
        
        for data in products_data:
            Product.objects.create(
                product_id=data['id'],
                store=self.store_magnit,
                store_id='magnit',
                name=data['name'],
                current_price=Decimal(data['price'])
            )
        
        count = Product.objects.filter(store=self.store_magnit).count()
        self.assertEqual(count, 3)
    
    def test_duplicate_product_handling(self):
        """Test handling duplicate products (update instead of create)."""
        # Create initial product
        Product.objects.create(
            product_id='dup_001',
            store=self.store_5ka,
            store_id='5ka',
            name='Duplicate Test',
            current_price=Decimal('100.00')
        )
        
        # Simulate scraper finding same product with different price
        Product.objects.update_or_create(
            product_id='dup_001',
            store=self.store_5ka,
            defaults={
                'name': 'Duplicate Test Updated',
                'current_price': Decimal('95.00'),
                'store_id': '5ka'
            }
        )
        
        # Should still have only one product
        count = Product.objects.filter(product_id='dup_001').count()
        self.assertEqual(count, 1)
        
        # Price should be updated
        product = Product.objects.get(product_id='dup_001')
        self.assertEqual(product.current_price, Decimal('95.00'))


class ScraperParsingTest(TestCase):
    """Tests for scraper data parsing logic."""
    
    def test_parse_price_integer(self):
        """Test parsing integer price."""
        price_str = "100"
        price = Decimal(price_str)
        self.assertEqual(price, Decimal('100'))
    
    def test_parse_price_float(self):
        """Test parsing float price."""
        price_str = "99.99"
        price = Decimal(price_str)
        self.assertEqual(price, Decimal('99.99'))
    
    def test_parse_price_with_currency(self):
        """Test parsing price with currency symbol."""
        price_str = "99.99 ₽"
        # Simulate scraper cleaning
        price_clean = ''.join(c for c in price_str if c.isdigit() or c == '.')
        price = Decimal(price_clean)
        self.assertEqual(price, Decimal('99.99'))
    
    def test_parse_price_with_comma(self):
        """Test parsing price with comma as decimal separator."""
        price_str = "99,99"
        price_clean = price_str.replace(',', '.')
        price = Decimal(price_clean)
        self.assertEqual(price, Decimal('99.99'))
    
    def test_extract_product_id_from_url(self):
        """Test extracting product ID from URL."""
        import re
        
        # 5ka URL pattern
        url_5ka = "https://5ka.ru/product/moloko-prostokvashino--12345/"
        match = re.search(r'--(\d+)\/?$', url_5ka)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), '12345')
        
        # Magnit URL pattern
        url_magnit = "https://magnit.ru/product/12345"
        match = re.search(r'/product/(\d+)', url_magnit)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), '12345')
    
    def test_clean_product_name(self):
        """Test cleaning product name."""
        raw_name = "  Молоко   Простоквашино  3.2%   930мл  "
        clean_name = ' '.join(raw_name.split())
        self.assertEqual(clean_name, 'Молоко Простоквашино 3.2% 930мл')
    
    def test_extract_category_name(self):
        """Test extracting category name from breadcrumb."""
        breadcrumb = "Главная / Молочные продукты / Молоко"
        parts = breadcrumb.split(' / ')
        category = parts[-2] if len(parts) >= 2 else parts[-1]
        self.assertEqual(category, 'Молочные продукты')


class PriceHistoryLogicTest(TestCase):
    """Tests for price history logic."""
    
    def setUp(self):
        self.store = Store.objects.create(store_id='test', name='Test')
        self.product = Product.objects.create(
            product_id='hist_001',
            store=self.store,
            store_id='test',
            name='Price History Test',
            current_price=Decimal('100.00'),
            min_price=Decimal('100.00'),
            max_price=Decimal('100.00')
        )
    
    def test_price_decrease_updates_min(self):
        """Test that price decrease updates min_price."""
        new_price = Decimal('90.00')
        
        self.product.current_price = new_price
        self.product.min_price = min(self.product.min_price, new_price)
        self.product.save()
        
        self.assertEqual(self.product.min_price, Decimal('90.00'))
    
    def test_price_increase_updates_max(self):
        """Test that price increase updates max_price."""
        new_price = Decimal('110.00')
        
        self.product.current_price = new_price
        self.product.max_price = max(self.product.max_price, new_price)
        self.product.save()
        
        self.assertEqual(self.product.max_price, Decimal('110.00'))
    
    def test_price_history_records_change(self):
        """Test that price changes are recorded in history."""
        old_price = self.product.current_price
        new_price = Decimal('95.00')
        
        # Only record if price changed
        if old_price != new_price:
            PriceHistory.objects.create(
                product=self.product,
                price=new_price
            )
        
        self.product.current_price = new_price
        self.product.save()
        
        history = PriceHistory.objects.filter(product=self.product)
        self.assertEqual(history.count(), 1)
        self.assertEqual(history.first().price, Decimal('95.00'))
    
    def test_same_price_no_history(self):
        """Test that same price doesn't create history entry."""
        old_price = self.product.current_price
        new_price = Decimal('100.00')  # Same price
        
        # Only record if price changed
        if old_price != new_price:
            PriceHistory.objects.create(
                product=self.product,
                price=new_price
            )
        
        history = PriceHistory.objects.filter(product=self.product)
        self.assertEqual(history.count(), 0)
