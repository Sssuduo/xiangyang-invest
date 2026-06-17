@echo off
chcp 65001 >nul
title 襄阳农高区招商服务网站

echo ============================================
echo    襄阳农高区招商服务网站 - 一键启动
echo ============================================
echo.

:: 检查 Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

:: 检查 Node.js
where node >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

echo [1/4] 检查 Python 依赖...
cd /d "%~dp0backend"
pip install -r requirements.txt -q
if %ERRORLEVEL% neq 0 (
    echo [警告] Python 依赖安装失败，尝试继续...
)

echo [2/4] 检查前端依赖...
cd /d "%~dp0frontend"
if not exist "node_modules" (
    echo 正在安装前端依赖，请稍候...
    call npm install --registry https://registry.npmmirror.com
)

echo [3/4] 启动后端服务...
cd /d "%~dp0backend"
start "Flask后端" cmd /c "python app.py"

echo [4/4] 启动前端开发服务器...
cd /d "%~dp0frontend"
start "Vue前端" cmd /c "npm run dev"

echo.
echo ============================================
echo    启动完成！
echo    后端 API: http://localhost:5000
echo    前端页面: http://localhost:5173
echo    管理后台: http://localhost:5173/admin/login
echo    默认账号: admin / changeme123
echo ============================================
echo.
echo 按任意键退出此窗口（不影响已启动的服务）
pause >nul
