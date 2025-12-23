"""
Django management command for scraping products.
Usage: python manage.py scrape --store=5ka --demo
"""
from django.core.management.base import BaseCommand
from products.models import Store, Product, PriceHistory
from decimal import Decimal
import time
import json
import re


class Command(BaseCommand):
    help = 'Scrape products from stores (5ka, magnit)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--store',
            type=str,
            default='5ka',
            choices=['5ka', 'magnit'],
            help='Store to scrape (5ka or magnit)'
        )
        parser.add_argument(
            '--demo',
            action='store_true',
            help='Demo mode - scrape only first category'
        )
        parser.add_argument(
            '--headless',
            action='store_true',
            default=True,
            help='Run browser in headless mode'
        )

    def handle(self, *args, **options):
        store_id = options['store']
        demo = options['demo']
        headless = options['headless']
        
        self.stdout.write(f"Starting scraper for {store_id}...")
        
        # Ensure store exists
        store, created = Store.objects.get_or_create(
            store_id=store_id,
            defaults={
                'name': 'Пятёрочка' if store_id == '5ka' else 'Магнит',
                'color': '#e30613' if store_id == '5ka' else '#e31e24',
                'icon': '5' if store_id == '5ka' else 'М',
            }
        )
        
        if store_id == '5ka':
            self.scrape_5ka(store, demo, headless)
        else:
            self.scrape_magnit(store, demo, headless)
        
        self.stdout.write(self.style.SUCCESS(f"Scraping completed for {store_id}!"))

    def scrape_5ka(self, store, demo, headless):
        """Scrape Pyaterochka."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from webdriver_manager.chrome import ChromeDriverManager
        except ImportError:
            self.stdout.write(self.style.ERROR("Selenium not installed. Run: pip install selenium webdriver-manager"))
            return
        
        options = Options()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        try:
            base_url = "https://5ka.ru"
            driver.get(base_url)
            time.sleep(3)
            
            # Get categories
            self.stdout.write("Getting categories...")
            categories = driver.execute_script("""
                return Array.from(document.querySelectorAll('a[href*="/catalog/"]'))
                    .map(a => ({name: a.textContent.trim(), url: a.href}))
                    .filter(c => c.name && c.url.includes('/catalog/'));
            """)
            
            if demo:
                categories = categories[:1]
                self.stdout.write(f"Demo mode: processing 1 category")
            
            total_products = 0
            
            for cat in categories:
                self.stdout.write(f"Processing: {cat['name']}")
                driver.get(cat['url'])
                time.sleep(2)
                
                # Scroll to load all products
                last_height = driver.execute_script("return document.body.scrollHeight")
                while True:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height
                
                # Extract products
                products_data = driver.execute_script("""
                    return Array.from(document.querySelectorAll('[data-product-id]')).map(el => ({
                        id: el.getAttribute('data-product-id'),
                        name: el.querySelector('[class*="ProductCard_title"]')?.textContent?.trim() || '',
                        price: el.querySelector('[class*="Price_price"]')?.textContent?.replace(/[^0-9.,]/g, '') || '0'
                    })).filter(p => p.id && p.name);
                """)
                
                for p in products_data:
                    try:
                        price_str = p['price'].replace(',', '.').replace(' ', '')
                        price = Decimal(price_str) if price_str else Decimal('0')
                        
                        product, created = Product.objects.update_or_create(
                            store=store,
                            product_id=p['id'],
                            defaults={
                                'name': p['name'],
                                'category_name': cat['name'],
                                'current_price': price,
                            }
                        )
                        
                        if created:
                            product.min_price = price
                            product.max_price = price
                            product.save()
                        else:
                            # Update price history
                            if product.current_price != price:
                                PriceHistory.objects.create(
                                    product=product,
                                    price=price,
                                    previous_price=product.current_price
                                )
                                product.current_price = price
                                if price < product.min_price or product.min_price == 0:
                                    product.min_price = price
                                if price > product.max_price:
                                    product.max_price = price
                                product.save()
                        
                        total_products += 1
                    except Exception as e:
                        self.stdout.write(f"Error saving product: {e}")
                
                self.stdout.write(f"  Found {len(products_data)} products")
            
            self.stdout.write(f"Total products processed: {total_products}")
            
        finally:
            driver.quit()

    def scrape_magnit(self, store, demo, headless):
        """Scrape Magnit."""
        self.stdout.write("Magnit scraper - similar implementation...")
        # Similar implementation for Magnit

