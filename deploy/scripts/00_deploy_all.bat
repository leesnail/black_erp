@echo off
rem ============================================================
rem  BLACK ERP one-click deploy (runs 01 -> 06 in order)
rem  Usage: double-click, or from cmd:  deploy\scripts\00_deploy_all.bat
rem  Prereq: Docker Desktop installed and running
rem  All steps are idempotent; on failure fix and re-run the step.
rem ============================================================
setlocal enabledelayedexpansion
set "SCRIPT_DIR=%~dp0"
set "NOPAUSE=1"
set "FAILED="

call "%SCRIPT_DIR%01_check_env.bat"
if errorlevel 1 set FAILED=01_check_env
if defined FAILED goto :done

call "%SCRIPT_DIR%02_init_env.bat"
if errorlevel 1 set FAILED=02_init_env
if defined FAILED goto :done

call "%SCRIPT_DIR%03_build_frontend.bat"
if errorlevel 1 set FAILED=03_build_frontend
if defined FAILED goto :done

rem Pause once after .env is created so prod passwords can be edited
if not defined ENV_WARNED (
  echo.
  echo --------------------------------------------------------
  echo For production: edit .env now and set
  echo   MYSQL_ROOT_PASSWORD / MYSQL_PASSWORD
  echo then press Enter to continue.
  echo --------------------------------------------------------
  pause
  set ENV_WARNED=1
)

call "%SCRIPT_DIR%04_init_db.bat"
if errorlevel 1 set FAILED=04_init_db
if defined FAILED goto :done

call "%SCRIPT_DIR%05_start.bat"
if errorlevel 1 set FAILED=05_start
if defined FAILED goto :done

call "%SCRIPT_DIR%06_verify.bat"
if errorlevel 1 set FAILED=06_verify

:done
echo.
if defined FAILED (
  echo [X] Deploy stopped at step %FAILED%
  echo     Fix the issue, then re-run that step script (all steps are idempotent).
  exit /b 1
)
echo [OK] Deploy finished. Open http://^<server-ip^>/  login: admin / Admin@12345
exit /b 0
