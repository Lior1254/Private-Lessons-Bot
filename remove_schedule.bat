@echo off
echo Removing the Facebook bot scheduled tasks...
schtasks /Delete /TN "FacebookLessonsBot" /F
schtasks /Delete /TN "FacebookLessonsBot_TEST" /F >nul 2>&1
echo.
echo Done. The bot will not run or wake the PC anymore.
echo To turn it back on later: run setup_schedule.bat
pause
