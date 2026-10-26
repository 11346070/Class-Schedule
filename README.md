# 個人課表維護系統

Django 期中專題，提供大學生課程查詢、選課、退選與個人課表管理功能。

## 系統功能

1. **課程清單與搜尋**
   - 支援關鍵字搜尋、課程類型及星期篩選。
   - 顯示課程狀態、剩餘名額及無法選課的原因。
   - 提供選課、退選、收藏及課程詳情功能。

2. **個人課表管理**
   - 查看每週課表及已選課程。
   - 支援快速退選、學分統計與學分上限提醒。

3. **選課規則檢查**
   - 自動檢查重複選課、課程衝突、課程名額及學分上限。
   - 提供選課前預檢，不會占用課程名額。
   - 防止超額選課及不合法的課程資料。

4. **課程收藏**
   - 收藏感興趣的課程並查看收藏清單。
   - 顯示收藏課程的選課可行性，支援快速選課及取消收藏。

5. **後台管理**
   - 使用 Django Admin + SimpleUI 管理課程、選課、收藏及學分上限。
   - 支援課程資料驗證、搜尋、篩選與分頁。

## 技術架構

- **後端：** Python 3.12、Django 6.x
- **資料庫：** SQLite、Django ORM
- **前端：** Django Templates、原生 CSS、JavaScript
- **其他：** Session、CSRF 防護、資料驗證與交易控制

## 本機安裝與執行

### 1. Clone 專案

```bash
git clone https://github.com/11346070/Class-Schedule.git
cd Class-Schedule
```

### 2. 建立虛擬環境並安裝依賴

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 設定環境變數並建立資料庫

```bash
copy .env.example .env
python manage.py migrate
```

### 4. 建立管理員帳號並啟動系統

```bash
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

## 系統網址

- **前台：** http://127.0.0.1:8000
- **後台：** http://127.0.0.1:8000/admin/

## 注意事項

- 本專案以本機執行為主，供課堂展示與測試使用。
- `db.sqlite3`、`.env` 與 `.venv/` 不納入版本控制。
- 首次執行資料庫遷移後，若資料庫尚無課程，系統會自動載入示範課程。

© 2026 個人課表維護系統
