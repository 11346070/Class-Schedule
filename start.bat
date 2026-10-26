@echo off
REM 個人課表維護系統 - 啟動腳本 (Windows)

echo ========================================
echo 個人課表維護系統 - Django 開發伺服器
echo ========================================
echo.

REM 檢查虛擬環境
if not exist ".venv\Scripts\python.exe" (
    echo [錯誤] 找不到虛擬環境，請先執行以下命令建立虛擬環境：
    echo python -m venv .venv
    echo .venv\Scripts\activate
    echo pip install -r requirements.txt
    pause
    exit /b 1
)

REM 檢查 .env 檔案
if not exist ".env" (
    echo [警告] 找不到 .env 檔案，將使用預設設定
    echo 建議複製 .env.example 為 .env 並設定 SECRET_KEY
    echo.
)

REM 執行 Django 系統檢查
echo [1/2] 執行系統檢查...
.venv\Scripts\python.exe manage.py check
if errorlevel 1 (
    echo [錯誤] 系統檢查失敗
    pause
    exit /b 1
)
echo [成功] 系統檢查通過
echo.

REM 啟動開發伺服器
echo [2/2] 啟動開發伺服器...
echo.
echo ========================================
echo 伺服器啟動成功！
echo 網址: http://127.0.0.1:8000
echo 按 Ctrl+C 停止伺服器
echo ========================================
echo.

.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000

pause
