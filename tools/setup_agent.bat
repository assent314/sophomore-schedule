@echo off
chcp 65001 >nul
setlocal
set "ROOT=%~dp0.."
set "PY=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" (
  py -3 -m venv "%ROOT%\.venv" 2>nul || python -m venv "%ROOT%\.venv"
)
if not exist "%PY%" (
  echo 无法创建 Python 虚拟环境。
  exit /b 1
)
"%PY%" -m pip install -r "%ROOT%\backend\requirements-agent.txt"
if errorlevel 1 exit /b 1
echo Agent MCP 依赖已就绪。请在 Codex 或 DeepSeek Harness 中注册 tools\agent_mcp.bat。
endlocal
