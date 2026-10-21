@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0..\.."
echo === [6/6] Deployment verify ===

docker compose ps
echo.

echo [check] /health ...
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 http://127.0.0.1/health; Write-Host ('[OK] /health -> ' + $r.Content) } catch { Write-Host ('[FAIL] ' + $_.Exception.Message); exit 1 }"
if errorlevel 1 goto :fail

echo [check] Login page ...
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 http://127.0.0.1/; if ($r.StatusCode -eq 200) { Write-Host '[OK] login page HTTP 200' } else { exit 1 } } catch { Write-Host ('[FAIL] ' + $_.Exception.Message); exit 1 }"
if errorlevel 1 goto :fail

echo.
echo Deploy verify PASSED.
echo Open http://^<server-ip^>/ and login: admin / Admin@12345 (reset password immediately)
echo Business smoke: add a spec -> upload test CSV -> batch status success -> audit log has records
if not defined NOPAUSE pause
exit /b 0

:fail
echo.
echo Deploy verify FAILED, check containers and: docker compose logs app
if not defined NOPAUSE pause
exit /b 1
