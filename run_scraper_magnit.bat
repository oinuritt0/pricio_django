@echo off
cd /d C:\pricio-django
echo === Installing dependencies ===
pip install -r requirements.txt --quiet
echo.
echo === Starting MAGNIT scraper (DEMO mode - first category only) ===
echo.
python manage.py scrape --store=magnit --demo
echo.
echo === Scraper finished ===
echo.
python manage.py shell -c "from products.models import Product; print(f'Total products in DB: {Product.objects.count()}')"
echo.
pause

