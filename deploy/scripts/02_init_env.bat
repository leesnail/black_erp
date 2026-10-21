@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0..\.."
echo === [2/6] Generate .env ===

if exist .env (
  echo [SKIP] .env already exists, delete it first if you want to regenerate
  if not defined NOPAUSE pause
  exit /b 0
)

copy /y .env.example .env >nul
if errorlevel 1 (
  echo [FAIL] cannot copy .env.example
  goto :fail
)

set SECRET=
for /f %%i in ('powershell -NoProfile -Command "[guid]::NewGuid().ToString('N')+[guid]::NewGuid().ToString('N')"') do set SECRET=%%i
powershell -NoProfile -Command "(Get-Content .env -Raw -Encoding UTF8) -replace 'SECRET_KEY=.*', ('SECRET_KEY=' + '%SECRET%') | Set-Content .env -Encoding UTF8 -NoNewline"

echo [OK] .env generated, SECRET_KEY randomized
echo [TODO] For production: edit .env and set MYSQL_ROOT_PASSWORD / MYSQL_PASSWORD before first MySQL start
if not defined NOPAUSE pause
exit /b 0

:fail
if not defined NOPAUSE pause
exit /b 1
