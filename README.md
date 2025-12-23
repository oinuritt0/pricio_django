# Pricio - Price Comparison Service

🛒 Compare prices between Russian grocery stores Pyaterochka (Пятёрочка) and Magnit (Магнит).

![Django](https://img.shields.io/badge/Django-5.0-green)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

- 🔍 **Smart Search** - Find products by name, brand, or category with full Cyrillic support
- 📊 **Price History** - Track how prices change over time with interactive charts
- 💰 **Price Comparison** - Compare prices between stores for similar products
- ❤️ **Favorites** - Save products to your favorites list
- 🔔 **Price Alerts** - Get notified when prices drop
- 📱 **Telegram Integration** - Receive notifications via Telegram bot
- 🎨 **Modern UI** - Clean, responsive design with green-white theme

## Tech Stack

- **Backend:** Django 5.0
- **Database:** SQLite (development), PostgreSQL (production)
- **Frontend:** HTML, CSS (custom design system), Chart.js
- **Scraping:** Selenium, WebDriver Manager
- **Notifications:** python-telegram-bot

## Quick Start

```bash
# Clone repository
git clone https://github.com/oinuritt0/pricio_django.git
cd pricio_django

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Run server
python manage.py runserver
```

Open http://localhost:8000 in your browser.

## Management Commands

```bash
# Scrape products from stores
python manage.py scrape --store=5ka --demo    # Demo mode (first category)
python manage.py scrape --store=5ka           # Full scrape
python manage.py scrape --store=magnit        # Magnit scrape

# Run Telegram bot
python manage.py telegram_bot

# Send price drop notifications
python manage.py notify_price_drops           # One-time check
python manage.py notify_price_drops --daemon  # Continuous monitoring
```

## Project Structure

```
pricio_django/
├── pricio/              # Main Django project settings
├── products/            # Products app (models, views, search)
├── accounts/            # User authentication & profiles
├── scrapers/            # Web scrapers & management commands
├── templates/           # HTML templates
├── static/              # CSS, JS, images
└── requirements.txt     # Python dependencies
```

## Environment Variables

```env
SECRET_KEY=your-secret-key
DEBUG=True
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_BOT_USERNAME=your-bot-username
```

## Authors

- **ChargeOnTop** - Project setup, scrapers, Telegram bot
- **inoed** - Database models, search, notifications

## License

MIT License

