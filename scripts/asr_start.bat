@echo off
REM ============================================================
REM ASR 隧道启动器（Windows）
REM 功能：启动 ASR API 并建立到生产服务器的 SSH 反向隧道
REM 开机/登录/休眠唤醒时由任务计划程序调用
REM ============================================================

setlocal enabledelayedexpansion

set PROJECT_DIR=%USERPROFILE%\h----1
set BACKEND_DIR=%PROJECT_DIR%\backend
set LOG_DIR=%PROJECT_DIR%\scripts
set ASR_PORT=5002
set REMOTE_PORT=15002
set SERVER=root@123.56.9.243
set SSH_KEY=%USERPROFILE%\.ssh\id_ed25519

cd /d %PROJECT_DIR%

echo ========================================
echo   ASR 隧道启动器 - %date% %time%
echo ========================================

:check_key
if not exist "%SSH_KEY%" (
    echo [ERROR] SSH 密钥不存在: %SSH_KEY%
    echo 请生成密钥: ssh-keygen -t ed25519 -f "%SSH_KEY%"
    pause
    exit /b 1
)

:check_asr_api
REM 检查 ASR API 是否已在运行
netstat -ano | findstr ":%ASR_PORT%" > nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] ASR API 已在运行
    goto start_tunnel
)

:restart_asr_api
echo [INFO] 启动 ASR API...
cd /d %BACKEND_DIR%
start /B python services/asr_api.py --port %ASR_PORT% > "%LOG_DIR%\asr_api_autostart.log" 2>&1

REM 等待模型加载（最多 60 秒）
set /a count=0
:wait_loop
timeout /t 3 /nobreak > nul
set /a count+=1
netstat -ano | findstr ":%ASR_PORT%" > nul 2>&1
if %errorlevel% neq 0 (
    if !count! lss 20 goto wait_loop
    echo [ERROR] ASR API 启动超时
    type "%LOG_DIR%\asr_api_autostart.log"
    pause
    exit /b 1
)
echo [OK] ASR API 已就绪

:start_tunnel
REM 清理旧隧道
echo [INFO] 清理旧隧道...
ssh -i "%SSH_KEY%" -o StrictHostKeyChecking=no -o ConnectTimeout=5 %SERVER% "fuser -k %REMOTE_PORT%/tcp 2>/dev/null; ss -tlnp | grep %REMOTE_PORT% || echo 'available'" 2>nul

REM 验证隧道
ssh -i "%SSH_KEY%" -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o ExitOnForwardFailure=yes -R %REMOTE_PORT%:localhost:%ASR_PORT% %SERVER% "echo tunnel_test" > nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] 隧道可用
) else (
    echo [WARN] 隧道可能未建立，将由 monitor 脚本处理
)

echo ========================================
echo   ASR 隧道启动完成
echo   监控脚本: asr_monitor.bat
echo ========================================

REM 启动监控（检测断线并重启）
echo [INFO] 启动隧道监控...
start "%LOG_DIR%\asr_monitor.bat"

exit /b 0
