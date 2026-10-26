@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title 日程规划 · 学习科学排程

echo ==========================================
echo    日程规划 · 学习科学排程
echo ==========================================
echo.

set "PY=.venv\Scripts\python.exe"

if not exist "%PY%" (
    echo [1/4] 创建 Python 虚拟环境 .venv ...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if not exist "%PY%" (
        echo 错误：创建虚拟环境失败，请确认已安装 Python 3.10+ 并加入 PATH。
        pause
        exit /b 1
    )
) else (
    echo [1/4] 虚拟环境已存在
)

echo [2/4] 安装 / 校验后端依赖 ...
"%PY%" -m pip install -q -r backend\requirements.txt
if errorlevel 1 (
    echo 错误：依赖安装失败。
    pause
    exit /b 1
)

if not exist "frontend\dist\index.html" (
    echo [3/4] 首次运行，构建前端 ...
    where pnpm >nul 2>nul
    if errorlevel 1 (
        echo 错误：未找到 pnpm。请先安装 Node.js 18+ 和 pnpm，然后执行：
        echo     cd frontend ^&^& pnpm install ^&^& pnpm build
        pause
        exit /b 1
    )
    pushd frontend
    call pnpm install || (popd & echo 错误：pnpm install 失败 & pause & exit /b 1)
    call pnpm build || (popd & echo 错误：pnpm build 失败 & pause & exit /b 1)
    popd
) else (
    echo [3/4] 前端已构建（改动前端源码后请执行 cd frontend ^&^& pnpm build）
)

echo [4/4] 启动服务 ...
echo.
echo   本机访问：  http://127.0.0.1:8000
echo   局域网访问：http://本机IPv4:8000  （手机连同一 WiFi 即可）
echo   停止服务：  Ctrl+C 或直接关闭本窗口
echo.
start "" http://127.0.0.1:8000
"%PY%" backend\run.py

endlocal
pause
