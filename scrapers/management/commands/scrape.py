# -*- coding: utf-8 -*-
"""
Django management command for scraping products.
Based on proven scraper_v2.py from Flask version.
Usage: python manage.py scrape --store=5ka --demo
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from django.core.management.base import BaseCommand
from products.models import Store, Product, PriceHistory, Category
from decimal import Decimal
from datetime import datetime
import time
import json


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

    def handle(self, *args, **options):
        store_id = options['store']
        demo = options['demo']
        
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
            self.scrape_5ka(store, demo)
        else:
            self.scrape_magnit(store, demo)

    def scrape_5ka(self, store, demo):
        """Scrape Pyaterochka using undetected-chromedriver."""
        try:
            import undetected_chromedriver as uc
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except ImportError:
            self.stdout.write(self.style.ERROR("Install: pip install undetected-chromedriver selenium"))
            return
        
        print("="*60)
        if demo:
            print("  СКРАПЕР ПЯТЁРОЧКА - ДЕМО (только 1 категория)")
        else:
            print("  СКРАПЕР ПЯТЁРОЧКА - ВСЕ КАТЕГОРИИ")
        print("="*60)
        print("  (используется undetected-chromedriver)")
        print("="*60)
        
        options = uc.ChromeOptions()
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        
        driver = uc.Chrome(options=options, use_subprocess=True)
        
        all_products = []
        seen_ids = set()
        
        try:
            # Load catalog
            print("\n[*] Загрузка каталога...")
            driver.get("https://5ka.ru/catalog/")
            time.sleep(3)
            
            print("\n" + "="*60)
            print(">>> Если появилась капча - пройдите её в браузере")
            input(">>> Нажмите ENTER когда каталог загрузится... ")
            print("="*60)
            
            # Get categories from __NEXT_DATA__
            print("\n[*] Получение категорий...")
            categories = []
            
            try:
                script = driver.find_element(By.ID, "__NEXT_DATA__")
                data = json.loads(script.get_attribute("innerHTML"))
                
                props = data.get("props", {}).get("pageProps", {}).get("props", {})
                catalog_store = props.get("catalogStore", "{}")
                
                if isinstance(catalog_store, str):
                    catalog_store = json.loads(catalog_store)
                
                sections = catalog_store.get("_sections", [])
                
                for section in sections:
                    cat_id = section.get("id", "")
                    cat_name = section.get("name", "")
                    if cat_id and cat_name:
                        categories.append({"id": cat_id, "name": cat_name})
                
                print(f"[OK] Найдено {len(categories)} категорий")
                
            except Exception as e:
                print(f"[!] Ошибка получения категорий: {e}")
                driver.quit()
                return
            
            if demo:
                categories = categories[:1]
                print(f"\n[ДЕМО] Обрабатываем только: {categories[0]['name']}")
            
            total_categories = len(categories)
            print(f"\n[*] Категорий к обработке: {total_categories}")
            print("-"*60)
            
            # Process each category
            for i, cat in enumerate(categories, 1):
                cat_id = cat["id"]
                cat_name = cat["name"]
                
                print(f"\n[{i}/{total_categories}] {cat_name}...")
                
                # Navigate to category
                url = f"https://5ka.ru/catalog/{cat_id}/"
                driver.get(url)
                time.sleep(3)
                
                # Check for captcha
                if "captcha" in driver.page_source.lower():
                    print("    [!] Обнаружена капча! Пройдите её в браузере...")
                    input("    >>> Нажмите ENTER после прохождения... ")
                    time.sleep(2)
                
                # Wait for products
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div[itemtype="https://schema.org/ItemList"], a[href*="/product/"]'))
                    )
                except:
                    print("    [!] Товары не найдены, пропускаем")
                    continue
                
                # Scroll to load all products
                print("    Прокрутка...", end=" ", flush=True)
                scroll_count = 0
                no_change_count = 0
                last_product_count = 0
                
                while scroll_count < 200 and no_change_count < 5:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.8)
                    
                    current_count = driver.execute_script('''
                        var items = document.querySelectorAll('div[itemprop="itemListElement"], a[href*="/product/"]');
                        return items.length;
                    ''')
                    
                    if current_count == last_product_count:
                        no_change_count += 1
                    else:
                        no_change_count = 0
                        last_product_count = current_count
                    
                    scroll_count += 1
                    
                    # Check captcha every 10 scrolls
                    if scroll_count % 10 == 0:
                        if "captcha" in driver.page_source.lower():
                            print("\n    [!] Капча! Пройдите в браузере...")
                            input("    >>> ENTER после прохождения... ")
                            no_change_count = 0
                
                print(f"({scroll_count} раз)")
                time.sleep(1)
                
                # Extract products via JavaScript
                print("    Извлечение товаров...", end=" ", flush=True)
                
                products_data = driver.execute_script('''
                    var products = [];
                    var seenIds = new Set();
                    
                    // Method 1: schema.org ItemList
                    var items = document.querySelectorAll('div[itemprop="itemListElement"]');
                    
                    items.forEach(function(item) {
                        try {
                            var product = {};
                            var html = item.outerHTML || '';
                            
                            // Link and ID
                            var link = item.querySelector('a[href*="/product/"]');
                            if (link) {
                                product.url = link.href || '';
                                var match = product.url.match(/--(\\d+)\\/?$/);
                                if (match) product.id = match[1];
                            }
                            
                            if (!product.id || seenIds.has(product.id)) return;
                            seenIds.add(product.id);
                            
                            // Name from meta
                            var nameMeta = item.querySelector('meta[itemprop="name"]');
                            if (nameMeta) {
                                product.name = nameMeta.getAttribute('content') || '';
                            }
                            if (!product.name && link) {
                                product.name = link.title || link.textContent.trim() || '';
                            }
                            
                            // Price from offers
                            var offersPos = html.indexOf('itemprop="offers"');
                            if (offersPos > 0) {
                                var afterOffers = html.substring(offersPos);
                                var priceMatches = afterOffers.match(/itemprop="price"[^>]*content="([\\d.]+)"/g) || [];
                                var prices = [];
                                priceMatches.forEach(function(m) {
                                    var p = m.match(/content="([\\d.]+)"/);
                                    if (p) prices.push(parseFloat(p[1]));
                                });
                                
                                if (prices.length > 0) {
                                    product.price = Math.min.apply(null, prices);
                                }
                            }
                            
                            // Fallback price
                            if (!product.price) {
                                var allPrices = html.match(/itemprop="price"[^>]*content="([\\d.]+)"/g) || [];
                                var validPrices = [];
                                allPrices.forEach(function(m) {
                                    var p = m.match(/content="([\\d.]+)"/);
                                    if (p && parseFloat(p[1]) > 10) validPrices.push(parseFloat(p[1]));
                                });
                                if (validPrices.length > 0) {
                                    product.price = Math.min.apply(null, validPrices);
                                }
                            }
                            
                            if (product.id && product.name) {
                                products.push(product);
                            }
                        } catch(e) {}
                    });
                    
                    // Method 2: fallback via product links
                    if (products.length === 0) {
                        var links = document.querySelectorAll('a[href*="/product/"]');
                        
                        links.forEach(function(link) {
                            try {
                                var href = link.href || '';
                                var match = href.match(/--(\\d+)\\/?$/);
                                if (!match) return;
                                
                                var productId = match[1];
                                if (seenIds.has(productId)) return;
                                seenIds.add(productId);
                                
                                // Find card container
                                var card = link;
                                for (var i = 0; i < 7; i++) {
                                    if (card.parentElement) {
                                        var parent = card.parentElement;
                                        if (parent.textContent && parent.textContent.includes('₽')) {
                                            card = parent;
                                            break;
                                        }
                                        if (parent.textContent && parent.textContent.length > card.textContent.length) {
                                            card = parent;
                                        }
                                    }
                                }
                                
                                var cardHtml = card.outerHTML || '';
                                var product = {id: productId, url: href, name: '', price: 0};
                                
                                // Name
                                var nameMeta = card.querySelector('meta[itemprop="name"]');
                                if (nameMeta) product.name = nameMeta.getAttribute('content') || '';
                                if (!product.name) product.name = link.title || '';
                                if (!product.name) {
                                    var img = card.querySelector('img[alt]');
                                    if (img && img.alt) product.name = img.alt;
                                }
                                
                                // Price
                                var priceMatches = cardHtml.match(/content="([\\d.]+)"/g) || [];
                                var prices = [];
                                priceMatches.forEach(function(m) {
                                    var p = m.match(/"([\\d.]+)"/);
                                    if (p) {
                                        var val = parseFloat(p[1]);
                                        if (val > 1 && val < 100000) prices.push(val);
                                    }
                                });
                                
                                if (prices.length > 0) {
                                    product.price = Math.min.apply(null, prices);
                                }
                                
                                if (product.name) products.push(product);
                            } catch(e) {}
                        });
                    }
                    
                    return products;
                ''')
                
                print(f"найдено {len(products_data)}")
                
                # Save to Django DB
                new_count = 0
                for p in products_data:
                    product_id = p.get('id', '')
                    if not product_id or product_id in seen_ids:
                        continue
                    seen_ids.add(product_id)
                    
                    name = p.get('name', '')
                    price = Decimal(str(p.get('price', 0) or 0))
                    
                    if not name:
                        continue
                    
                    # Get or create category
                    category, _ = Category.objects.get_or_create(
                        name=cat_name,
                        store=store
                    )
                    
                    # Update or create product
                    product, created = Product.objects.update_or_create(
                        store=store,
                        product_id=product_id,
                        defaults={
                            'name': name,
                            'category': category,
                            'category_name': cat_name,
                            'current_price': price,
                        }
                    )
                    
                    if created:
                        product.min_price = price
                        product.max_price = price
                        product.save()
                        new_count += 1
                    else:
                        # Update price tracking
                        if product.current_price != price and price > 0:
                            PriceHistory.objects.create(
                                product=product,
                                price=price,
                                previous_price=product.current_price
                            )
                            if price < product.min_price or product.min_price == 0:
                                product.min_price = price
                            if price > product.max_price:
                                product.max_price = price
                            product.current_price = price
                            product.save()
                    
                    all_products.append(p)
                
                print(f"    Сохранено: {len(products_data)} | Новых: {new_count} | Всего: {len(all_products)}")
                
                if not demo:
                    time.sleep(1)
            
            print("\n" + "="*60)
            print(f"[OK] ИТОГО: {len(all_products)} товаров в базе")
            print("="*60)
            
            # Show examples
            if all_products:
                print("\nПримеры:")
                for p in all_products[:5]:
                    name = (p.get('name', '') or '')[:50]
                    price = p.get('price', 0)
                    print(f"  - {name}... {price} руб.")
            
        finally:
            driver.quit()
            print("\n[OK] Готово!")

    def scrape_magnit(self, store, demo):
        """Scrape Magnit using proven method."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from webdriver_manager.chrome import ChromeDriverManager
        except ImportError:
            self.stdout.write(self.style.ERROR("Selenium not installed. Run: pip install selenium webdriver-manager"))
            return
        
        print("="*60)
        if demo:
            print("  СКРАПЕР МАГНИТ - ДЕМО (только 1 категория)")
        else:
            print("  СКРАПЕР МАГНИТ - ВСЕ КАТЕГОРИИ")
        print("="*60)
        
        options = Options()
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        base_url = "https://magnit.ru"
        all_products = []
        seen_ids = set()
        
        def close_popups():
            """Close popup dialogs"""
            try:
                cookie_btn = driver.find_element(By.XPATH, "//*[contains(text(), 'Хорошо, закрыть')]")
                cookie_btn.click()
                time.sleep(0.5)
            except:
                pass
            try:
                not_now = driver.find_element(By.XPATH, "//*[contains(text(), 'Не сейчас')]")
                not_now.click()
                time.sleep(0.5)
            except:
                pass
        
        try:
            # Load catalog
            print("\n[*] Загрузка каталога...")
            driver.get(f"{base_url}/catalog/")
            time.sleep(3)
            close_popups()
            
            print("\n" + "="*60)
            print(">>> Нажмите ENTER когда каталог загрузится...")
            input()
            print("="*60)
            
            # Get categories
            print("\n[*] Получение категорий...")
            categories = []
            
            links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/catalog/"]')
            seen_urls = set()
            
            for link in links:
                try:
                    href = link.get_attribute("href") or ""
                    text = link.text.strip()
                    
                    if not href or href.endswith('/catalog/') or href.endswith('/catalog') or not text:
                        continue
                    
                    if href.startswith(base_url):
                        href = href[len(base_url):]
                    
                    if 'promokod' in href.lower():
                        continue
                    
                    if href not in seen_urls and len(text) > 2:
                        seen_urls.add(href)
                        categories.append({"name": text[:50], "url": href})
                except:
                    continue
            
            print(f"[OK] Найдено {len(categories)} категорий")
            
            if demo:
                categories = categories[:1]
                print(f"\n[ДЕМО] Обрабатываем только: {categories[0]['name']}")
            
            total_categories = len(categories)
            print(f"\n[*] Категорий к обработке: {total_categories}")
            print("-"*60)
            
            # Process each category
            for i, cat in enumerate(categories, 1):
                cat_name = cat['name']
                cat_url = cat['url']
                
                print(f"\n[{i}/{total_categories}] {cat_name}...")
                
                driver.get(f"{base_url}{cat_url}")
                time.sleep(2)
                close_popups()
                
                # Wait for products
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'article[data-test-id="v-product-preview"]'))
                    )
                except:
                    print("    [!] Товары не найдены, пропускаем")
                    continue
                
                # Load all products by clicking "Show more"
                clicks = 0
                fails = 0
                
                while clicks < 100 and fails < 3:
                    try:
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(0.8)
                        
                        clicked = driver.execute_script('''
                            var btn = document.querySelector('button[data-test-id="v-pagination-show-more-button"]');
                            if (btn && btn.offsetParent !== null) {
                                btn.scrollIntoView({behavior: 'instant', block: 'center'});
                                btn.click();
                                return true;
                            }
                            return false;
                        ''')
                        
                        if clicked:
                            clicks += 1
                            fails = 0
                            time.sleep(1.2)
                        else:
                            fails += 1
                            time.sleep(0.5)
                    except:
                        fails += 1
                        time.sleep(0.5)
                
                if clicks > 0:
                    print(f"    [+] Нажато 'Показать ещё': {clicks} раз")
                
                # Extract products
                print("    [*] Извлекаю товары...", end=" ", flush=True)
                
                products_data = driver.execute_script('''
                    var products = [];
                    var articles = document.querySelectorAll('article[data-test-id="v-product-preview"]');
                    
                    articles.forEach(function(article) {
                        try {
                            var product = {};
                            
                            // Link and ID
                            var link = article.querySelector('a[href*="/product/"]');
                            if (link) {
                                product.url = link.href || '';
                                product.name = link.title || '';
                                var match = product.url.match(/\\/product\\/(\\d+)/);
                                if (match) product.id = match[1];
                            }
                            
                            // Name fallback
                            if (!product.name) {
                                var titleEl = article.querySelector('.unit-catalog-product-preview-title');
                                if (titleEl) product.name = titleEl.textContent.trim();
                            }
                            
                            // Price
                            var priceEl = article.querySelector('.unit-catalog-product-preview-prices__regular');
                            if (priceEl) {
                                var priceText = priceEl.textContent.replace('₽', '').replace(/\\s/g, '').replace(',', '.');
                                product.price = parseFloat(priceText) || 0;
                            }
                            
                            // Rating
                            var ratingEl = article.querySelector('.unit-catalog-product-preview-rating-score');
                            if (ratingEl) product.rating = parseFloat(ratingEl.textContent) || 0;
                            
                            if (product.id && product.name) {
                                products.push(product);
                            }
                        } catch(e) {}
                    });
                    
                    return products;
                ''')
                
                print(f"найдено {len(products_data)}")
                
                # Save to Django DB
                new_count = 0
                for p in products_data:
                    product_id = p.get('id', '')
                    if not product_id or product_id in seen_ids:
                        continue
                    seen_ids.add(product_id)
                    
                    name = p.get('name', '')
                    price = Decimal(str(p.get('price', 0) or 0))
                    
                    if not name:
                        continue
                    
                    # Get or create category
                    category, _ = Category.objects.get_or_create(
                        name=cat_name,
                        store=store
                    )
                    
                    # Update or create product
                    product, created = Product.objects.update_or_create(
                        store=store,
                        product_id=product_id,
                        defaults={
                            'name': name,
                            'category': category,
                            'category_name': cat_name,
                            'current_price': price,
                        }
                    )
                    
                    if created:
                        product.min_price = price
                        product.max_price = price
                        product.save()
                        new_count += 1
                    else:
                        if product.current_price != price and price > 0:
                            PriceHistory.objects.create(
                                product=product,
                                price=price,
                                previous_price=product.current_price
                            )
                            if price < product.min_price or product.min_price == 0:
                                product.min_price = price
                            if price > product.max_price:
                                product.max_price = price
                            product.current_price = price
                            product.save()
                    
                    all_products.append(p)
                
                print(f"    Сохранено: {len(products_data)} | Новых: {new_count} | Всего: {len(all_products)}")
                
                if not demo:
                    time.sleep(1)
            
            print("\n" + "="*60)
            print(f"[OK] ИТОГО: {len(all_products)} товаров в базе")
            print("="*60)
            
            # Show examples
            if all_products:
                print("\nПримеры:")
                for p in all_products[:5]:
                    name = (p.get('name', '') or '')[:40]
                    price = p.get('price', 0)
                    print(f"  - {name}... {price} руб.")
            
        finally:
            driver.quit()
            print("\n[OK] Готово!")
