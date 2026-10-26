"""
產生「個人課表維護系統」期中報告簡報
使用 python-pptx 套件自動產生 PowerPoint 檔案
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
import os


def create_presentation():
    """建立簡報"""
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)
    
    # 1. 封面
    add_title_slide(prs)
    
    # 2. 專題背景與動機
    add_background_slide(prs)
    
    # 3. 系統目標與功能需求
    add_objectives_slide(prs)
    
    # 4. 使用技術及選用原因
    add_technologies_slide(prs)
    
    # 5. 系統架構圖
    add_architecture_slide(prs)
    
    # 6. 系統主要功能與頁面
    add_features_slide(prs)
    
    # 7. 選課與退選流程
    add_enrollment_flow_slide(prs)
    
    # 8. 課程衝突檢查與名額管理機制
    add_conflict_quota_slide(prs)
    
    # 9. 資料儲存方式、限制及安全設計
    add_data_storage_slide(prs)
    
    # 10. 本機執行方式與展示流程
    add_execution_slide(prs)
    
    # 11. 專題總結與未來擴充方向
    add_conclusion_slide(prs)
    
    return prs


def add_title_slide(prs):
    """封面"""
    blank_layout = prs.slide_layouts[6]  # 空白版面
    slide = prs.slides.add_slide(blank_layout)
    
    # 設定背景色
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(37, 99, 235)  # 藍色
    
    # 主標題
    title_box = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(8), Inches(1))
    title_frame = title_box.text_frame
    title_frame.text = "個人課表維護系統"
    title_para = title_frame.paragraphs[0]
    title_para.font.size = Pt(54)
    title_para.font.bold = True
    title_para.font.color.rgb = RGBColor(255, 255, 255)
    title_para.alignment = PP_ALIGN.CENTER
    
    # 副標題
    subtitle_box = slide.shapes.add_textbox(Inches(1), Inches(3.8), Inches(8), Inches(0.6))
    subtitle_frame = subtitle_box.text_frame
    subtitle_frame.text = "Django 期中專題報告"
    subtitle_para = subtitle_frame.paragraphs[0]
    subtitle_para.font.size = Pt(28)
    subtitle_para.font.color.rgb = RGBColor(255, 255, 255)
    subtitle_para.alignment = PP_ALIGN.CENTER
    
    # 組員資訊欄位
    info_box = slide.shapes.add_textbox(Inches(2), Inches(5.2), Inches(6), Inches(1.2))
    info_frame = info_box.text_frame
    info_frame.text = "課程名稱：【請填寫課程名稱】\n組員：【請填寫組員姓名】\n指導教師：【請填寫教師姓名】"
    for para in info_frame.paragraphs:
        para.font.size = Pt(18)
        para.font.color.rgb = RGBColor(255, 255, 255)
        para.alignment = PP_ALIGN.CENTER


def add_background_slide(prs):
    """專題背景與動機"""
    slide = add_slide_with_title(prs, "專題背景與動機")
    
    content = [
        "專題背景",
        "  • 開發適合大學生使用的課表維護系統",
        "  • 管理選課、退選及課程安排",
        "  • 特別注重選課規則與名額管理",
        "",
        "開發動機",
        "  • 實作完整的選課流程與規則檢查",
        "  • 處理課程時間衝突問題",
        "  • 確保課程名額管理的正確性",
        "  • 提供清楚的課表視覺化",
        "",
        "專題特色",
        "  • 不使用任何資料庫（SQLite、MySQL、PostgreSQL）",
        "  • 採用記憶體儲存，符合特殊需求",
        "  • 完整實作選課業務邏輯",
    ]
    
    add_bullet_content(slide, content)


def add_objectives_slide(prs):
    """系統目標與功能需求"""
    slide = add_slide_with_title(prs, "系統目標與功能需求")
    
    left = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(4.5), Inches(5.5))
    left_frame = left.text_frame
    left_frame.text = "系統目標\n\n✓ 課程瀏覽與搜尋\n\n✓ 選課與退選管理\n\n✓ 課程衝突檢查\n\n✓ 名額管理與占用\n\n✓ 每週課表視覺化\n\n✓ 學分統計"
    for para in left_frame.paragraphs:
        para.font.size = Pt(18)
    
    right = slide.shapes.add_textbox(Inches(5.2), Inches(1.5), Inches(4.5), Inches(5.5))
    right_frame = right.text_frame
    right_frame.text = "核心功能\n\n• 課程清單與搜尋\n\n• 個人課表維護\n\n• 時間衝突檢查\n\n• 名額正確管理\n\n• 選課合理性驗證\n\n• 繁體中文介面"
    for para in right_frame.paragraphs:
        para.font.size = Pt(18)


def add_technologies_slide(prs):
    """使用技術及選用原因"""
    slide = add_slide_with_title(prs, "使用技術及選用原因")
    
    content = [
        "後端技術",
        "  • Django 6.1.2 - 成熟的 Python Web 框架",
        "  • Python 3.12 - 最新穩定版本",
        "  • python-decouple - 環境變數管理",
        "",
        "前端技術",
        "  • Django Templates - 伺服器端渲染",
        "  • 原生 CSS - 完全客製化樣式",
        "  • 原生 JavaScript - 輕量化互動",
        "",
        "資料儲存",
        "  • 記憶體儲存 - Python 字典與集合",
        "  • 檔案式 Session - 使用者識別",
        "  • threading.Lock - 並發控制",
    ]
    
    add_bullet_content(slide, content)


def add_architecture_slide(prs):
    """系統架構圖"""
    slide = add_slide_with_title(prs, "系統架構圖")
    
    # 架構說明（文字版）
    textbox = slide.shapes.add_textbox(Inches(1), Inches(1.8), Inches(8), Inches(5))
    text_frame = textbox.text_frame
    text_frame.text = """Django MTV 架構

Model（資料模型）
  → Course 類別（課程資料）
  → CourseDataStore 類別（記憶體儲存管理）
  → 單例模式確保資料一致性

Template（模板）
  → base.html、index.html、course_list.html
  → course_detail.html、my_courses.html、system_info.html

View（視圖）
  → index、course_list、course_detail、my_courses
  → enroll_course、drop_course、system_info

URL Routing
  → 專案層級：timetable_project/urls.py
  → 應用程式層級：timetable/urls.py"""
    
    for para in text_frame.paragraphs:
        para.font.size = Pt(16)
        para.space_after = Pt(8)


def add_features_slide(prs):
    """系統主要功能與頁面"""
    slide = add_slide_with_title(prs, "系統主要功能與頁面")
    
    content = [
        "1. 首頁",
        "  • 每週課表視覺化顯示",
        "  • 已選學分與課程數統計",
        "",
        "2. 課程清單",
        "  • 瀏覽所有課程（24 門示範課程）",
        "  • 關鍵字搜尋與篩選",
        "  • 即時顯示名額狀態",
        "",
        "3. 我的課表",
        "  • 查看已選課程詳細資訊",
        "  • 退選課程功能",
        "",
        "4. 課程詳情",
        "  • 完整課程資訊",
        "  • 選課/退選操作",
        "  • 衝突與名額狀態提示",
    ]
    
    add_bullet_content(slide, content)


def add_enrollment_flow_slide(prs):
    """選課與退選流程"""
    slide = add_slide_with_title(prs, "選課與退選流程")
    
    left = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(4.5), Inches(5.5))
    left_frame = left.text_frame
    left_frame.text = "選課流程\n\n1. 使用者點擊選課\n\n2. 檢查課程是否存在\n\n3. 檢查是否已選過\n\n4. 檢查是否額滿\n\n5. 檢查是否時間衝突\n\n6. 加鎖並更新資料\n\n7. 返回成功訊息"
    for para in left_frame.paragraphs:
        para.font.size = Pt(16)
    
    right = slide.shapes.add_textbox(Inches(5.2), Inches(1.5), Inches(4.5), Inches(5.5))
    right_frame = right.text_frame
    right_frame.text = "退選流程\n\n1. 使用者點擊退選\n\n2. 檢查課程是否存在\n\n3. 檢查是否已選過\n\n4. 加鎖並移除選課\n\n5. 減少已選人數\n\n6. 釋放名額\n\n7. 返回成功訊息"
    for para in right_frame.paragraphs:
        para.font.size = Pt(16)


def add_conflict_quota_slide(prs):
    """課程衝突檢查與名額管理機制"""
    slide = add_slide_with_title(prs, "課程衝突檢查與名額管理")
    
    content = [
        "課程衝突檢查",
        "  • 同一星期檢查：只有同一天的課程可能衝突",
        "  • 節次重疊檢查：使用區間重疊演算法",
        "  • 不重疊條件：end1 < start2 或 end2 < start1",
        "  • 拒絕衝突選課並明確提示原因",
        "",
        "名額管理機制",
        "  • 單例模式：所有使用者共用同一份課程資料",
        "  • 執行緒鎖定：防止並發選課問題",
        "  • 即時更新：選課後名額立即減少",
        "  • 釋放機制：退選後名額立即增加",
        "  • 防止超額：額滿課程拒絕選課",
        "  • 防止重複：使用 Set 儲存選課清單",
    ]
    
    add_bullet_content(slide, content)


def add_data_storage_slide(prs):
    """資料儲存方式、限制及安全設計"""
    slide = add_slide_with_title(prs, "資料儲存與安全設計")
    
    content = [
        "資料儲存方式",
        "  • 記憶體儲存：Python 字典 (Dict) 與集合 (Set)",
        "  • 課程目錄：course_id -> Course 物件",
        "  • 選課清單：user_id -> Set[course_id]",
        "  • 檔案式 Session：使用者識別（sessions/ 目錄）",
        "",
        "系統限制",
        "  • 伺服器重啟後資料重置為初始狀態",
        "  • 無法跨程序共用記憶體",
        "  • 單程序執行限制",
        "",
        "安全設計",
        "  • .env 未納入版本控制",
        "  • SECRET_KEY 從環境變數讀取",
        "  • CSRF 防護啟用",
        "  • 所有 POST 請求使用 CSRF Token",
    ]
    
    add_bullet_content(slide, content)


def add_execution_slide(prs):
    """本機執行方式與展示流程"""
    slide = add_slide_with_title(prs, "本機執行方式")
    
    content = [
        "環境需求",
        "  • Windows 10/11",
        "  • Python 3.12 或以上",
        "",
        "安裝步驟",
        "  1. Clone 專案：git clone [repository-url]",
        "  2. 建立虛擬環境：python -m venv .venv",
        "  3. 啟動虛擬環境：.venv\\Scripts\\Activate.ps1",
        "  4. 安裝依賴：pip install -r requirements.txt",
        "  5. 建立 .env：copy .env.example .env",
        "",
        "啟動方式",
        "  • 使用啟動腳本：.\\start.ps1 或 start.bat",
        "  • 手動啟動：python manage.py runserver 127.0.0.1:8000",
        "  • 訪問系統：http://127.0.0.1:8000",
    ]
    
    add_bullet_content(slide, content)


def add_conclusion_slide(prs):
    """專題總結與未來擴充方向"""
    slide = add_slide_with_title(prs, "專題總結與未來擴充")
    
    content = [
        "專題總結",
        "  ✓ 成功實作完整的課表維護功能",
        "  ✓ 精確的選課規則與衝突檢查",
        "  ✓ 正確的名額管理機制",
        "  ✓ 清楚的系統架構與程式碼",
        "  ✓ 適合課堂展示與教學",
        "",
        "未來擴充方向",
        "  • 加入資料庫實現資料持久化",
        "  • 實作使用者註冊與登入",
        "  • 新增學分上限與先修課程限制",
        "  • 加入 Email 通知功能",
        "  • 實作課程評價系統",
        "  • 提供 RESTful API 介面",
        "  • 支援課表匯出（PDF、iCal）",
    ]
    
    add_bullet_content(slide, content)


def add_slide_with_title(prs, title_text):
    """建立帶標題的投影片"""
    title_layout = prs.slide_layouts[5]  # 標題與內容
    slide = prs.slides.add_slide(title_layout)
    
    title = slide.shapes.title
    title.text = title_text
    title.text_frame.paragraphs[0].font.size = Pt(36)
    title.text_frame.paragraphs[0].font.bold = True
    title.text_frame.paragraphs[0].font.color.rgb = RGBColor(37, 99, 235)
    
    return slide


def add_bullet_content(slide, content_lines):
    """新增條列內容"""
    textbox = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(9), Inches(5.5))
    text_frame = textbox.text_frame
    text_frame.word_wrap = True
    
    for i, line in enumerate(content_lines):
        if i > 0:
            p = text_frame.add_paragraph()
        else:
            p = text_frame.paragraphs[0]
        
        p.text = line
        p.font.size = Pt(18)
        
        if line and not line.startswith("  "):
            # 主標題
            p.font.bold = True
            p.space_before = Pt(12)
        else:
            # 子項目
            p.space_before = Pt(4)


def main():
    """主程式"""
    print("開始產生簡報...")
    
    # 建立簡報
    prs = create_presentation()
    
    # 儲存檔案
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'docs')
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, '個人課表維護系統_期中報告.pptx')
    prs.save(output_file)
    
    print(f"[OK] 簡報已成功產生：{output_file}")
    print(f"[OK] 簡報共 {len(prs.slides)} 頁")
    print("\n請使用 PowerPoint 或相容軟體開啟編輯。")
    print("記得填寫封面的課程名稱、組員姓名及指導教師資訊。")


if __name__ == '__main__':
    main()
