@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0..\.."
echo === Tail logs: app / worker / beat (Ctrl+C to exit) ===
docker compose logs -f --tail 200 app worker beat
if not defined NOPAUSE pause
