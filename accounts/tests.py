# -*- coding: utf-8 -*-
"""
Unit tests for accounts app.
Run: python manage.py test accounts
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import UserProfile, TelegramLinkCode


class UserProfileModelTest(TestCase):
    """Tests for UserProfile model."""
    
    def test_profile_created_on_user_creation(self):
        """Test that profile is automatically created when user is created."""
        user = User.objects.create_user(
            username='profileuser',
            password='testpass123'
        )
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, UserProfile)
    
    def test_profile_telegram_fields(self):
        """Test Telegram-related fields."""
        user = User.objects.create_user(username='tguser', password='pass123')
        profile = user.profile
        
        # Initially should be empty
        self.assertIsNone(profile.telegram_chat_id)
        self.assertEqual(profile.telegram_username, '')
        
        # Update Telegram info
        profile.telegram_chat_id = '123456789'
        profile.telegram_username = 'testbot'
        profile.save()
        
        # Verify saved
        profile.refresh_from_db()
        self.assertEqual(profile.telegram_chat_id, '123456789')
        self.assertEqual(profile.telegram_username, 'testbot')
    
    def test_profile_str(self):
        """Test profile string representation."""
        user = User.objects.create_user(username='struser', password='pass123')
        self.assertIn('struser', str(user.profile))


class TelegramLinkCodeModelTest(TestCase):
    """Tests for TelegramLinkCode model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='linkuser',
            password='testpass123'
        )
    
    def test_create_link_code_with_user(self):
        """Test creating link code with user."""
        code = TelegramLinkCode.objects.create(
            user=self.user,
            code='ABC12345',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        self.assertEqual(code.user, self.user)
        self.assertEqual(code.code, 'ABC12345')
        self.assertFalse(code.is_used)
    
    def test_create_link_code_with_chat_id(self):
        """Test creating link code with Telegram chat_id."""
        code = TelegramLinkCode.objects.create(
            telegram_chat_id='987654321',
            code='XYZ98765',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        self.assertEqual(code.telegram_chat_id, '987654321')
        self.assertIsNone(code.user)
    
    def test_link_code_is_valid(self):
        """Test is_valid method."""
        # Valid code
        valid_code = TelegramLinkCode.objects.create(
            telegram_chat_id='111',
            code='VALID123',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        self.assertTrue(valid_code.is_valid())
        
        # Expired code
        expired_code = TelegramLinkCode.objects.create(
            telegram_chat_id='222',
            code='EXPIRED1',
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        self.assertFalse(expired_code.is_valid())
        
        # Used code
        used_code = TelegramLinkCode.objects.create(
            telegram_chat_id='333',
            code='USED1234',
            expires_at=timezone.now() + timedelta(minutes=10),
            is_used=True
        )
        self.assertFalse(used_code.is_valid())
    
    def test_link_code_unique(self):
        """Test that codes must be unique."""
        TelegramLinkCode.objects.create(
            telegram_chat_id='444',
            code='UNIQUE12',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        with self.assertRaises(Exception):
            TelegramLinkCode.objects.create(
                telegram_chat_id='555',
                code='UNIQUE12',  # Same code
                expires_at=timezone.now() + timedelta(minutes=10)
            )


class UserRegistrationTest(TestCase):
    """Tests for user registration."""
    
    def setUp(self):
        self.client = Client()
    
    def test_register_page_loads(self):
        """Test registration page loads correctly."""
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Регистрация')
    
    def test_register_success(self):
        """Test successful user registration."""
        response = self.client.post(reverse('accounts:register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'complexpass123!',
            'password2': 'complexpass123!'
        })
        
        # Should redirect after successful registration
        self.assertIn(response.status_code, [200, 302])
        
        # User should be created
        self.assertTrue(User.objects.filter(username='newuser').exists())
    
    def test_register_password_mismatch(self):
        """Test registration with mismatched passwords."""
        response = self.client.post(reverse('accounts:register'), {
            'username': 'mismatchuser',
            'email': 'mismatch@example.com',
            'password1': 'password123!',
            'password2': 'differentpassword!'
        })
        
        # Should stay on page with error
        self.assertEqual(response.status_code, 200)
        
        # User should not be created
        self.assertFalse(User.objects.filter(username='mismatchuser').exists())
    
    def test_register_duplicate_username(self):
        """Test registration with existing username."""
        User.objects.create_user(username='existinguser', password='pass123')
        
        response = self.client.post(reverse('accounts:register'), {
            'username': 'existinguser',
            'email': 'new@example.com',
            'password1': 'password123!',
            'password2': 'password123!'
        })
        
        # Should stay on page with error
        self.assertEqual(response.status_code, 200)


class UserLoginTest(TestCase):
    """Tests for user login."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='loginuser',
            email='login@example.com',
            password='testpass123'
        )
    
    def test_login_page_loads(self):
        """Test login page loads correctly."""
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
    
    def test_login_success(self):
        """Test successful login."""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'loginuser',
            'password': 'testpass123'
        }, follow=True)
        
        self.assertTrue(response.wsgi_request.user.is_authenticated)
    
    def test_login_wrong_password(self):
        """Test login with wrong password."""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'loginuser',
            'password': 'wrongpassword'
        })
        
        self.assertFalse(response.wsgi_request.user.is_authenticated)
    
    def test_login_nonexistent_user(self):
        """Test login with nonexistent user."""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'nonexistent',
            'password': 'anypassword'
        })
        
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class UserLogoutTest(TestCase):
    """Tests for user logout."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='logoutuser',
            password='testpass123'
        )
    
    def test_logout(self):
        """Test logout functionality."""
        # Login first
        self.client.login(username='logoutuser', password='testpass123')
        
        # Verify logged in
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        
        # Logout via POST (Django's logout view may require POST)
        response = self.client.post(reverse('accounts:logout'), follow=True)
        
        # Logout should succeed (either redirect or show success page)
        self.assertIn(response.status_code, [200, 302])
        
        # Verify logged out - profile should redirect to login
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)


class ProfileViewTest(TestCase):
    """Tests for user profile view."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='profileview',
            email='profile@example.com',
            password='testpass123'
        )
    
    def test_profile_requires_login(self):
        """Test that profile page requires login."""
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_profile_authenticated(self):
        """Test profile page for authenticated user."""
        self.client.login(username='profileview', password='testpass123')
        response = self.client.get(reverse('accounts:profile'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'profileview')


class TelegramLinkingViewTest(TestCase):
    """Tests for Telegram linking functionality."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='tglinkuser',
            password='testpass123'
        )
    
    def test_link_telegram_requires_login(self):
        """Test that linking requires authentication."""
        response = self.client.post(reverse('accounts:link_telegram'), {
            'code': 'TESTCODE'
        })
        self.assertEqual(response.status_code, 302)
    
    def test_link_telegram_invalid_code(self):
        """Test linking with invalid code."""
        self.client.login(username='tglinkuser', password='testpass123')
        
        response = self.client.post(reverse('accounts:link_telegram'), {
            'code': 'INVALIDCODE'
        }, follow=True)
        
        # Should redirect to profile with error message
        self.assertEqual(response.status_code, 200)
        
        # Profile should still not have telegram linked
        self.user.refresh_from_db()
        self.assertIsNone(self.user.profile.telegram_chat_id)
    
    def test_link_telegram_valid_code(self):
        """Test linking with valid code."""
        self.client.login(username='tglinkuser', password='testpass123')
        
        # Create a valid link code (as if from Telegram bot)
        TelegramLinkCode.objects.create(
            telegram_chat_id='999888777',
            code='VALIDCDE',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        response = self.client.post(reverse('accounts:link_telegram'), {
            'code': 'VALIDCDE'
        }, follow=True)
        
        self.assertEqual(response.status_code, 200)
        
        # Profile should have telegram linked
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile.telegram_chat_id, '999888777')
    
    def test_unlink_telegram(self):
        """Test unlinking Telegram account."""
        self.client.login(username='tglinkuser', password='testpass123')
        
        # First link
        profile = self.user.profile
        profile.telegram_chat_id = '123456'
        profile.save()
        
        # Then unlink
        response = self.client.post(reverse('accounts:link_telegram'), {
            'action': 'unlink'
        }, follow=True)
        
        self.assertEqual(response.status_code, 200)
        
        # Profile should not have telegram linked
        self.user.refresh_from_db()
        self.assertIsNone(self.user.profile.telegram_chat_id)
