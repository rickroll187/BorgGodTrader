@echo off
REM BorgGodTrader Windows Launcher
REM Created by Chemothearpy/Eviscerate

REM Activate venv if present
IF EXIST venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Launch Streamlit dashboard
echo Launching BorgGodTrader dashboard...
python -m streamlit run dashboard\streamlit_app.py

pause