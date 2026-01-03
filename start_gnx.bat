@echo off
echo Initializing GNX Environment...

REM Check if .venv exists
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found. Running with system python.
)

echo Starting GNX History Backend (Port 5000)...
start "GNX History Backend" /MIN python chat_backend/app.py

echo Waiting for backend to initialize...
timeout /t 3 >nul

echo Starting GNX CLI...
python main.py

echo.
echo GNX CLI has exited.
echo To stop the backend server, close the "GNX History Backend" window.
pause
