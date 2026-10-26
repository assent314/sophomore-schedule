@echo off
REM One-click build for 日程规划.exe -- actual work lives in build_exe.ps1
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_exe.ps1"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [x] build failed, see messages above.
)
exit /b %RC%
