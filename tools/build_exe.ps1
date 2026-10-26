# 一键打包 日程规划.exe（由 build_exe.bat 调用；也可直接右键「使用 PowerShell 运行」）
# 前置：.venv 里装好 backend\requirements.txt + pyinstaller + pillow；frontend\dist 已构建
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "[x] 未找到 .venv，请先：" -ForegroundColor Red
    Write-Host "    python -m venv .venv"
    Write-Host "    .venv\Scripts\pip install -r backend\requirements.txt pyinstaller pillow"
    exit 1
}

if (-not (Test-Path "frontend\dist\index.html")) {
    Write-Host "[i] frontend\dist 不存在，先构建前端..." -ForegroundColor Cyan
    Push-Location frontend
    pnpm install
    pnpm build
    Pop-Location
    if (-not (Test-Path "frontend\dist\index.html")) {
        Write-Host "[x] 前端构建失败" -ForegroundColor Red
        exit 1
    }
}

Write-Host "[i] 生成图标 assets\icon.ico ..." -ForegroundColor Cyan
& $py "tools\make_icon.py"
if ($LASTEXITCODE -ne 0) { Write-Host "[x] 图标生成失败" -ForegroundColor Red; exit 1 }

Write-Host "[i] PyInstaller 打包（约 1 分钟）..." -ForegroundColor Cyan
Push-Location backend
try {
    & "..\.venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --noconsole `
        --name "日程规划" `
        --icon "..\assets\icon.ico" `
        --add-data "..\frontend\dist;frontend\dist" `
        --hidden-import uvicorn.logging `
        --hidden-import uvicorn.loops.auto `
        --hidden-import uvicorn.protocols.http.auto `
        --hidden-import uvicorn.protocols.websockets.auto `
        --hidden-import uvicorn.lifespan.on `
        launcher.py
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller 失败（exit $LASTEXITCODE）" }
} finally {
    Pop-Location
}

Copy-Item "backend\dist\日程规划.exe" "日程规划.exe" -Force
Write-Host ""
Write-Host "[ok] 已生成 日程规划.exe（双击即可启动；桌面快捷方式仍指向它）" -ForegroundColor Green
