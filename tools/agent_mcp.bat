@echo off
setlocal
set "ROOT=%~dp0.."
set "PY=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" exit /b 1
"%PY%" "%ROOT%\backend\agent_mcp.py"
endlocal
