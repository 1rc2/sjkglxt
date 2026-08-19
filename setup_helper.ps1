# ============================================================================
#  注册"手机远程启动助手"为开机自启（Windows 任务计划）
#  需以管理员身份运行: powershell -ExecutionPolicy Bypass -File setup_helper.ps1
# ============================================================================
$ErrorActionPreference = 'Stop'

$root   = $PSScriptRoot
$helper = Join-Path $root 'start_helper.py'
if (-not (Test-Path $helper)) { throw "start_helper.py not found: $helper" }

$python = (Get-Command python).Source
$action  = New-ScheduledTaskAction -Execute $python -Argument "`"$helper`"" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName 'SJKGLXT_Helper' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null

Write-Host 'OK: 开机自启已注册 (任务名 SJKGLXT_Helper)'
Start-ScheduledTask -TaskName 'SJKGLXT_Helper'
Write-Host '已立即启动助手，验证:'
Start-Sleep -Seconds 3
try {
    $r = Invoke-RestMethod 'http://127.0.0.1:5001/status' -TimeoutSec 5
    Write-Host ('helper: ok, mysql=' + $r.mysql + ', backend=' + $r.backend)
} catch {
    Write-Host 'helper: 启动中或端口未就绪，请稍后访问 http://127.0.0.1:5001/status'
}
