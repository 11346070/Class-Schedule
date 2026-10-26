# 個人課表維護系統

Django 期中專題 - 完整的課表維護與選課管理系統

## 專題簡介

本系統是一套適合大學生使用的個人課表維護系統，讓使用者能夠瀏覽課程、選課、退選、維護個人課表，並即時檢查課程衝突與課程名額。系統特別注重選課規則及名額管理，確保選課流程的合理性與正確性。

**重要特色：**
- ✅ 不使用任何資料庫（SQLite、MySQL、PostgreSQL）
- ✅ 採用記憶體儲存，所有資料存儲於 Python 記憶體中
- ✅ 完整的課程時間衝突檢查
- ✅ 精確的課程名額管理與占用
- ✅ 繁體中文介面
- ✅ 響應式設計

## 系統功能

### 1. 課程清單
- 瀏覽所有課程
- 關鍵字搜尋（課程名稱、教師、課程編號）
- 依課程類型篩選（必修、選修、通識）
- 依星期篩選
- 即時顯示課程名額狀態

### 2. 個人課表維護
- 新增課程至個人課表
- 查看已選課程
- 退選課程
- 每週課表視覺化
- 已選學分統計
- 選課數量統計

### 3. 課程時間衝突檢查
- 自動檢測同一天、節次重疊的課程
- 拒絕衝突選課並明確提示
- 不同星期或不重疊時段可正常選課

### 4. 課程名額管理
- 所有使用者共用同一份課程名額
- 額滿課程無法選課
- 退選後即時釋放名額
- 防止重複選課
- 防止名額超額或負數

### 5. 選課合理性檢查
- 課程是否存在
- 是否重複選課
- 是否已額滿
- 是否時間衝突
- 星期與節次合法性
- 學分合理性

## 技術架構

### 後端
- **框架：** Django 6.1.2
- **語言：** Python 3.12
- **資料儲存：** 記憶體儲存（無資料庫）
- **Session：** 檔案式 Session
- **並發控制：** threading.Lock

### 前端
- **模板引擎：** Django Templates
- **樣式：** 原生 CSS
- **腳本：** 原生 JavaScript
- **響應式：** 支援桌面與平板瀏覽

### 架構特點
- Django MTV 架構
- 單例模式課程資料儲存
- Session 識別使用者
- CSRF 防護
- 表單伺服器端驗證

## 本機安裝與執行

### 環境需求
- Windows 10/11
- Python 3.12 或以上
- PowerShell 或 CMD

### 安裝步驟

1. **Clone 專案**
```powershell
git clone https://github.com/11346070/Class-Schedule.git
cd Class-Schedule
```

2. **建立虛擬環境**
```powershell
python -m venv .venv
```

3. **啟動虛擬環境**

PowerShell：
```powershell
.venv\Scripts\Activate.ps1
```

CMD：
```cmd
.venv\Scripts\activate.bat
```

4. **安裝依賴**
```powershell
pip install -r requirements.txt
```

5. **建立 .env 檔案**
```powershell
copy .env.example .env
```

（可選）編輯 `.env` 並設定新的 SECRET_KEY

6. **執行系統檢查**
```powershell
python manage.py check
```

### 啟動系統

#### 方式一：使用啟動腳本（推薦）

**PowerShell：**
```powershell
.\start.ps1
```

**CMD：**
```cmd
start.bat
```

#### 方式二：手動啟動

```powershell
python manage.py runserver 127.0.0.1:8000
```

### 訪問系統

啟動成功後，在瀏覽器開啟：

```
http://127.0.0.1:8000
```

## 系統操作說明

### 1. 首頁
- 顯示已選課程的每週課表
- 顯示已選學分與課程數統計
- 可快速退選課程

### 2. 課程清單
- 瀏覽所有課程
- 使用搜尋與篩選功能
- 點擊「選課」按鈕選課
- 點擊「詳情」查看課程詳細資訊

### 3. 我的課表
- 查看所有已選課程
- 查看學分統計
- 退選課程

### 4. 系統資訊
- 查看系統統計
- 了解技術架構
- 閱讀系統說明與限制

## 專案結構

```
Class-Schedule/
├── timetable_project/      # Django 專案設定
│   ├── settings.py         # 設定檔（無資料庫、檔案式 Session）
│   └── urls.py             # 主 URL routing
├── timetable/              # 主要應用程式
│   ├── data_store.py       # 課程資料儲存與管理（記憶體）
│   ├── views.py            # 視圖處理
│   └── urls.py             # App URL routing
├── templates/              # HTML 模板
│   ├── base.html           # 基礎模板
│   ├── index.html          # 首頁
│   ├── course_list.html    # 課程清單
│   ├── course_detail.html  # 課程詳情
│   ├── my_courses.html     # 我的課表
│   └── system_info.html    # 系統資訊
├── static/                 # 靜態資源
│   ├── css/style.css       # 樣式表
│   └── js/main.js          # JavaScript
├── docs/                   # 文件
│   ├── SYSTEM_ARCHITECTURE.md      # 系統架構文件
│   ├── DEMO_SCRIPT.md              # 展示腳本
│   ├── ACCEPTANCE_CHECKLIST.md     # 驗收清單
│   └── 個人課表維護系統_期中報告.pptx  # 簡報
├── scripts/                # 腳本
│   └── generate_presentation.py    # 產生簡報
├── start.bat               # Windows CMD 啟動腳本
├── start.ps1               # PowerShell 啟動腳本
├── requirements.txt        # Python 依賴
├── .env.example            # 環境變數範例
├── .gitignore              # Git 忽略檔案
└── README.md               # 專案說明
```

## 重要限制

### 資料儲存限制
- **伺服器重啟後資料重置：** 所有選課資料會回到初始狀態
- **無法跨程序共用：** 多個 Worker 或程序無法共用記憶體
- **單程序執行：** 本專題採用單一 Django 程序確保名額正確

### 使用者識別
- 使用 Django Session 識別使用者
- 每個瀏覽器 Session 視為獨立使用者
- Session 儲存於檔案（sessions/ 目錄）

### 並發處理
- 使用 threading.Lock 防止並發選課問題
- 適合開發環境與課堂展示
- 正式環境需考慮分散式鎖定或資料庫

## 文件與簡報

- **系統架構文件：** [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md)
- **展示腳本：** [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)
- **驗收清單：** [docs/ACCEPTANCE_CHECKLIST.md](docs/ACCEPTANCE_CHECKLIST.md)
- **期中報告簡報：** [docs/個人課表維護系統_期中報告.pptx](docs/個人課表維護系統_期中報告.pptx)

## 安全性說明

### 機敏資訊保護
- `.env` 檔案未納入版本控制
- 使用 `.env.example` 提供範例
- SECRET_KEY 從環境變數讀取
- `.gitignore` 排除所有機敏檔案

### CSRF 防護
- 所有 POST 請求使用 CSRF Token
- Django 內建 CSRF 中介軟體啟用

## 開發說明

### 依賴套件
- Django >= 5.0, < 5.1
- python-decouple >= 3.8（環境變數管理）
- python-pptx >= 0.6.23（簡報產生）

### 停止伺服器
在終端機按 `Ctrl + C`

### 重置資料
重新啟動伺服器即可重置所有選課資料

## 授權與聲明

本專案為 Django 期中專題作業，僅供教學與展示用途。

© 2026 個人課表維護系統
