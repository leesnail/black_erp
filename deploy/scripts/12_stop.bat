@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0..\.."
echo === Stop all services, data volumes kept (docker compose stop) ===
docker compose stop
if not defined NOPAUSE pause
