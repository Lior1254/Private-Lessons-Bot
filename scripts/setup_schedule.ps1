# Creates the Windows scheduled task for the Facebook bot.
# Wakes the PC from sleep at 16:30 (Sun-Fri) and 20:30 (Sun-Thu + Saturday night).
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent   # the project folder (this file lives in scripts\)
$taskName = "FacebookLessonsBot"
$script = Join-Path $root "scheduled_run.py"
# pythonw = Python without a console window, so nothing pops up while you work
$py = Join-Path $root ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $py)) { $py = (Get-Command pythonw.exe -ErrorAction Stop).Source }
Write-Host "Using: $py"

$triggers = @(
  (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday,Monday,Tuesday,Wednesday,Thursday,Friday -At "16:30"),
  (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday,Monday,Tuesday,Wednesday,Thursday,Saturday -At "20:30")
)
$action = New-ScheduledTaskAction -Execute $py -Argument "`"$script`"" -WorkingDirectory $root
$settings = New-ScheduledTaskSettingsSet -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive

Register-ScheduledTask -TaskName $taskName -Trigger $triggers -Action $action -Settings $settings `
  -Principal $principal -Description "Posts private-lesson ads to Facebook groups" -Force | Out-Null
Write-Host "OK - scheduled task '$taskName' created."

# Allow wake timers (needed so Windows can wake the PC for the task)
powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1
powercfg /SETACTIVE SCHEME_CURRENT
Write-Host "OK - wake timers allowed in the current power plan."
