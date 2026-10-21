@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0..\.."
echo === [3/6] Build frontend ===

pushd frontend
if errorlevel 1 goto :fail
call npm install --no-fund --no-audit
if errorlevel 1 (
  popd
  goto :fail
)
call npm run build
if errorlevel 1 (
  popd
  goto :fail
)
popd

if not exist frontend\dist\index.html (
  echo [FAIL] frontend\dist\index.html not produced
  goto :fail
)
echo [OK] frontend\dist built
if not defined NOPAUSE pause
exit /b 0

:fail
echo [FAIL] frontend build failed
if not defined NOPAUSE pause
exit /b 1
