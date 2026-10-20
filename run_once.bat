@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat
rem Real run to all groups now, with Chrome visible so you can watch
set BOT_SHOW=1
python bot.py
pause
