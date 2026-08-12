#Requires -Version 5.1
<#
.SYNOPSIS
  ASR watchdog guard - heartbeat self-check monitor

.DESCRIPTION
  The watchdog (asr_watchdog.ps1) writes a heartbeat file (asr_watchdog.online)
  on every check cycle. This guard runs every 15 minutes via Task Scheduler:
  - If heartbeat file is missing or older than 2x check interval (60 min)
    -> watchdog task stopped; restart ASR_Tunnel task (or spawn watchdog directly)
  - Also verifies ASR_Tunnel task points to asr_watchdog.ps1 (not old asr_monitor.ps1)
  - Also checks tunnel health from server side (15002 -> /health), rebuilds if dead

  All log messages kept ASCII to avoid PowerShell 5.1 UTF-8 parsing issues.
#>
[CmdletBinding()]
param(
    [int] $MaxHeartbeatMinutes = 60
)

$ErrorActionPreference = 'Continue'

$SCRIPT_DIR = $PSScriptRoot
$HEARTBEAT  = Join-Path $SCRIPT_DIR "asr_watchdog.online"
$GUARD_LOG  = Join-Path $SCRIPT_DIR "asr_watchdog_guard.log"
$TASK_NAME  = "ASR_Tunnel"
$SERVER     = "root@123.56.9.243"
$REMOTE_PORT = 15002
$SSH_KEY    = Join-Path $env:USERPROFILE ".ssh\id_ed25519"

function Write-GuardLog {
    param([string]$msg)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$ts $msg"
    try { $line | Out-File -FilePath $GUARD_LOG -Append -Encoding UTF8 } catch {}
    Write-Host $line
}

# --- 1. heartbeat freshness check ---
$heartbeatFresh = $false
$hbAgeMin = -1
if (Test-Path $HEARTBEAT) {
    try {
        $content = Get-Content $HEARTBEAT -Raw -Encoding UTF8
        if ($content -match '(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})') {
            $hbTime = [datetime]::ParseExact($Matches[1], 'yyyy-MM-dd HH:mm:ss', $null)
            $hbAgeMin = ((Get-Date) - $hbTime).TotalMinutes
            $heartbeatFresh = ($hbAgeMin -le $MaxHeartbeatMinutes)
            if (-not $heartbeatFresh) {
                Write-GuardLog "[WARN] heartbeat stale: $content ($([math]::Round($hbAgeMin)) min ago)"
            }
        }
    } catch {
        Write-GuardLog "[WARN] heartbeat parse failed: $_"
    }
} else {
    Write-GuardLog "[WARN] heartbeat file missing: $HEARTBEAT"
}

# --- 1.5 verify ASR_Tunnel task points to asr_watchdog.ps1 ---
try {
    $taskAction = (Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue).Actions.Arguments
    if ($taskAction -match 'asr_monitor\.ps1') {
        Write-GuardLog "[WARN] ASR_Tunnel points to old asr_monitor.ps1, fixing..."
        $fixAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-WindowStyle Hidden -ExecutionPolicy Bypass -File $SCRIPT_DIR\asr_watchdog.ps1"
        Register-ScheduledTask -TaskName $TASK_NAME -Action $fixAction -Force -ErrorAction SilentlyContinue
        Write-GuardLog "[OK] ASR_Tunnel re-pointed to asr_watchdog.ps1"
    }
} catch { }

# --- 2. heartbeat stale -> restart watchdog ---
if (-not $heartbeatFresh) {
    Write-GuardLog "[WARN] watchdog heartbeat stale, restarting $TASK_NAME ..."
    try {
        Stop-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        Start-ScheduledTask -TaskName $TASK_NAME
        Write-GuardLog "[OK] scheduled task $TASK_NAME restarted"
        # immediately run one watchdog check (-NoLoop) to restore service fast
        Start-Sleep -Seconds 3
        & (Join-Path $SCRIPT_DIR "asr_watchdog.ps1") -NoLoop 2>$null
        Write-GuardLog "[OK] watchdog one-shot check done"
    } catch {
        Write-GuardLog "[ERROR] restart task failed: $_"
        # fallback: spawn watchdog directly (bypass scheduled task)
        Start-Process powershell.exe -ArgumentList "-WindowStyle Hidden -ExecutionPolicy Bypass -File $(Join-Path $SCRIPT_DIR 'asr_watchdog.ps1')" -WindowStyle Hidden
        Write-GuardLog "[OK] watchdog spawned directly (fallback)"
    }
} else {
    Write-GuardLog "[OK] watchdog heartbeat OK ($([math]::Round($hbAgeMin)) min ago)"
}

# --- 3. tunnel health check (server side 15002 -> /health) ---
try {
    $tunnelOk = ssh.exe -i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=8 $SERVER `
        "curl -s -m 5 http://127.0.0.1:${REMOTE_PORT}/health" 2>$null
    if ($tunnelOk -match '"status"\s*:\s*"ok"') {
        Write-GuardLog "[OK] tunnel OK"
    } else {
        Write-GuardLog "[WARN] tunnel unhealthy, running watchdog check to rebuild"
        & (Join-Path $SCRIPT_DIR "asr_watchdog.ps1") -NoLoop 2>$null
    }
} catch {
    Write-GuardLog "[WARN] tunnel check error: $_"
}
