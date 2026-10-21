@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0..\.."
echo === [1/6] Environment check ===

echo [check] Docker ...
docker --version >nul 2>&1
if errorlevel 1 (
  echo [FAIL] Docker Desktop not installed or not running
  goto :fail
)
docker compose version >nul 2>&1
if errorlevel 1 (
  echo [FAIL] Docker Compose v2 not available
  goto :fail
)
echo [OK] Docker + Compose

echo [check] Node.js ...
where node >nul 2>&1
if errorlevel 1 (
  echo [FAIL] node not found, frontend build needs Node 18+
  goto :fail
)
set NODE_MAJOR=0
for /f "delims=v." %%a in ('node -v') do set NODE_MAJOR=%%a
if %NODE_MAJOR% LSS 18 (
  echo [FAIL] Node version too old ^(%NODE_MAJOR%^), need 18+
  goto :fail
)
echo [OK] Node %NODE_MAJOR%

echo [check] Python (optional, native deploy only) ...
where python >nul 2>&1
if errorlevel 1 (
  echo [WARN] python not found, not required for Docker deploy
) else (
  python --version 2>&1
)

echo [check] Port 80 ...
netstat -ano | findstr /c:":80 " | findstr LISTENING >nul 2>&1
if not errorlevel 1 (
  echo [WARN] Port 80 already in use, check it is not IIS / another nginx
)

echo [check] .env ...
if exist .env (
  echo [OK] .env exists
) else (
  echo [WARN] .env missing, run 02_init_env.bat next
)

echo.
echo Environment check passed (WARN items are non-blocking)
if not defined NOPAUSE pause
exit /b 0

:fail
echo.
echo Environment check FAILED, fix the issues above first
if not defined NOPAUSE pause
exit /b 1
