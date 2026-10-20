@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat
rem Same as the sleep test but while you are at the PC (hidden Chrome, DEMO groups only)
echo Running hidden test to the 2 DEMO groups... (about 2 minutes)
python scheduled_run.py --test --no-sleep
echo Done. Results are in logs\scheduled.log and logs\scheduled_output.log
pause
