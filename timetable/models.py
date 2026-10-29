"""
課程與選課相關資料模型（SQLite）
"""

from django.core.exceptions import ValidationError
from django.db import models

DEFAULT_CREDIT_LIMIT = 25
DEFAULT_CREDIT_FLOOR = 9
MODULE_INFO = "資訊"
MODULE_FINANCE = "金融"
MODULE_CHOICES = [
    (MODULE_INFO, "資訊"),
    (MODULE_FINANCE, "金融"),
]
MIN_PERIOD = 1
MAX_PERIOD = 13
MIN_CREDITS = 1
MAX_CREDITS = 6

WEEKDAY_NAMES = {
    1: "週一", 2: "週二", 3: "週三",
    4: "週四", 5: "週五", 6: "週六", 7: "週日",
}


class Course(models.Model):
    """課程"""
    course_id = models.CharField("課程編號", max_length=20, primary_key=True)
    name = models.CharField("課程名稱", max_length=100)
    teacher = models.CharField("授課教師", max_length=50)
    weekday = models.PositiveSmallIntegerField("星期")  # 1-7
    start_period = models.PositiveSmallIntegerField("開始節次")
    end_period = models.PositiveSmallIntegerField("結束節次")
    credits = models.PositiveSmallIntegerField("學分")
    course_type = models.CharField("課程類型", max_length=20)  # 必修、選修、通識
    module = models.CharField("所屬模組", max_length=20, blank=True, default="")
    target_class = models.CharField("開課班級", max_length=50)
    total_quota = models.PositiveIntegerField("總名額")
    enrolled_count = models.PositiveIntegerField("已選人數", default=0)

    class Meta:
        ordering = ["course_id"]

    def __str__(self):
        return f"{self.course_id} {self.name}"

    @property
    def remaining_quota(self) -> int:
        return self.total_quota - self.enrolled_count

    @property
    def is_full(self) -> bool:
        return self.enrolled_count >= self.total_quota

    def clean(self):
        """後台維護課程時，檢查星期、節次、學分與名額是否合理。"""
        super().clean()
        errors = {}

        if self.weekday is not None and self.weekday not in WEEKDAY_NAMES:
            errors["weekday"] = "星期必須介於 1（週一）到 7（週日）。"

        for field_name in ("start_period", "end_period"):
            value = getattr(self, field_name)
            if value is not None and not (MIN_PERIOD <= value <= MAX_PERIOD):
                errors[field_name] = f"節次必須介於 {MIN_PERIOD} 到 {MAX_PERIOD}。"

        if (
            self.start_period is not None
            and self.end_period is not None
            and "start_period" not in errors
            and "end_period" not in errors
            and self.start_period > self.end_period
        ):
            errors["end_period"] = "結束節次不可早於開始節次。"

        if self.credits is not None and not (MIN_CREDITS <= self.credits <= MAX_CREDITS):
            errors["credits"] = f"學分必須介於 {MIN_CREDITS} 到 {MAX_CREDITS}。"

        if self.total_quota is not None and self.total_quota < 1:
            errors["total_quota"] = "總名額必須大於 0。"
        elif (
            self.total_quota is not None
            and self.enrolled_count is not None
            and self.total_quota < self.enrolled_count
        ):
            errors["total_quota"] = (
                f"總名額不可少於已選人數（目前已選 {self.enrolled_count} 人）。"
            )

        if errors:
            raise ValidationError(errors)

    def get_weekday_name(self) -> str:
        return WEEKDAY_NAMES.get(self.weekday, "未知")

    def get_time_display(self) -> str:
        return f"{self.get_weekday_name()} 第{self.start_period}-{self.end_period}節"

    def to_dict(self) -> dict:
        return {
            "course_id": self.course_id,
            "name": self.name,
            "teacher": self.teacher,
            "weekday": self.weekday,
            "weekday_name": self.get_weekday_name(),
            "start_period": self.start_period,
            "end_period": self.end_period,
            "time_display": self.get_time_display(),
            "credits": self.credits,
            "course_type": self.course_type,
            "module": self.module,
            "target_class": self.target_class,
            "total_quota": self.total_quota,
            "enrolled_count": self.enrolled_count,
            "remaining_quota": self.remaining_quota,
            "is_full": self.is_full,
        }


class Enrollment(models.Model):
    """使用者選課紀錄"""
    user_id = models.CharField("使用者 ID", max_length=64, db_index=True)
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="enrollments"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user_id", "course")]
        indexes = [
            models.Index(fields=["user_id"]),
        ]

    def __str__(self):
        return f"{self.user_id} -> {self.course_id}"


class Favorite(models.Model):
    """使用者收藏紀錄"""
    user_id = models.CharField("使用者 ID", max_length=64, db_index=True)
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="favorites"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user_id", "course")]
        indexes = [
            models.Index(fields=["user_id"]),
        ]

    def __str__(self):
        return f"{self.user_id} ★ {self.course_id}"


class GraduationRequirement(models.Model):
    """畢業學分門檻（全系統一份，由管理員調整）。"""
    total_credits = models.PositiveIntegerField("畢業總學分", default=128)
    required_credits = models.PositiveIntegerField("必修門檻", default=60)
    elective_credits = models.PositiveIntegerField("選修門檻", default=40)
    general_credits = models.PositiveIntegerField("通識門檻", default=28)
    recognition_cap = models.PositiveIntegerField("模組認列上限", default=9)

    class Meta:
        verbose_name = "畢業門檻"
        verbose_name_plural = "畢業門檻"

    def __str__(self):
        return f"畢業 {self.total_credits} 學分"


class StudyRecord(models.Model):
    """歷年修課紀錄。已通過的學分才計入畢業「已取得」。"""
    STATUS_PASSED = "passed"
    STATUS_FAILED = "failed"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_CHOICES = [
        (STATUS_PASSED, "已通過"),
        (STATUS_FAILED, "未通過"),
        (STATUS_IN_PROGRESS, "正在修"),
    ]

    user_id = models.CharField("使用者 ID", max_length=64, db_index=True)
    course = models.ForeignKey(
        Course,
        verbose_name="課程",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="study_records",
    )
    course_code = models.CharField("課程編號", max_length=20)
    course_name = models.CharField("課程名稱", max_length=100)
    credits = models.PositiveSmallIntegerField("學分")
    course_type = models.CharField("課程類型", max_length=20)
    module = models.CharField("所屬模組", max_length=20, blank=True, default="")
    semester = models.CharField("學期", max_length=20, help_text="例如 113-1")
    status = models.CharField("狀態", max_length=20, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-semester", "course_code"]
        verbose_name = "歷年修課紀錄"
        verbose_name_plural = "歷年修課紀錄"

    def __str__(self):
        return f"{self.user_id} {self.semester} {self.course_code} {self.get_status_display()}"


class CourseReview(models.Model):
    """修過的學生對作業量與考試難度的評價。"""
    HOMEWORK_CHOICES = [("多", "多"), ("適中", "適中"), ("少", "少")]
    EXAM_CHOICES = [("難", "難"), ("適中", "適中"), ("易", "易")]

    user_id = models.CharField("使用者 ID", max_length=64, db_index=True)
    course = models.ForeignKey(
        Course, verbose_name="課程", on_delete=models.CASCADE, related_name="reviews"
    )
    homework = models.CharField("作業量", max_length=10, choices=HOMEWORK_CHOICES)
    exam = models.CharField("考試難度", max_length=10, choices=EXAM_CHOICES)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user_id", "course")]
        verbose_name = "課程評價"
        verbose_name_plural = "課程評價"

    def __str__(self):
        return f"{self.user_id} {self.course_id} 作業{self.homework} 考試{self.exam}"


class StudentProfile(models.Model):
    """學生選擇的主修模組。另一模組學分最多認列到上限。"""
    user_id = models.CharField("使用者 ID", max_length=64, primary_key=True)
    module = models.CharField("主修模組", max_length=20, blank=True, default="")
    notify_at_floor = models.BooleanField("已達退選下限時提醒", default=True)
    notify_near_floor = models.BooleanField("接近退選下限時提醒", default=True)
    notify_at_limit = models.BooleanField("已達學分上限時提醒", default=True)

    class Meta:
        verbose_name = "學生模組"
        verbose_name_plural = "學生模組"

    def __str__(self):
        return f"{self.user_id}: {self.module or '未選'}"


class UserCreditLimit(models.Model):
    """使用者學分上限與下限"""
    user_id = models.CharField("使用者 ID", max_length=64, primary_key=True)
    credit_limit = models.PositiveIntegerField("學分上限", default=DEFAULT_CREDIT_LIMIT)
    credit_floor = models.PositiveIntegerField("學分下限", default=DEFAULT_CREDIT_FLOOR)

    def __str__(self):
        return f"{self.user_id}: {self.credit_floor}–{self.credit_limit}"
