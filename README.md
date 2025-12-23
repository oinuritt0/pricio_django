# Pricio - Price Comparison Service

🛒 Compare prices between Russian grocery stores Pyaterochka (Пятёрочка) and Magnit (Магнит).

## Features

- 🔍 **Smart Search** - Find products by name, brand, or category with Cyrillic support
- 📊 **Price History** - Track how prices change over time
- 💰 **Price Comparison** - Compare prices between stores for similar products
- ❤️ **Favorites** - Save products to your favorites list
- 🔔 **Price Alerts** - Get notified when prices drop
- 📱 **Telegram Integration** - Receive notifications via Telegram bot

## Tech Stack

- **Backend:** Django 5.0
- **Database:** SQLite (development), PostgreSQL (production)
- **Frontend:** HTML, CSS (custom design system)
- **Scraping:** Selenium, WebDriver Manager
- **Notifications:** python-telegram-bot

## Installation

1. Clone the repository:
```bash
git clone https://github.com/ChargeOnTop/pricio-django.git
cd pricio-django
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Create superuser (optional):
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

7. Open http://localhost:8000 in your browser

## Project Structure

```
pricio-django/
├── pricio/              # Main Django project
│   ├── settings.py      # Project settings
│   ├── urls.py          # URL routing
│   └── wsgi.py          # WSGI config
├── products/            # Products app
│   ├── models.py        # Product, PriceHistory models
│   ├── views.py         # Views for products
│   └── urls.py          # Product URLs
├── accounts/            # User accounts app
│   ├── models.py        # User profile model
│   ├── views.py         # Auth views
│   └── forms.py         # Registration form
├── scrapers/            # Web scrapers app
│   └── management/      # Django management commands
├── templates/           # HTML templates
├── static/              # CSS, JS, images
└── requirements.txt     # Python dependencies
```

## Environment Variables

Create a `.env` file in the root directory:

```env
SECRET_KEY=your-secret-key
DEBUG=True
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_BOT_USERNAME=your-bot-username
```

## License

MIT License

