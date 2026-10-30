# 個人課表維護系統

Django 期中專題，提供課程查詢、選課、退選、個人課表與修課進度。

## 系統功能

1. **課程清單與搜尋**
   - 可用關鍵字、課程類型、星期篩選，並看到名額與不能選的原因。
   - 可選課、退選、收藏，以及查看課程詳情和評價。

2. **個人課表**
   - 每週課表同時顯示節次與上課時間，可匯出 PDF、PNG。
   - 顯示已選學分、學分上限與退選下限。

3. **選課規則**
   - 檢查重複選課、衝堂、名額、個人學分上下限，以及資訊、金融模組的學分上下限。
   - 選課前預檢不會占用名額。低於退選下限時，只能由管理員退選。

4. **修課進度**
   - 已取得只算歷年已通過的學分，本學期正在修的課另計。
   - 可在此選擇主修模組；另一模組學分依認列上限互認。
   - 模組學分上下限由管理員設定，這一頁會顯示目前數值。

5. **個人設定**
   - 修改密碼與上傳頭貼。

6. **後台管理**
   - 用 Django Admin 管理課程、選課、收藏、畢業門檻、模組學分限制與使用者學分上下限。

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
- 學分上下限、畢業門檻與模組學分限制都在後台調整，前台重新整理後即會更新。

© 2026 個人課表維護系統
