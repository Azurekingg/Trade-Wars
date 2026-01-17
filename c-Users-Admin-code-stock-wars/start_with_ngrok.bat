@echo off
echo Starting Flask app with ngrok...
echo.

REM Start Flask in background
start "Flask App" cmd /k "python app.py"

REM Wait a moment for Flask to start
timeout /t 3 /nobreak >nul

REM Start ngrok
echo Starting ngrok tunnel...
ngrok http 5000

pause









