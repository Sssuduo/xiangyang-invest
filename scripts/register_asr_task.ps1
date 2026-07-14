# ASR 隧道监控 - 任务计划注册脚本（以管理员身份运行 PowerShell）
# 执行: powershell -ExecutionPolicy Bypass -File "h:\项目1\scripts\register_asr_task.ps1"

$TaskName = "ASR Tunnel Monitor"
$ProjectDir = "h:\项目1"
$MonitorScript = "$ProjectDir\scripts\asr_monitor.ps1"

# 1. 清理旧任务（如果存在）
try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "已清理旧任务: $TaskName" -ForegroundColor Yellow
} catch {}

# 2. 定义触发器：登录时 + 工作站解锁时（含休眠唤醒）
$triggers = @(
    New-ScheduledTaskTrigger -AtLogon
    New-ScheduledTaskTrigger -AtLogon -User $env:USERNAME
)

# 3. 定义执行动作
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$MonitorScript`"" `
    -WorkingDirectory $ProjectDir

# 4. 任务设置
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 365) `
    -MultipleInstances IgnoreNew

# 5. 注册任务
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Trigger $triggers `
        -Action $action `
        -Settings $settings `
        -Description "ASR 语音识别 API 隧道监控 - 登录/休眠唤醒时自动启动" `
        -RunLevel Highest `
        -Force

    Write-Host "任务注册成功: $TaskName" -ForegroundColor Green
    Write-Host ""
    Write-Host "验证命令:" -ForegroundColor Cyan
    Write-Host "  Get-ScheduledTask -TaskName '$TaskName' | Get-ScheduledTaskInfo"
    Write-Host ""
    Write-Host "立即启动:" -ForegroundColor Cyan
    Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
} catch {
    Write-Host "任务注册失败: $_" -ForegroundColor Red
    exit 1
}
