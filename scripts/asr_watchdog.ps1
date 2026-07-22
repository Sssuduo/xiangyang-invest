#Requires -Version 5.1
<#
.SYNOPSIS
  ASR local service watchdog hook.
.DESCRIPTION
  When the agent is online, every $IntervalMinutes minutes this hook checks the
  local ASR service and the SSH reverse tunnel. If the local service is down it
  restarts asr_api.py; if the tunnel is down it rebuilds the SSH reverse tunnel.
  Designed to run as a background process (launched by Task Scheduler on logon /
  unlock). Use -NoLoop for a single check (e.g. from a git hook or manual run).
  This supersedes the old 30-second asr_monitor.ps1 polling.
  NOTE: paths are derived from $PSScriptRoot at runtime so no CJK literals live
  in source (avoids GBK/ANSI mis-decode on this Windows host).
#>
[CmdletBinding()]
param(
    [int]    $IntervalMinutes    = 30,
    [switch] $RequireAgentOnline,   # only act when <scriptdir>/agent_online.flag exists
    [switch] $NoLoop                  # run one check then exit
)

$ErrorActionPreference = 'Continue'

# derive paths from the script location (runtime-resolved, CJK-safe)
$SCRIPT_DIR  = $PSScriptRoot
$API_DIR     = Join-Path $PSScriptRoot "..\backend"
$ASR_PORT    = 5002
$REMOTE_PORT = 15002
$SERVER      = "root@123.56.9.243"
$SSH_KEY     = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
$LOG_FILE    = Join-Path $SCRIPT_DIR "asr_watchdog.log"
$HEARTBEAT   = Join-Path $SCRIPT_DIR "asr_watchdog.online"
$AGENT_FLAG  = Join-Path $SCRIPT_DIR "agent_online.flag"

# process handles kept across loop iterations
$script:asrProc    = $null
$script:tunnelProc = $null

function Write-Log {
    param([string]$msg, [string]$level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$ts [$level] $msg"
    try { $line | Out-File -FilePath $LOG_FILE -Append -Encoding UTF8 } catch {}
    Write-Host $line
}

function Update-Heartbeat {
    # advertise that this hook/agent is online (consumed by external tooling)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    try { "agent_online=$ts" | Out-File -FilePath $HEARTBEAT -Encoding UTF8 } catch {}
}

function Test-AgentOnline {
    if (-not $RequireAgentOnline) { return $true }
    return (Test-Path $AGENT_FLAG)
}

function Test-AsrLocal {
    try {
        $r = curl.exe -s --max-time 3 "http://localhost:$ASR_PORT/health" 2>$null
        return ($r -match '"status"\s*:\s*"ok"')
    } catch { return $false }
}

function Start-AsrApi {
    Write-Log "Starting ASR API: python services/asr_api.py --port $ASR_PORT" "INFO"
    try {
        Set-Location $API_DIR
        $p = Start-Process -FilePath "python" `
            -ArgumentList "services/asr_api.py", "--port", $ASR_PORT `
            -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $SCRIPT_DIR "asr_api.log") `
            -RedirectStandardError  (Join-Path $SCRIPT_DIR "asr_api_err.log") `
            -PassThru
        $script:asrProc = $p
        # wait for model load (up to ~60s)
        for ($i = 1; $i -le 30; $i++) {
            Start-Sleep -Seconds 2
            if (Test-AsrLocal) { Write-Log "ASR API ready (PID=$($p.Id))" "OK"; return $true }
        }
        Write-Log "ASR API did not become ready after start; check asr_api_err.log" "WARN"
        return $false
    } catch {
        Write-Log "Failed to start ASR API: $_" "ERROR"
        return $false
    }
}

function Start-Tunnel {
    # clear stale server-side port so ExitOnForwardFailure does not trip on a zombie sshd
    try {
        ssh.exe -i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=10 $SERVER `
            "fuser -k ${REMOTE_PORT}/tcp 2>/dev/null; true" 2>$null | Out-Null
    } catch {}
    Write-Log "Building SSH reverse tunnel: ${REMOTE_PORT}:localhost:${ASR_PORT} -> $SERVER" "INFO"
    try {
        $p = Start-Process -FilePath "ssh.exe" `
            -ArgumentList @("-i", $SSH_KEY, "-o", "StrictHostKeyChecking=no",
                            "-o", "ServerAliveInterval=60", "-o", "ServerAliveCountMax=3",
                            "-o", "ExitOnForwardFailure=yes", "-N",
                            "-R", "${REMOTE_PORT}:localhost:${ASR_PORT}", $SERVER) `
            -WindowStyle Hidden -PassThru
        $script:tunnelProc = $p
        Start-Sleep -Seconds 3
        if (-not $p.HasExited) { Write-Log "Tunnel process launched (PID=$($p.Id))" "OK"; return $true }
        Write-Log "Tunnel process exited immediately (exit=$($p.ExitCode))" "ERROR"
        return $false
    } catch {
        Write-Log "Failed to build tunnel: $_" "ERROR"
        return $false
    }
}

function Test-TunnelAlive {
    if ($null -eq $script:tunnelProc) { return $false }
    if ($script:tunnelProc.HasExited) { return $false }
    # process alive == tunnel considered alive (laptop side cannot probe server 15002 directly)
    return $true
}

function Invoke-Check {
    Update-Heartbeat
    if (-not (Test-AgentOnline)) {
        Write-Log "Agent offline (missing $AGENT_FLAG), skipping this check" "INFO"
        return
    }
    # 1) local ASR service
    if (-not (Test-AsrLocal)) {
        Write-Log "ASR local service is down, restarting" "WARN"
        if ($script:asrProc -and -not $script:asrProc.HasExited) {
            try { $script:asrProc.Kill() } catch {}
        }
        Start-AsrApi | Out-Null
    } else {
        Write-Log "ASR local service OK (localhost:$ASR_PORT)" "OK"
    }
    # 2) reverse tunnel (ensure local API up first, then ensure tunnel up)
    if (-not (Test-TunnelAlive)) {
        Write-Log "Reverse tunnel is down, rebuilding" "WARN"
        Start-Tunnel | Out-Null
    } else {
        Write-Log "Reverse tunnel OK (-> ${SERVER}:${REMOTE_PORT})" "OK"
    }
}

Write-Log "=== ASR Watchdog started (interval=${IntervalMinutes}min, requireAgentOnline=$RequireAgentOnline) ===" "INFO"

if ($NoLoop) {
    Invoke-Check
    Write-Log "Single check done, exiting" "INFO"
} else {
    while ($true) {
        Invoke-Check
        Start-Sleep -Seconds ($IntervalMinutes * 60)
    }
}
