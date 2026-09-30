@echo off
REM ============================================================
REM  Starts the already-installed Perennia v2 backend (which also
REM  serves the built public site and admin dashboard). Run
REM  installer.bat first if you haven't yet - this just starts
REM  what it already set up.
REM
REM      start_server.bat
REM ============================================================
setlocal
title Perennia Server

set "ROOT_DIR=%~dp0"
set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "VENV_PY=%BACKEND_DIR%\venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo [ERROR] Backend is not set up yet - the virtual environment is missing.
    echo         Run installer.bat first.
    echo.
    pause
    exit /b 1
)

cd /d "%BACKEND_DIR%"
echo Perennia server starting...
echo.
echo   Public site        http://localhost:8001/
echo   Admin dashboard    http://localhost:8001/admin
echo.
echo Leave this window open while you use the site.
echo Press Ctrl+C to stop the server.
echo.

"%VENV_PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8001

echo.
echo Server stopped.
pause
endlocal
