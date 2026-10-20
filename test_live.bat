@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat
rem Visible Chrome, posts ONLY to the 2 demo groups, 12 seconds between them
set BOT_SHOW=1
set BOT_DEMO=1
python main_once.py
