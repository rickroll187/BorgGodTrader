@echo off
title BorgGodTrader - Crypto Trading Dashboard
color 0A

echo.
echo  ===============================================
echo        BorgGodTrader - Trading Dashboard
echo  ===============================================
echo.

cd /d "%~dp0"

:: Check for .env
if not exist ".env" (
    echo [!] No .env file found. Creating from template...
    if exist ".env.example" (
        copy .env.example .env
        echo [+] Created .env - Please edit with your API keys
    )
)

:: Check for virtual environment
if exist "venv\Scripts\activate.bat" (
    echo [+] Activating virtual environment...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo [+] Activating virtual environment...
    call .venv\Scripts\activate.bat
)

echo [+] Starting dashboard...
echo [*] Dashboard will open at: http://localhost:8501
echo.

streamlit run dashboard/advanced_dashboard.py ^
    --server.port=8501 ^
    --server.headless=false ^
    --browser.gatherUsageStats=false ^
    --theme.base=dark ^
    --theme.primaryColor=#00d4aa

pause
