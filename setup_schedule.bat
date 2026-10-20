@echo off
cd /d "%~dp0"
echo Creating the scheduled task (wake from sleep at 16:30 / 20:30)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_schedule.ps1"
pause
