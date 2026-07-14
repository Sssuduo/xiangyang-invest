@echo off
chcp 65001 >nul 2>&1

echo ========================================
echo   ASR Tunnel Task Registration
echo ========================================

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Admin rights required!
    echo Right-click - Run as administrator
    pause
    exit /b 1
)

schtasks /Delete /TN "ASR Tunnel Monitor" /F >nul 2>&1

schtasks /Create ^
    /TN "ASR Tunnel Monitor" ^
    /TR "powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File ""h:\项目1\scripts\asr_monitor.ps1""" ^
    /SC ONLOGON ^
    /RL HIGHEST ^
    /DELAY 0000:10 ^
    /F

if %errorlevel% equ 0 (
    echo.
    echo [OK] Task registered: ASR Tunnel Monitor
    echo.
    echo Starting task now...
    schtasks /Run /TN "ASR Tunnel Monitor"
    echo [OK] Task started
) else (
    echo.
    echo [ERROR] Registration failed
)

echo.
pause
