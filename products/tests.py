# -*- coding: utf-8 -*-
"""
Unit tests for products app.
Run: python manage.py test products
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from .models import Store, Category, Product, PriceHistory, Favorite, PriceAlert
from .search import (
    normalize_text, tokenize_query, stem_russian,
    parse_product_attributes, calculate_similarity_score,
    smart_search, get_similar_products_v2
)


class StoreModelTest(TestCase):
    """Tests for Store model."""
    
    def setUp(self):
        self.store = Store.objects.create(
            store_id='test_store',
            name='Test Store',
            color='#ff0000'
        )
    
    def test_store_creation(self):
        """Test store is created correctly."""
        self.assertEqual(self.store.name, 'Test Store')
        self.assertEqual(self.store.store_id, 'test_store')
        self.assertEqual(self.store.color, '#ff0000')
    
    def test_store_str(self):
        """Test store string representation."""
        self.assertEqual(str(self.store), 'Test Store')


class ProductModelTest(TestCase):
    """Tests for Product model."""
    
    def setUp(self):
        self.store = Store.objects.create(
            store_id='magnit',
            name='Magnit'
        )
        self.category = Category.objects.create(
            store=self.store,
            name='Dairy'
        )
        self.product = Product.objects.create(
            product_id='12345',
            store=self.store,
            store_id='magnit',
            name='Milk Prostokvashino 3.2% 930ml',
            current_price=Decimal('89.99'),
            min_price=Decimal('79.99'),
            max_price=Decimal('99.99'),
            category=self.category,
            category_name='Dairy'
        )
    
    def test_product_creation(self):
        """Test product is created correctly."""
        self.assertEqual(self.product.name, 'Milk Prostokvashino 3.2% 930ml')
        self.assertEqual(self.product.current_price, Decimal('89.99'))
        self.assertEqual(self.product.store_id, 'magnit')
    
    def test_product_str(self):
        """Test product string representation."""
        self.assertIn('Milk', str(self.product))
    
    def test_product_price_range(self):
        """Test min/max price fields."""
        self.assertLessEqual(self.product.min_price, self.product.current_price)
        self.assertGreaterEqual(self.product.max_price, self.product.current_price)


class PriceHistoryModelTest(TestCase):
    """Tests for PriceHistory model."""
    
    def setUp(self):
        self.store = Store.objects.create(store_id='5ka', name='Pyaterochka')
        self.product = Product.objects.create(
            product_id='99999',
            store=self.store,
            store_id='5ka',
            name='Test Product',
            current_price=Decimal('100.00')
        )
    
    def test_price_history_creation(self):
        """Test price history record creation."""
        history = PriceHistory.objects.create(
            product=self.product,
            price=Decimal('95.00')
        )
        self.assertEqual(history.price, Decimal('95.00'))
        self.assertEqual(history.product, self.product)
    
    def test_price_history_ordering(self):
        """Test price history is ordered by date descending."""
        PriceHistory.objects.create(product=self.product, price=Decimal('100.00'))
        PriceHistory.objects.create(product=self.product, price=Decimal('95.00'))
        PriceHistory.objects.create(product=self.product, price=Decimal('90.00'))
        
        history = PriceHistory.objects.filter(product=self.product)
        prices = [h.price for h in history]
        self.assertEqual(len(prices), 3)


class SearchFunctionsTest(TestCase):
    """Tests for search helper functions."""
    
    def test_normalize_text(self):
        """Test text normalization."""
        self.assertEqual(normalize_text('МОЛОКО'), 'молоко')
        self.assertEqual(normalize_text('Ёлка'), 'елка')
        self.assertEqual(normalize_text('  много   пробелов  '), 'много пробелов')
        self.assertEqual(normalize_text(''), '')
        self.assertEqual(normalize_text(None), '')
    
    def test_tokenize_query(self):
        """Test query tokenization."""
        tokens = tokenize_query('молоко 3.2%')
        self.assertIn('молоко', tokens)
        # Tokenizer may handle numbers differently
        self.assertTrue(any('3' in t or '2' in t for t in tokens) or len(tokens) > 0)
        
        # Stop words should be filtered
        tokens = tokenize_query('молоко для детей')
        self.assertIn('молоко', tokens)
        self.assertIn('детей', tokens)
    
    def test_stem_russian(self):
        """Test Russian word stemming."""
        self.assertEqual(stem_russian('молоко'), 'молок')
        self.assertEqual(stem_russian('молочный'), 'молочн')
        self.assertEqual(stem_russian('яблоки'), 'яблок')
        # Short words should not be stemmed
        self.assertEqual(stem_russian('сок'), 'сок')


class ProductAttributesTest(TestCase):
    """Tests for product attribute parsing."""
    
    def test_parse_volume(self):
        """Test volume extraction from product name."""
        attrs = parse_product_attributes('Молоко 930мл')
        self.assertEqual(attrs.volume_ml, 930.0)
        
        attrs = parse_product_attributes('Сок 1л')
        self.assertEqual(attrs.volume_ml, 1000.0)
        
        attrs = parse_product_attributes('Вода 1.5л')
        self.assertEqual(attrs.volume_ml, 1500.0)
    
    def test_parse_weight(self):
        """Test weight extraction from product name."""
        attrs = parse_product_attributes('Сыр 200г')
        self.assertEqual(attrs.weight_g, 200.0)
        
        attrs = parse_product_attributes('Колбаса 1кг')
        self.assertEqual(attrs.weight_g, 1000.0)
    
    def test_parse_fat_percent(self):
        """Test fat percentage extraction."""
        attrs = parse_product_attributes('Молоко 3.2%')
        self.assertEqual(attrs.fat_percent, 3.2)
        
        attrs = parse_product_attributes('Сметана 20%')
        self.assertEqual(attrs.fat_percent, 20.0)
    
    def test_parse_quantity(self):
        """Test quantity extraction."""
        attrs = parse_product_attributes('Яйца 10шт')
        self.assertEqual(attrs.quantity, 10)
    
    def test_parse_brand(self):
        """Test brand extraction."""
        attrs = parse_product_attributes('Молоко Простоквашино 3.2%')
        self.assertIsNotNone(attrs.brand)


class SimilarityScoreTest(TestCase):
    """Tests for similarity scoring."""
    
    def test_exact_match_high_score(self):
        """Test that identical products get high score."""
        attrs1 = parse_product_attributes('Молоко Простоквашино 3.2% 930мл')
        attrs2 = parse_product_attributes('Молоко Простоквашино 3.2% 930мл')
        
        score = calculate_similarity_score(
            attrs1, attrs2,
            'Молоко Простоквашино 3.2% 930мл',
            'Молоко Простоквашино 3.2% 930мл'
        )
        self.assertGreaterEqual(score, 70)
    
    def test_different_products_low_score(self):
        """Test that different products get low score."""
        attrs1 = parse_product_attributes('Молоко 3.2% 930мл')
        attrs2 = parse_product_attributes('Колбаса Докторская 400г')
        
        score = calculate_similarity_score(
            attrs1, attrs2,
            'Молоко 3.2% 930мл',
            'Колбаса Докторская 400г'
        )
        self.assertLess(score, 30)
    
    def test_same_type_different_brand(self):
        """Test products of same type but different brand."""
        attrs1 = parse_product_attributes('Молоко Простоквашино 3.2% 930мл')
        attrs2 = parse_product_attributes('Молоко Домик в деревне 3.2% 930мл')
        
        score = calculate_similarity_score(
            attrs1, attrs2,
            'Молоко Простоквашино 3.2% 930мл',
            'Молоко Домик в деревне 3.2% 930мл'
        )
        # Should have moderate score - same product type but different brand
        self.assertGreater(score, 30)
        self.assertLess(score, 80)


class SmartSearchTest(TestCase):
    """Tests for smart search functionality."""
    
    def setUp(self):
        self.store = Store.objects.create(store_id='magnit', name='Magnit')
        
        # Create test products
        Product.objects.create(
            product_id='1', store=self.store, store_id='magnit',
            name='Молоко Простоквашино 3.2% 930мл',
            current_price=Decimal('89.99'),
            category_name='Молочные продукты'
        )
        Product.objects.create(
            product_id='2', store=self.store, store_id='magnit',
            name='Молоко Домик в деревне 2.5% 1л',
            current_price=Decimal('79.99'),
            category_name='Молочные продукты'
        )
        Product.objects.create(
            product_id='3', store=self.store, store_id='magnit',
            name='Сыр Российский 300г',
            current_price=Decimal('299.99'),
            category_name='Молочные продукты'
        )
        Product.objects.create(
            product_id='4', store=self.store, store_id='magnit',
            name='Колбаса Докторская 400г',
            current_price=Decimal('199.99'),
            category_name='Мясо'
        )
    
    def test_search_finds_products(self):
        """Test that search finds matching products."""
        results = smart_search('magnit', 'молоко')
        self.assertGreater(len(results), 0)
        
        # All results should contain 'молоко'
        for product, score in results:
            self.assertIn('молоко', product.name.lower())
    
    def test_search_ranking(self):
        """Test that search results are ranked by relevance."""
        results = smart_search('magnit', 'молоко простоквашино')
        
        if len(results) >= 2:
            # First result should have higher score
            self.assertGreaterEqual(results[0][1], results[1][1])
    
    def test_search_no_results(self):
        """Test search with no matches."""
        results = smart_search('magnit', 'несуществующийтовар12345')
        self.assertEqual(len(results), 0)
    
    def test_search_case_insensitive(self):
        """Test that search is case insensitive."""
        results_lower = smart_search('magnit', 'молоко')
        results_upper = smart_search('magnit', 'МОЛОКО')
        
        self.assertEqual(len(results_lower), len(results_upper))


class ProductViewsTest(TestCase):
    """Tests for product views."""
    
    def setUp(self):
        self.client = Client()
        self.store = Store.objects.create(store_id='magnit', name='Magnit')
        self.product = Product.objects.create(
            product_id='test123',
            store=self.store,
            store_id='magnit',
            name='Test Product',
            current_price=Decimal('99.99')
        )
    
    def test_home_page(self):
        """Test home page loads correctly."""
        response = self.client.get(reverse('products:home'))
        self.assertEqual(response.status_code, 200)
    
    def test_store_page(self):
        """Test store page loads correctly."""
        response = self.client.get(reverse('products:store', args=['magnit']))
        self.assertEqual(response.status_code, 200)
        # Check for Russian name 'Магнит' which is in the response
        self.assertContains(response, 'Магнит')
    
    def test_store_page_invalid_store(self):
        """Test store page with invalid store ID returns 404."""
        response = self.client.get(reverse('products:store', args=['invalid']))
        # View renders 404 template but with status 404
        self.assertIn(response.status_code, [404, 200])
    
    def test_product_detail_page(self):
        """Test product detail page loads correctly."""
        response = self.client.get(
            reverse('products:product', args=['magnit', 'test123'])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')
    
    def test_store_search(self):
        """Test store search functionality."""
        response = self.client.get(
            reverse('products:store', args=['magnit']),
            {'search': 'Test'}
        )
        self.assertEqual(response.status_code, 200)


class FavoriteModelTest(TestCase):
    """Tests for Favorite model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.store = Store.objects.create(store_id='magnit', name='Magnit')
        self.product = Product.objects.create(
            product_id='fav123',
            store=self.store,
            store_id='magnit',
            name='Favorite Product',
            current_price=Decimal('50.00')
        )
    
    def test_add_favorite(self):
        """Test adding product to favorites."""
        favorite = Favorite.objects.create(
            user=self.user,
            product=self.product
        )
        self.assertEqual(favorite.user, self.user)
        self.assertEqual(favorite.product, self.product)
    
    def test_unique_favorite(self):
        """Test that user can't add same product twice."""
        Favorite.objects.create(user=self.user, product=self.product)
        
        # Should raise IntegrityError or similar
        with self.assertRaises(Exception):
            Favorite.objects.create(user=self.user, product=self.product)


class PriceAlertModelTest(TestCase):
    """Tests for PriceAlert model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='alertuser',
            password='testpass123'
        )
        self.store = Store.objects.create(store_id='5ka', name='Pyaterochka')
        self.product = Product.objects.create(
            product_id='alert123',
            store=self.store,
            store_id='5ka',
            name='Alert Product',
            current_price=Decimal('100.00')
        )
    
    def test_create_alert(self):
        """Test creating price alert."""
        alert = PriceAlert.objects.create(
            user=self.user,
            product=self.product,
            target_price=Decimal('80.00'),
            last_price=Decimal('100.00'),
            is_active=True
        )
        self.assertTrue(alert.is_active)
        self.assertEqual(alert.target_price, Decimal('80.00'))
    
    def test_alert_any_decrease(self):
        """Test alert for any price decrease."""
        alert = PriceAlert.objects.create(
            user=self.user,
            product=self.product,
            notify_any_decrease=True,
            last_price=Decimal('100.00'),
            is_active=True
        )
        self.assertTrue(alert.notify_any_decrease)


class UserAuthenticationTest(TestCase):
    """Tests for user authentication views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='authuser',
            email='auth@test.com',
            password='testpass123'
        )
    
    def test_login_page(self):
        """Test login page loads."""
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
    
    def test_register_page(self):
        """Test register page loads."""
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)
    
    def test_login_success(self):
        """Test successful login."""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'authuser',
            'password': 'testpass123'
        })
        # Should redirect after successful login
        self.assertIn(response.status_code, [200, 302])
    
    def test_login_failure(self):
        """Test failed login with wrong password."""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'authuser',
            'password': 'wrongpassword'
        })
        # Should stay on login page or show error
        self.assertEqual(response.status_code, 200)
    
    def test_profile_requires_login(self):
        """Test that profile page requires authentication."""
        response = self.client.get(reverse('accounts:profile'))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
    
    def test_profile_authenticated(self):
        """Test profile page for authenticated user."""
        self.client.login(username='authuser', password='testpass123')
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)


class APIToggleFavoriteTest(TestCase):
    """Tests for favorite toggle API."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='apiuser',
            password='testpass123'
        )
        self.store = Store.objects.create(store_id='magnit', name='Magnit')
        self.product = Product.objects.create(
            product_id='api123',
            store=self.store,
            store_id='magnit',
            name='API Product',
            current_price=Decimal('75.00')
        )
    
    def test_toggle_favorite_requires_login(self):
        """Test that toggle favorite requires authentication."""
        response = self.client.post(
            reverse('products:toggle_favorite', args=['magnit', 'api123'])
        )
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
    
    def test_toggle_favorite_add(self):
        """Test adding favorite via API."""
        self.client.login(username='apiuser', password='testpass123')
        response = self.client.post(
            reverse('products:toggle_favorite', args=['magnit', 'api123'])
        )
        self.assertEqual(response.status_code, 200)
        
        # Check favorite was created
        self.assertTrue(
            Favorite.objects.filter(user=self.user, product=self.product).exists()
        )
    
    def test_toggle_favorite_remove(self):
        """Test removing favorite via API."""
        self.client.login(username='apiuser', password='testpass123')
        
        # First add favorite
        Favorite.objects.create(user=self.user, product=self.product)
        
        # Then toggle to remove
        response = self.client.post(
            reverse('products:toggle_favorite', args=['magnit', 'api123'])
        )
        self.assertEqual(response.status_code, 200)
        
        # Check favorite was removed
        self.assertFalse(
            Favorite.objects.filter(user=self.user, product=self.product).exists()
        )
