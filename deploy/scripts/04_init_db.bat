@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0..\.."
echo === [4/6] Init database ===

if not exist .env (
  echo [FAIL] .env missing, run 02_init_env.bat first
  goto :fail
)

set ROOTPW=black_erp_root
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
  if "%%a"=="MYSQL_ROOT_PASSWORD" set "ROOTPW=%%b"
)

echo [1/2] Start MySQL / Redis ...
docker compose up -d mysql redis
if errorlevel 1 goto :fail

echo [2/2] Wait for MySQL then create tables + seed ...
set /a WAITED=0
:waitmysql
docker compose exec -T mysql mysqladmin ping -uroot -p"%ROOTPW%" --silent >nul 2>&1
if not errorlevel 1 goto :mysqlok
set /a WAITED+=5
if %WAITED% geq 120 (
  echo [FAIL] MySQL not ready in 120s, check: docker compose logs mysql
  goto :fail
)
timeout /t 5 /nobreak >nul
goto :waitmysql

:mysqlok
docker compose run --rm --build app python -m app.init_db
if errorlevel 1 goto :fail
echo [OK] Tables + seed done. Default admin / Admin@12345, reset password after first login
if not defined NOPAUSE pause
exit /b 0

:fail
echo [FAIL] Database init failed
if not defined NOPAUSE pause
exit /b 1
