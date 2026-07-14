# ASR 隧道监控脚本（PowerShell）
# 每 30 秒检查隧道是否存活，断线则自动重连
# 开机启动/休眠唤醒后由任务计划程序调用

$PROJECT_DIR = "h:\项目1"
$LOG_DIR = "$PROJECT_DIR\scripts"
$ASR_PORT = 5002
$REMOTE_PORT = 15002
$SERVER = "root@123.56.9.243"
$SSH_KEY = "$env:USERPROFILE\.ssh\id_ed25519"
$LOG_FILE = "$LOG_DIR\asr_monitor.log"

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts $msg" | Tee-Object -FilePath $LOG_FILE -Append
}

function Test-Tunnel {
    try {
        $result = curl.exe -s --max-time 5 http://localhost:15002/health 2>$null
        if ($result -match '"status":\s*"ok"') { return $true }
    } catch {}
    return $false
}

function Test-AsrLocal {
    try {
        $result = curl.exe -s --max-time 3 http://localhost:5002/health 2>$null
        if ($result -match '"status":\s*"ok"') { return $true }
    } catch {}
    return $false
}

function Start-AsrTunnel {
    Write-Log "[INFO] 正在建立隧道..."

    # 确保 ASR API 在运行
    if (-not (Test-AsrLocal)) {
        Write-Log "[INFO] 启动 ASR API..."
        Set-Location "$PROJECT_DIR\backend"
        Start-Process -FilePath "python" -ArgumentList "services/asr_api.py","--port","5002" -WindowStyle Hidden -RedirectStandardOutput "$LOG_DIR\asr_api.log" -RedirectStandardError "$LOG_DIR\asr_api_err.log"
        Start-Sleep -Seconds 10
    }

    # 建立隧道（后台）
    $sshArgs = @(
        "-i", $SSH_KEY,
        "-o", "StrictHostKeyChecking=no",
        "-o", "ServerAliveInterval=60",
        "-o", "ServerAliveCountMax=3",
        "-o", "ExitOnForwardFailure=yes",
        "-N", "-R", "${REMOTE_PORT}:localhost:${ASR_PORT}",
        $SERVER
    )
    Start-Process -FilePath "ssh" -ArgumentList $sshArgs -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

# === 主循环 ===
Write-Log "=== ASR 监控启动 ==="

while ($true) {
    if (Test-Tunnel) {
        Write-Log "[OK] 隧道正常"
    } else {
        Write-Log "[WARN] 隧道断开，正在重连..."
        Start-AsrTunnel
        Start-Sleep -Seconds 5
        if (Test-Tunnel) {
            Write-Log "[OK] 隧道重连成功"
        } else {
            Write-Log "[ERROR] 隧道重连失败，60秒后重试..."
            Start-Sleep -Seconds 60
        }
    }
    Start-Sleep -Seconds 30
}
