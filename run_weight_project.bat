@echo off
TITLE Xiaomi S400 BLE Monitor
SETLOCAL

:: 1. Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b
)

:: 2. Create a virtual environment (optional but recommended)
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)

:: 3. Activate virtual environment and install requirements
echo [INFO] Activating environment and checking dependencies...
call venv\Scripts\activate
pip install -r requirements.txt

:: 4. Run the script
echo [INFO] Starting S400 BLE Service...
python s400_ble.py

:: Keep window open if it crashes
echo.
echo [INFO] Script stopped.
pause