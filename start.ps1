# 個人課表維護系統 - 啟動腳本 (PowerShell)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "個人課表維護系統 - Django 開發伺服器" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 檢查虛擬環境
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[錯誤] 找不到虛擬環境，請先執行以下命令建立虛擬環境：" -ForegroundColor Red
    Write-Host "python -m venv .venv" -ForegroundColor Yellow
    Write-Host ".venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "pip install -r requirements.txt" -ForegroundColor Yellow
    Read-Host "按 Enter 鍵離開"
    exit 1
}

# 檢查 .env 檔案
if (-not (Test-Path ".env")) {
    Write-Host "[警告] 找不到 .env 檔案，將使用預設設定" -ForegroundColor Yellow
    Write-Host "建議複製 .env.example 為 .env 並設定 SECRET_KEY" -ForegroundColor Yellow
    Write-Host ""
}

# 執行 Django 系統檢查
Write-Host "[1/2] 執行系統檢查..." -ForegroundColor Green
& .venv\Scripts\python.exe manage.py check
if ($LASTEXITCODE -ne 0) {
    Write-Host "[錯誤] 系統檢查失敗" -ForegroundColor Red
    Read-Host "按 Enter 鍵離開"
    exit 1
}
Write-Host "[成功] 系統檢查通過" -ForegroundColor Green
Write-Host ""

# 啟動開發伺服器
Write-Host "[2/2] 啟動開發伺服器..." -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "伺服器啟動成功！" -ForegroundColor Green
Write-Host "網址: http://127.0.0.1:8000" -ForegroundColor Yellow
Write-Host "按 Ctrl+C 停止伺服器" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

& .venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000

Read-Host "按 Enter 鍵離開"
