# One-time SLEEP/WAKE test: wakes the PC 3 minutes from now, posts to the 2 DEMO groups only, then sleeps again.
$ErrorActionPreference = "Stop"
$taskName = "FacebookLessonsBot_TEST"
$script = Join-Path $PSScriptRoot "scheduled_run.py"
$py = Join-Path $PSScriptRoot ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $py)) { $py = (Get-Command pythonw.exe -ErrorAction Stop).Source }

$when = (Get-Date).AddMinutes(3)
$when = $when.AddSeconds(-$when.Second)
$trigger = New-ScheduledTaskTrigger -Once -At $when
$action = New-ScheduledTaskAction -Execute $py -Argument "`"$script`" --test" -WorkingDirectory $PSScriptRoot
$settings = New-ScheduledTaskSettingsSet -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive
Register-ScheduledTask -TaskName $taskName -Trigger $trigger -Action $action -Settings $settings -Principal $principal -Force | Out-Null

powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1
powercfg /SETACTIVE SCHEME_CURRENT

Write-Host ""
Write-Host "=============================================="
Write-Host ("  The PC will wake at " + $when.ToString("HH:mm"))
Write-Host "  Now put the PC to SLEEP (Start > Power > Sleep)."
Write-Host "  It will post to the 2 DEMO groups, then sleep again."
Write-Host "=============================================="
