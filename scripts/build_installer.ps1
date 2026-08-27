# 串口调试助手 安装包构建脚本
# 用法（需先安装 Inno Setup 6，免费）：powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1
# 自动查找 ISCC.exe（常见安装路径），编译 installer.iss 生成 installer\SerialTool-Setup-*.exe

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# 1) 打包目录版 exe（带图标、隐藏黑框、含资源）
# 用 --onedir 而非 --onefile：单文件版在 Windows 上会临时解压 DLL 到 %TEMP%\_MEI*，
# 易被杀毒软件拦截导致 "Failed to load Python DLL"。目录版运行时无需解压，更稳定。
Write-Host "==> 1/2 PyInstaller 打包 exe（onedir）..." -ForegroundColor Cyan
$py = "C:\Users\35370\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
& $py -m PyInstaller --onedir --windowed --name SerialTool --clean --noconfirm `
    --add-data "assets;assets" --icon assets\logo.ico main.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller 打包失败" }

# 2) 查找 Inno Setup 编译器
Write-Host "==> 2/2 Inno Setup 编译安装包 ..." -ForegroundColor Cyan
$iscc = @(
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 5\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 5\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 5\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    Write-Host "未找到 Inno Setup，请先安装：https://jrsoftware.org/isinfo.php （免费）" -ForegroundColor Yellow
    Write-Host "安装后重新运行本脚本即可。exe 已打包完成：dist\SerialTool.exe"
    exit 0
}
& $iscc "installer.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup 编译失败" }
Write-Host "完成！安装包：installer\SerialTool-Setup-*.exe" -ForegroundColor Green
