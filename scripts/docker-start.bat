@echo off
REM Start Pricio in Docker (production mode)

echo Starting Pricio...

REM Build and start containers
docker-compose up -d --build

echo.
echo Pricio is running!
echo.
echo Web:      http://localhost:8000
echo Database: PostgreSQL (pricio_db container)
echo Bot:      Running in background
echo.
echo Commands:
echo   docker-compose logs -f web          - View web logs
echo   docker-compose logs -f telegram_bot - View bot logs
echo   docker-compose exec web python manage.py scrape magnit --full - Run scraper
echo   docker-compose down                 - Stop all services

