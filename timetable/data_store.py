"""
課程資料存取層（SQLite / Django ORM）

對外 API 與原先記憶體版相容，views 無需大改。
資料持久化於 SQLite，伺服器重啟後選課／收藏資料仍保留。
"""

from typing import List, Optional, Tuple
import threading

from django.db import transaction
from django.db.models import Q

from .models import (
    Course,
    Enrollment,
    Favorite,
    GraduationRequirement,
    StudyRecord,
    UserCreditLimit,
    DEFAULT_CREDIT_FLOOR,
    DEFAULT_CREDIT_LIMIT,
)

# 對外仍可引用
__all__ = ["Course", "CourseDataStore", "course_store", "DEFAULT_CREDIT_LIMIT"]


SAMPLE_COURSES = [
    # 資訊工程系課程
    ("CS101", "程式設計(一)", "王教授", 1, 2, 4, 3, "必修", "資工一", 60),
    ("CS102", "離散數學", "李教授", 2, 2, 4, 3, "必修", "資工一", 60),
    ("CS103", "計算機概論", "張教授", 3, 6, 8, 3, "必修", "資工一", 60),
    ("CS201", "資料結構", "陳教授", 1, 6, 8, 3, "必修", "資工二", 55),
    ("CS202", "演算法", "林教授", 4, 2, 4, 3, "必修", "資工二", 55),
    ("CS203", "作業系統", "黃教授", 5, 2, 4, 3, "必修", "資工二", 55),
    ("CS301", "資料庫系統", "劉教授", 2, 6, 8, 3, "選修", "資工三", 50),
    ("CS302", "人工智慧", "吳教授", 3, 2, 4, 3, "選修", "資工三", 45),
    ("CS303", "機器學習", "鄭教授", 4, 6, 8, 3, "選修", "資工三", 40),
    ("CS304", "網路程式設計", "周教授", 1, 6, 8, 3, "選修", "資工三", 45),
    # 通識課程
    ("GE101", "中國文學欣賞", "文教授", 1, 2, 3, 2, "通識", "全校", 120),
    ("GE102", "英文寫作", "外教授", 2, 2, 3, 2, "通識", "全校", 100),
    ("GE103", "歷史與文化", "史教授", 3, 2, 3, 2, "通識", "全校", 100),
    ("GE104", "哲學與人生", "哲教授", 4, 2, 3, 2, "通識", "全校", 80),
    ("GE201", "經濟學原理", "經教授", 1, 6, 7, 2, "通識", "全校", 100),
    ("GE202", "心理學導論", "心教授", 2, 6, 7, 2, "通識", "全校", 90),
    ("GE203", "社會學概論", "社教授", 3, 6, 7, 2, "通識", "全校", 85),
    ("GE204", "環境科學", "環教授", 5, 6, 7, 2, "通識", "全校", 75),
    # 體育與藝術
    ("PE101", "體育(一)", "體教授", 2, 8, 9, 1, "必修", "全校", 50),
    ("PE102", "體育(二)", "運教授", 4, 8, 9, 1, "必修", "全校", 50),
    ("ART101", "音樂欣賞", "音教授", 3, 8, 9, 2, "選修", "全校", 60),
    ("ART102", "美術創作", "美教授", 5, 8, 9, 2, "選修", "全校", 40),
    # 測試用課程（小名額、時段衝突）
    ("TEST01", "進階專題研究", "專教授", 1, 3, 4, 2, "選修", "資工三", 2),
    ("TEST02", "獨立研究", "研教授", 1, 3, 5, 3, "選修", "資工三", 3),
]


class CourseDataStore:
    """
    課程資料儲存管理（SQLite）
    使用單例模式；對外方法與舊版記憶體 API 相容。
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
        self.lock = threading.Lock()
        self._initialized = True

    def ensure_seeded(self):
        """若資料庫尚無課程，寫入示範資料"""
        if Course.objects.exists():
            return
        with self.lock:
            if Course.objects.exists():
                return
            Course.objects.bulk_create([
                Course(
                    course_id=cid,
                    name=name,
                    teacher=teacher,
                    weekday=weekday,
                    start_period=start,
                    end_period=end,
                    credits=credits,
                    course_type=ctype,
                    target_class=target,
                    total_quota=quota,
                    enrolled_count=0,
                )
                for cid, name, teacher, weekday, start, end, credits, ctype, target, quota
                in SAMPLE_COURSES
            ])

    def get_course(self, course_id: str) -> Optional[Course]:
        self.ensure_seeded()
        try:
            return Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            return None

    def get_all_courses(self) -> List[Course]:
        self.ensure_seeded()
        return list(Course.objects.all())

    def search_courses(
        self, keyword: str = "", course_type: str = "", weekday: int = 0
    ) -> List[Course]:
        self.ensure_seeded()
        qs = Course.objects.all()

        if keyword:
            qs = qs.filter(
                Q(name__icontains=keyword)
                | Q(teacher__icontains=keyword)
                | Q(course_id__icontains=keyword)
            )

        if course_type:
            qs = qs.filter(course_type=course_type)

        if weekday > 0:
            qs = qs.filter(weekday=weekday)

        return list(qs)

    def get_user_enrollments(self, user_id: str) -> List[Course]:
        self.ensure_seeded()
        return list(
            Course.objects.filter(enrollments__user_id=user_id).order_by(
                "weekday", "start_period"
            )
        )

    def is_user_enrolled(self, user_id: str, course_id: str) -> bool:
        return Enrollment.objects.filter(
            user_id=user_id, course_id=course_id
        ).exists()

    def _get_credit_rule(self, user_id: str) -> UserCreditLimit:
        rule, _ = UserCreditLimit.objects.get_or_create(
            user_id=user_id,
            defaults={
                "credit_limit": DEFAULT_CREDIT_LIMIT,
                "credit_floor": DEFAULT_CREDIT_FLOOR,
            },
        )
        return rule

    def get_user_credit_limit(self, user_id: str) -> int:
        if not user_id:
            return DEFAULT_CREDIT_LIMIT
        return self._get_credit_rule(user_id).credit_limit

    def get_user_credit_floor(self, user_id: str) -> int:
        if not user_id:
            return DEFAULT_CREDIT_FLOOR
        return self._get_credit_rule(user_id).credit_floor

    def set_user_credit_limit(self, user_id: str, limit: int) -> bool:
        if limit <= 0:
            return False
        UserCreditLimit.objects.update_or_create(
            user_id=user_id, defaults={"credit_limit": limit}
        )
        return True

    def check_enrollment_eligibility(
        self, user_id: str, course_id: str
    ) -> Tuple[bool, str]:
        course = self.get_course(course_id)
        if not course:
            return False, "課程不存在"

        if self.is_user_enrolled(user_id, course_id):
            return False, "您已經選過這門課程"

        if course.is_full:
            return False, f"課程已額滿（{course.total_quota}/{course.total_quota}）"

        conflict_course = self._check_time_conflict(user_id, course)
        if conflict_course:
            return (
                False,
                f"時間衝突：與「{conflict_course.name}」（{conflict_course.get_time_display()}）衝堂",
            )

        current_credits = self.get_user_total_credits(user_id)
        credit_limit = self.get_user_credit_limit(user_id)
        if current_credits + course.credits > credit_limit:
            return (
                False,
                f"超過學分上限：目前 {current_credits} 學分，選課後將達 "
                f"{current_credits + course.credits} 學分，上限為 {credit_limit} 學分",
            )

        return True, f"可以選課！選課後將有 {current_credits + course.credits} 學分"

    def enroll_course(self, user_id: str, course_id: str) -> Tuple[bool, str]:
        with self.lock:
            with transaction.atomic():
                try:
                    course = Course.objects.select_for_update().get(pk=course_id)
                except Course.DoesNotExist:
                    return False, "課程不存在"

                if Enrollment.objects.filter(
                    user_id=user_id, course=course
                ).exists():
                    return False, "您已經選過這門課程"

                if course.enrolled_count >= course.total_quota:
                    return False, f"課程已額滿（{course.total_quota}/{course.total_quota}）"

                conflict_course = self._check_time_conflict(user_id, course)
                if conflict_course:
                    return (
                        False,
                        f"時間衝突：與「{conflict_course.name}」（{conflict_course.get_time_display()}）衝堂",
                    )

                current_credits = self.get_user_total_credits(user_id)
                credit_limit = self.get_user_credit_limit(user_id)
                if current_credits + course.credits > credit_limit:
                    return (
                        False,
                        f"超過學分上限：目前 {current_credits} 學分，上限為 {credit_limit} 學分",
                    )

                Enrollment.objects.create(user_id=user_id, course=course)
                course.enrolled_count += 1
                course.save(update_fields=["enrolled_count"])

                return True, f"選課成功！剩餘名額：{course.remaining_quota}"

    def drop_course(
        self, user_id: str, course_id: str, force: bool = False
    ) -> Tuple[bool, str]:
        with self.lock:
            with transaction.atomic():
                try:
                    course = Course.objects.select_for_update().get(pk=course_id)
                except Course.DoesNotExist:
                    return False, "課程不存在"

                enrollment = (
                    Enrollment.objects.select_for_update()
                    .filter(user_id=user_id, course=course)
                    .first()
                )
                if enrollment is None:
                    return False, "您尚未選修此課程"

                current_credits = self.get_user_total_credits(user_id)
                credit_floor = self.get_user_credit_floor(user_id)
                remaining = current_credits - course.credits
                if not force and remaining < credit_floor:
                    return (
                        False,
                        f"低於學分下限：目前 {current_credits} 學分，退選後將剩 "
                        f"{remaining} 學分，下限為 {credit_floor} 學分。"
                        "請聯絡管理員協助退選。",
                    )

                enrollment.delete()
                if course.enrolled_count > 0:
                    course.enrolled_count -= 1
                    course.save(update_fields=["enrolled_count"])

                return True, "退選成功"

    def _check_time_conflict(
        self, user_id: str, new_course: Course
    ) -> Optional[Course]:
        enrolled_courses = self.get_user_enrollments(user_id)

        for existing_course in enrolled_courses:
            if existing_course.weekday != new_course.weekday:
                continue
            if self._periods_overlap(
                existing_course.start_period,
                existing_course.end_period,
                new_course.start_period,
                new_course.end_period,
            ):
                return existing_course
        return None

    @staticmethod
    def _periods_overlap(start1: int, end1: int, start2: int, end2: int) -> bool:
        return not (end1 < start2 or end2 < start1)

    def get_graduation_requirement(self) -> GraduationRequirement:
        rule, _ = GraduationRequirement.objects.get_or_create(
            pk=1,
            defaults={
                "total_credits": 128,
                "required_credits": 60,
                "elective_credits": 40,
                "general_credits": 28,
            },
        )
        return rule

    def get_graduation_summary(self, user_id: str) -> dict:
        """已取得只算歷年「已通過」；本學期選課另計為正在修。"""
        rule = self.get_graduation_requirement()
        passed = {"必修": 0, "選修": 0, "通識": 0}
        for record in StudyRecord.objects.filter(
            user_id=user_id, status=StudyRecord.STATUS_PASSED
        ):
            if record.course_type in passed:
                passed[record.course_type] += record.credits

        in_progress = {"必修": 0, "選修": 0, "通識": 0}
        for course in self.get_user_enrollments(user_id):
            if course.course_type in in_progress:
                in_progress[course.course_type] += course.credits

        earned_total = sum(passed.values())

        def gap(have, need):
            return max(need - have, 0)

        return {
            "total_required": rule.total_credits,
            "earned_total": earned_total,
            "remaining_total": gap(earned_total, rule.total_credits),
            "required": {
                "need": rule.required_credits,
                "earned": passed["必修"],
                "gap": gap(passed["必修"], rule.required_credits),
                "in_progress": in_progress["必修"],
            },
            "elective": {
                "need": rule.elective_credits,
                "earned": passed["選修"],
                "gap": gap(passed["選修"], rule.elective_credits),
                "in_progress": in_progress["選修"],
            },
            "general": {
                "need": rule.general_credits,
                "earned": passed["通識"],
                "gap": gap(passed["通識"], rule.general_credits),
                "in_progress": in_progress["通識"],
            },
            "in_progress_total": sum(in_progress.values()),
        }

    def get_user_total_credits(self, user_id: str) -> int:
        enrolled_courses = self.get_user_enrollments(user_id)
        return sum(course.credits for course in enrolled_courses)

    def is_course_favorited(self, user_id: str, course_id: str) -> bool:
        return Favorite.objects.filter(
            user_id=user_id, course_id=course_id
        ).exists()

    def add_favorite(self, user_id: str, course_id: str) -> Tuple[bool, str]:
        with self.lock:
            course = self.get_course(course_id)
            if not course:
                return False, "課程不存在"

            if self.is_course_favorited(user_id, course_id):
                return False, "您已經收藏過這門課程"

            Favorite.objects.create(user_id=user_id, course=course)
            return True, f"已收藏「{course.name}」"

    def remove_favorite(self, user_id: str, course_id: str) -> Tuple[bool, str]:
        with self.lock:
            course = self.get_course(course_id)
            if not course:
                return False, "課程不存在"

            deleted, _ = Favorite.objects.filter(
                user_id=user_id, course=course
            ).delete()
            if not deleted:
                return False, "您尚未收藏此課程"

            return True, f"已取消收藏「{course.name}」"

    def get_user_favorites(self, user_id: str) -> List[Course]:
        self.ensure_seeded()
        return list(Course.objects.filter(favorites__user_id=user_id))

    def get_free_periods(self, user_id: str):
        """計算空堂節次（保留 API，目前首頁未使用）"""
        enrolled_courses = self.get_user_enrollments(user_id)
        free_periods = {weekday: list(range(1, 14)) for weekday in range(1, 8)}
        for course in enrolled_courses:
            for period in range(course.start_period, course.end_period + 1):
                if period in free_periods[course.weekday]:
                    free_periods[course.weekday].remove(period)
        return free_periods


# 全域單例（延遲連線資料庫，首次操作時才 seed）
course_store = CourseDataStore()
