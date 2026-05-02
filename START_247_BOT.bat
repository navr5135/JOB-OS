@echo off
echo Waking up the Job Search OS 24/7 Daemon...
echo.
echo The Telegram bot is now online! You can close this window.
echo The system will run silently in the background and automatically fire at 09:00 AM.
echo (To stop the bot, type /stop in Telegram or kill pythonw.exe in Task Manager).
echo.
start /B pythonw main.py
pause
