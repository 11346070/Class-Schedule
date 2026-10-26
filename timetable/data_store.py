"""
課程資料結構及記憶體儲存管理

本專題不使用資料庫，所有資料存儲於 Python 記憶體中。
重要限制：
- 伺服器重啟後資料會重置
- 多個 Worker 或程序無法共用記憶體
- 本專題採用單一 Django 程序執行
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import threading


@dataclass
class Course:
    """課程資料類別"""
    course_id: str  # 課程編號
    name: str  # 課程名稱
    teacher: str  # 授課教師
    weekday: int  # 星期（1=週一, 7=週日）
    start_period: int  # 開始節次
    end_period: int  # 結束節次
    credits: int  # 學分
    course_type: str  # 課程類型（必修、選修、通識）
    target_class: str  # 開課班級
    total_quota: int  # 課程總名額
    enrolled_count: int = 0  # 目前選課人數
    
    def __post_init__(self):
        """驗證資料合法性"""
        if not 1 <= self.weekday <= 7:
            raise ValueError(f"星期必須在 1-7 之間：{self.weekday}")
        if self.start_period > self.end_period:
            raise ValueError(f"開始節次不能大於結束節次：{self.start_period} > {self.end_period}")
        if self.credits <= 0:
            raise ValueError(f"學分必須大於 0：{self.credits}")
        if self.total_quota <= 0:
            raise ValueError(f"課程名額必須大於 0：{self.total_quota}")
    
    @property
    def remaining_quota(self) -> int:
        """剩餘名額"""
        return self.total_quota - self.enrolled_count
    
    @property
    def is_full(self) -> bool:
        """是否已額滿"""
        return self.enrolled_count >= self.total_quota
    
    def get_weekday_name(self) -> str:
        """取得星期中文名稱"""
        weekday_names = {
            1: "週一", 2: "週二", 3: "週三", 
            4: "週四", 5: "週五", 6: "週六", 7: "週日"
        }
        return weekday_names.get(self.weekday, "未知")
    
    def get_time_display(self) -> str:
        """取得時段顯示字串"""
        return f"{self.get_weekday_name()} 第{self.start_period}-{self.end_period}節"
    
    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            'course_id': self.course_id,
            'name': self.name,
            'teacher': self.teacher,
            'weekday': self.weekday,
            'weekday_name': self.get_weekday_name(),
            'start_period': self.start_period,
            'end_period': self.end_period,
            'time_display': self.get_time_display(),
            'credits': self.credits,
            'course_type': self.course_type,
            'target_class': self.target_class,
            'total_quota': self.total_quota,
            'enrolled_count': self.enrolled_count,
            'remaining_quota': self.remaining_quota,
            'is_full': self.is_full,
        }


class CourseDataStore:
    """
    課程資料儲存管理（記憶體儲存）
    使用單例模式確保所有使用者共用同一份課程資料
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 課程目錄：course_id -> Course
        self.courses: Dict[str, Course] = {}
        
        # 使用者選課清單：user_id -> Set[course_id]
        self.user_enrollments: Dict[str, Set[str]] = {}
        
        # 執行緒鎖定（防止並發問題）
        self.lock = threading.Lock()
        
        self._initialized = True
        
        # 初始化示範課程資料
        self._init_sample_courses()
    
    def _init_sample_courses(self):
        """初始化示範課程資料"""
        sample_courses = [
            # 資訊工程系課程
            Course("CS101", "程式設計(一)", "王教授", 1, 2, 4, 3, "必修", "資工一", 60),
            Course("CS102", "離散數學", "李教授", 2, 2, 4, 3, "必修", "資工一", 60),
            Course("CS103", "計算機概論", "張教授", 3, 6, 8, 3, "必修", "資工一", 60),
            Course("CS201", "資料結構", "陳教授", 1, 6, 8, 3, "必修", "資工二", 55),
            Course("CS202", "演算法", "林教授", 4, 2, 4, 3, "必修", "資工二", 55),
            Course("CS203", "作業系統", "黃教授", 5, 2, 4, 3, "必修", "資工二", 55),
            Course("CS301", "資料庫系統", "劉教授", 2, 6, 8, 3, "選修", "資工三", 50),
            Course("CS302", "人工智慧", "吳教授", 3, 2, 4, 3, "選修", "資工三", 45),
            Course("CS303", "機器學習", "鄭教授", 4, 6, 8, 3, "選修", "資工三", 40),
            Course("CS304", "網路程式設計", "周教授", 1, 6, 8, 3, "選修", "資工三", 45),
            
            # 通識課程
            Course("GE101", "中國文學欣賞", "文教授", 1, 2, 3, 2, "通識", "全校", 120),
            Course("GE102", "英文寫作", "外教授", 2, 2, 3, 2, "通識", "全校", 100),
            Course("GE103", "歷史與文化", "史教授", 3, 2, 3, 2, "通識", "全校", 100),
            Course("GE104", "哲學與人生", "哲教授", 4, 2, 3, 2, "通識", "全校", 80),
            Course("GE201", "經濟學原理", "經教授", 1, 6, 7, 2, "通識", "全校", 100),
            Course("GE202", "心理學導論", "心教授", 2, 6, 7, 2, "通識", "全校", 90),
            Course("GE203", "社會學概論", "社教授", 3, 6, 7, 2, "通識", "全校", 85),
            Course("GE204", "環境科學", "環教授", 5, 6, 7, 2, "通識", "全校", 75),
            
            # 體育與藝術
            Course("PE101", "體育(一)", "體教授", 2, 8, 9, 1, "必修", "全校", 50),
            Course("PE102", "體育(二)", "運教授", 4, 8, 9, 1, "必修", "全校", 50),
            Course("ART101", "音樂欣賞", "音教授", 3, 8, 9, 2, "選修", "全校", 60),
            Course("ART102", "美術創作", "美教授", 5, 8, 9, 2, "選修", "全校", 40),
            
            # 測試用課程（小名額、時段衝突）
            Course("TEST01", "進階專題研究", "專教授", 1, 3, 4, 2, "選修", "資工三", 2),  # 名額少
            Course("TEST02", "獨立研究", "研教授", 1, 3, 5, 3, "選修", "資工三", 3),  # 與 TEST01 衝突
        ]
        
        for course in sample_courses:
            self.courses[course.course_id] = course
    
    def get_course(self, course_id: str) -> Optional[Course]:
        """取得課程"""
        return self.courses.get(course_id)
    
    def get_all_courses(self) -> List[Course]:
        """取得所有課程"""
        return list(self.courses.values())
    
    def search_courses(self, keyword: str = "", course_type: str = "", weekday: int = 0) -> List[Course]:
        """
        搜尋課程
        keyword: 關鍵字（課程名稱或教師）
        course_type: 課程類型篩選
        weekday: 星期篩選（0 表示不篩選）
        """
        results = []
        for course in self.courses.values():
            # 關鍵字搜尋
            if keyword:
                keyword_lower = keyword.lower()
                if (keyword_lower not in course.name.lower() and 
                    keyword_lower not in course.teacher.lower() and
                    keyword_lower not in course.course_id.lower()):
                    continue
            
            # 課程類型篩選
            if course_type and course.course_type != course_type:
                continue
            
            # 星期篩選
            if weekday > 0 and course.weekday != weekday:
                continue
            
            results.append(course)
        
        return results
    
    def get_user_enrollments(self, user_id: str) -> List[Course]:
        """取得使用者已選課程"""
        if user_id not in self.user_enrollments:
            return []
        
        course_ids = self.user_enrollments[user_id]
        return [self.courses[cid] for cid in course_ids if cid in self.courses]
    
    def is_user_enrolled(self, user_id: str, course_id: str) -> bool:
        """檢查使用者是否已選此課程"""
        if user_id not in self.user_enrollments:
            return False
        return course_id in self.user_enrollments[user_id]
    
    def enroll_course(self, user_id: str, course_id: str) -> tuple[bool, str]:
        """
        選課
        返回：(是否成功, 訊息)
        """
        with self.lock:
            # 檢查課程是否存在
            course = self.get_course(course_id)
            if not course:
                return False, "課程不存在"
            
            # 檢查是否已選過
            if self.is_user_enrolled(user_id, course_id):
                return False, "您已經選過這門課程"
            
            # 檢查名額
            if course.is_full:
                return False, f"課程已額滿（{course.total_quota}/{course.total_quota}）"
            
            # 檢查時間衝突
            conflict_course = self._check_time_conflict(user_id, course)
            if conflict_course:
                return False, f"時間衝突：與「{conflict_course.name}」（{conflict_course.get_time_display()}）衝堂"
            
            # 選課成功
            if user_id not in self.user_enrollments:
                self.user_enrollments[user_id] = set()
            
            self.user_enrollments[user_id].add(course_id)
            course.enrolled_count += 1
            
            return True, f"選課成功！剩餘名額：{course.remaining_quota}"
    
    def drop_course(self, user_id: str, course_id: str) -> tuple[bool, str]:
        """
        退選課程
        返回：(是否成功, 訊息)
        """
        with self.lock:
            # 檢查課程是否存在
            course = self.get_course(course_id)
            if not course:
                return False, "課程不存在"
            
            # 檢查是否已選過
            if not self.is_user_enrolled(user_id, course_id):
                return False, "您尚未選修此課程"
            
            # 退選成功
            self.user_enrollments[user_id].remove(course_id)
            course.enrolled_count -= 1
            
            return True, "退選成功"
    
    def _check_time_conflict(self, user_id: str, new_course: Course) -> Optional[Course]:
        """
        檢查時間衝突
        返回：衝突的課程（若無衝突則返回 None）
        """
        enrolled_courses = self.get_user_enrollments(user_id)
        
        for existing_course in enrolled_courses:
            # 不同星期不會衝突
            if existing_course.weekday != new_course.weekday:
                continue
            
            # 檢查節次是否重疊
            if self._periods_overlap(
                existing_course.start_period, existing_course.end_period,
                new_course.start_period, new_course.end_period
            ):
                return existing_course
        
        return None
    
    @staticmethod
    def _periods_overlap(start1: int, end1: int, start2: int, end2: int) -> bool:
        """
        檢查兩個時段是否重疊
        例如：[2,4] 與 [3,5] 重疊
              [2,4] 與 [5,7] 不重疊
        """
        return not (end1 < start2 or end2 < start1)
    
    def get_user_total_credits(self, user_id: str) -> int:
        """計算使用者已選總學分"""
        enrolled_courses = self.get_user_enrollments(user_id)
        return sum(course.credits for course in enrolled_courses)
    
    def reset_all_data(self):
        """重置所有資料（用於測試或系統重置）"""
        with self.lock:
            self.user_enrollments.clear()
            for course in self.courses.values():
                course.enrolled_count = 0


# 建立全域單例
course_store = CourseDataStore()
