@echo off
REM Start Pricio in Docker (development mode with hot reload)

echo Starting Pricio (development mode)...

REM Start with dev compose file
docker-compose -f docker-compose.dev.yml up --build

echo.
echo Development server stopped.

