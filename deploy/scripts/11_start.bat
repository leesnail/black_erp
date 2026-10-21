@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0..\.."
echo === Start all services (docker compose start) ===
docker compose start
docker compose ps
if not defined NOPAUSE pause
