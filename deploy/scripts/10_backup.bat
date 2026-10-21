@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0..\.."
echo === Backup (MySQL dump + uploads + config) ===

set TS=
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmm"') do set TS=%%i
set "BKDIR=backup\%TS%"
mkdir "%BKDIR%" 2>nul

set ROOTPW=black_erp_root
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
  if "%%a"=="MYSQL_ROOT_PASSWORD" set "ROOTPW=%%b"
)

echo [1/3] Dump MySQL ...
docker compose exec -T mysql sh -c "mysqldump -uroot -p\"$MYSQL_ROOT_PASSWORD\" --single-transaction --routines --triggers black_erp" > "%BKDIR%\black_erp.sql"
if errorlevel 1 goto :fail
for %%a in ("%BKDIR%\black_erp.sql") do if %%~za LSS 100 (
  echo [FAIL] dump file too small, likely failed
  goto :fail
)
echo [OK] %BKDIR%\black_erp.sql

echo [2/3] Pack uploads ...
docker compose exec -T app tar czf - -C /data/uploads . > "%BKDIR%\uploads.tgz" 2>nul
if exist "%BKDIR%\uploads.tgz" (
  echo [OK] %BKDIR%\uploads.tgz
) else (
  echo [WARN] uploads dir empty or unreadable, skipped
)

echo [3/3] Backup config ...
copy /y .env "%BKDIR%\.env" >nul
copy /y docker-compose.yml "%BKDIR%\docker-compose.yml" >nul
echo [OK] config backed up

echo.
echo Backup done: %BKDIR%
echo Restore: docker compose exec -T mysql mysql -uroot -p^<ROOT_PW^> black_erp ^< black_erp.sql
if not defined NOPAUSE pause
exit /b 0

:fail
echo [FAIL] Backup failed
if not defined NOPAUSE pause
exit /b 1
