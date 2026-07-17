$ASR_PORT = 5002
$REMOTE_PORT = 15002
$SERVER = "root@123.56.9.243"
$SSH_KEY = "$env:USERPROFILE\.ssh\id_ed25519"
$LOG_FILE = "h:\scripts\asr_monitor.log"

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts $msg" | Out-File -FilePath $LOG_FILE -Append -Encoding UTF8
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

function Start-Tunnel {
    Write-Log "[INFO] Starting tunnel..."

    if (-not (Test-AsrLocal)) {
        Write-Log "[INFO] Starting ASR API..."
        Set-Location "h:\项目1\backend"
        Start-Process -FilePath "python" -ArgumentList "services/asr_api.py","--port","5002" -WindowStyle Hidden -RedirectStandardOutput "h:\scripts\asr_api.log" -RedirectStandardError "h:\scripts\asr_api_err.log"
        Start-Sleep -Seconds 10
    }

    $sshArgs = @("-i", $SSH_KEY, "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=60", "-o", "ServerAliveCountMax=3", "-o", "ExitOnForwardFailure=yes", "-N", "-R", "${REMOTE_PORT}:localhost:${ASR_PORT}", $SERVER)
    Start-Process -FilePath "ssh" -ArgumentList $sshArgs -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

Write-Log "=== ASR Monitor Started ==="

while ($true) {
    if (Test-Tunnel) {
        Write-Log "[OK] Tunnel alive"
    } else {
        Write-Log "[WARN] Tunnel down, reconnecting..."
        Start-Tunnel
        Start-Sleep -Seconds 5
        if (Test-Tunnel) {
            Write-Log "[OK] Tunnel restored"
        } else {
            Write-Log "[ERROR] Reconnect failed, retry in 60s"
            Start-Sleep -Seconds 60
        }
    }
    Start-Sleep -Seconds 30
}
