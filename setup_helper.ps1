# ============================================================================
#  Register "Mobile Remote Start Helper" as auto-start (Windows Task Scheduler)
#  Double-click install_autostart.bat as Administrator, or run:
#    powershell -ExecutionPolicy Bypass -File setup_helper.ps1
# ============================================================================
$ErrorActionPreference = 'Stop'

$root   = $PSScriptRoot
$helper = Join-Path $root 'start_helper.py'
if (-not (Test-Path $helper)) { throw "start_helper.py not found: $helper" }

$python = (Get-Command python).Source
$action  = New-ScheduledTaskAction -Execute $python -Argument "`"$helper`"" -WorkingDirectory $root

# Double triggers: at startup AND at user logon - whichever fires first starts the helper
$trigger = @(
    New-ScheduledTaskTrigger -AtStartup,
    New-ScheduledTaskTrigger -AtLogOn -User "$env:USERNAME"
)

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest

# IgnoreNew: do not start another instance if the helper is already running
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName 'SJKGLXT_Helper' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null

Write-Host 'OK: auto-start registered (task: SJKGLXT_Helper)'
Start-ScheduledTask -TaskName 'SJKGLXT_Helper'
Write-Host 'Helper started. Verifying...'
Start-Sleep -Seconds 3
try {
    $r = Invoke-RestMethod 'http://127.0.0.1:5001/status' -TimeoutSec 5
    Write-Host ('helper: ok, mysql=' + $r.mysql + ', backend=' + $r.backend)
} catch {
    Write-Host 'helper: starting or port not ready, visit http://127.0.0.1:5001/status later'
}
