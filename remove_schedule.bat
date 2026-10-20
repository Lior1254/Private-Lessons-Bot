@echo off
echo Removing the scheduled task...
schtasks /Delete /TN "FacebookLessonsBot" /F
pause
