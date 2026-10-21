@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0..\.."
echo === [5/6] Start all services ===

docker compose up -d --build
if errorlevel 1 goto :fail
echo Waiting for services ...
timeout /t 8 /nobreak >nul
docker compose ps
echo.
echo [OK] Started. Open http://^<server-ip^>/ on the intranet
if not defined NOPAUSE pause
exit /b 0

:fail
echo [FAIL] Start failed, see errors above and: docker compose logs
if not defined NOPAUSE pause
exit /b 1
