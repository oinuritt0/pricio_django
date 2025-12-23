@echo off
cd /d C:\pricio-django
echo === Installing dependencies ===
pip install setuptools --quiet
pip install -r requirements.txt --quiet
pip install undetected-chromedriver --quiet
echo.
echo === Starting 5ka scraper (DEMO mode - first category only) ===
echo.
python manage.py scrape --store=5ka --demo
echo.
echo === Scraper finished ===
echo.
python manage.py shell -c "from products.models import Product; print(f'Total products in DB: {Product.objects.count()}')"
echo.
pause

