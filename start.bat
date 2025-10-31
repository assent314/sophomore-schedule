@echo off
chcp 65001 >nul
echo ====================================
echo    日程规划表 Demo 启动脚本
echo ====================================
echo.

echo [1/3] 检查虚拟环境...
if not exist "venv\Scripts\python.exe" (
    echo 创建虚拟环境...
    py -m venv venv
    if errorlevel 1 (
        echo 错误：创建虚拟环境失败
        pause
        exit /b 1
    )
)
echo.

echo [2/3] 激活虚拟环境并安装依赖...
call venv\Scripts\activate.bat
cd backend
pip install -r requirements.txt
if errorlevel 1 (
    echo 警告：依赖安装可能失败，继续尝试启动...
)
echo.

echo [3/3] 启动服务...
echo.
echo ====================================
echo 后端服务: http://localhost:5000
echo 前端页面: http://localhost:8080
echo ====================================
echo.
echo 按 Ctrl+C 可以停止服务
echo.

start "后端服务" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && cd backend && python app.py"
timeout /t 3 /nobreak >nul

cd ..\frontend
start "前端服务" cmd /k "python -m http.server 8080"
timeout /t 2 /nobreak >nul

echo.
echo 正在打开浏览器...
start http://localhost:8080

echo.
echo 服务已启动！
echo 关闭此窗口不会停止服务，请关闭对应的服务窗口。
pause
