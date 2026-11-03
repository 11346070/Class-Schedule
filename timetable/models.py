"""
課程與選課相關資料模型（SQLite）
"""

import re
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import models

COURSE_TYPE_REQUIRED = "必修"
COURSE_TYPE_ELECTIVE = "選修"
COURSE_TYPE_GENERAL = "通識"
COURSE_TYPE_CHOICES = [
    (COURSE_TYPE_REQUIRED, "必修"),
    (COURSE_TYPE_ELECTIVE, "選修"),
    (COURSE_TYPE_GENERAL, "通識"),
]
COURSE_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]+")


def syllabus_upload_to(instance, filename):
    """檔名只用課程編號，避免沿用上傳路徑。"""
    safe_id = COURSE_ID_PATTERN.fullmatch(instance.course_id or "")
    return f"syllabi/{safe_id.group(0) if safe_id else 'course'}.pdf"


def avatar_upload_to(instance, filename):
    """只用使用者自己的 ID 當檔名，避免沿用上傳檔名。"""
    suffix = Path(filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".img"
    return f"avatars/{instance.user_id}{suffix}"

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


class Classroom(models.Model):
    """上課地點。課程連結到這裡，改名後已開的課會跟著顯示新名稱。"""
    name = models.CharField("教室名稱", max_length=50, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "教室"
        verbose_name_plural = "教室"

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        self.name = (self.name or "").strip()
        if not self.name:
            raise ValidationError({"name": "請填寫教室名稱。"})

    def save(self, *args, **kwargs):
        self.name = (self.name or "").strip()
        super().save(*args, **kwargs)


class Teacher(models.Model):
    """授課教師。課程連結到這裡，改名後已開的課會跟著顯示新姓名。"""
    name = models.CharField("教師姓名", max_length=50, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "教師"
        verbose_name_plural = "教師"

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        self.name = (self.name or "").strip()
        if not self.name:
            raise ValidationError({"name": "請填寫教師姓名。"})

    def save(self, *args, **kwargs):
        self.name = (self.name or "").strip()
        super().save(*args, **kwargs)


class Course(models.Model):
    """課程"""
    course_id = models.CharField("課程編號", max_length=20, primary_key=True)
    name = models.CharField("課程名稱", max_length=100)
    teacher = models.ForeignKey(
        Teacher,
        verbose_name="授課教師",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="courses",
    )
    weekday = models.PositiveSmallIntegerField("星期")  # 1-7
    start_period = models.PositiveSmallIntegerField("開始節次")
    end_period = models.PositiveSmallIntegerField("結束節次")
    credits = models.PositiveSmallIntegerField("學分")
    course_type = models.CharField(
        "課程類型",
        max_length=20,
        choices=COURSE_TYPE_CHOICES,
        help_text="選「必修」後，開課班級相同的學生會自動加入這門課，而且不能退選。",
    )
    module = models.CharField("所屬模組", max_length=20, blank=True, default="")
    syllabus = models.FileField("課程大綱 PDF", upload_to=syllabus_upload_to, blank=True)
    school_class = models.ForeignKey(
        "SchoolClass",
        verbose_name="開課班級",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="courses",
    )
    opens_to_all = models.BooleanField("開放全校", default=False)
    classroom = models.ForeignKey(
        Classroom,
        verbose_name="教室",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="courses",
    )
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

    def __init__(self, *args, **kwargs):
        target_class = kwargs.pop("target_class", None)
        teacher_name = None
        classroom_name = None
        if isinstance(kwargs.get("teacher"), str):
            teacher_name = kwargs.pop("teacher")
        if isinstance(kwargs.get("classroom"), str):
            classroom_name = kwargs.pop("classroom")
        super().__init__(*args, **kwargs)
        if classroom_name is not None:
            label = classroom_name.strip()
            if label:
                self.classroom, _created = Classroom.objects.get_or_create(name=label)
            else:
                self.classroom = None
        if teacher_name is not None:
            label = teacher_name.strip()
            if label:
                self.teacher, _created = Teacher.objects.get_or_create(name=label)
            else:
                self.teacher = None
        if target_class is not None:
            self.target_class = target_class

    def _get_target_class(self):
        if self.opens_to_all:
            return "全校"
        if self.school_class_id:
            return self.school_class.name
        return ""

    _get_target_class.short_description = "開課班級"

    def _set_target_class(self, value):
        label = (value or "").strip()
        if label == "全校":
            self.opens_to_all = True
            self.school_class = None
            return
        self.opens_to_all = False
        if not label:
            self.school_class = None
            return
        if self.school_class_id and self.school_class.name == label:
            return
        self.school_class, _created = SchoolClass.objects.get_or_create(name=label)

    target_class = property(_get_target_class, _set_target_class)

    def clean(self):
        """後台維護課程時，檢查星期、節次、學分與名額是否合理。"""
        super().clean()
        errors = {}
        self.course_type = (self.course_type or "").strip()
        self.course_id = (self.course_id or "").strip()
        if self.opens_to_all and self.school_class_id:
            errors["school_class"] = "全校課程不用再指定班級。"

        if self.course_id and COURSE_ID_PATTERN.fullmatch(self.course_id) is None:
            errors["course_id"] = "課程編號只能使用英數、底線或連字號。"

        if self.course_type and self.course_type not in dict(COURSE_TYPE_CHOICES):
            errors["course_type"] = "課程類型必須是必修、選修或通識。"

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

    def save(self, *args, **kwargs):
        self.course_type = (self.course_type or "").strip()
        self.module = (self.module or "").strip()
        if self.course_id:
            self.course_id = self.course_id.strip()
        super().save(*args, **kwargs)

    def get_weekday_name(self) -> str:
        return WEEKDAY_NAMES.get(self.weekday, "未知")

    def get_time_display(self) -> str:
        return f"{self.get_weekday_name()} 第{self.start_period}-{self.end_period}節"

    def to_dict(self) -> dict:
        return {
            "course_id": self.course_id,
            "name": self.name,
            "teacher": self.teacher.name if self.teacher_id else "",
            "weekday": self.weekday,
            "weekday_name": self.get_weekday_name(),
            "start_period": self.start_period,
            "end_period": self.end_period,
            "time_display": self.get_time_display(),
            "credits": self.credits,
            "course_type": self.course_type,
            "module": self.module,
            "target_class": self.target_class,
            "classroom": self.classroom.name if self.classroom_id else "",
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
    """歷年修課紀錄。已通過才計入畢業；已過但不認列的學分不算。"""
    STATUS_PASSED = "passed"
    STATUS_FAILED = "failed"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_UNRECOGNIZED = "unrecognized"
    STATUS_CHOICES = [
        (STATUS_PASSED, "已通過"),
        (STATUS_UNRECOGNIZED, "已過但不認列"),
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


class SchoolClass(models.Model):
    """學生可選、課程可開課的班級。全校不是班級，只用於課程。"""
    name = models.CharField("班級名稱", max_length=50, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "班級"
        verbose_name_plural = "班級"

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        self.name = (self.name or "").strip()
        if not self.name:
            raise ValidationError({"name": "請填寫班級名稱。"})
        if self.name == "全校":
            raise ValidationError({"name": "「全校」只用於課程的開課對象，不用另外建班級。"})

    def save(self, *args, **kwargs):
        self.name = (self.name or "").strip()
        super().save(*args, **kwargs)


class StudentProfile(models.Model):
    """學生的學號、班級與主修模組。另一模組學分最多認列到上限。"""
    user_id = models.CharField("使用者 ID", max_length=64, primary_key=True)
    student_number = models.CharField(
        "學號", max_length=12, blank=True, null=True, unique=True
    )
    school_class = models.ForeignKey(
        SchoolClass,
        verbose_name="班級",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="students",
    )
    module = models.CharField("主修模組", max_length=20, blank=True, default="")
    schedule_note = models.TextField("課表提醒", blank=True, default="")
    notify_at_floor = models.BooleanField("已達退選下限時提醒", default=True)
    notify_near_floor = models.BooleanField("接近退選下限時提醒", default=True)
    notify_at_limit = models.BooleanField("已達學分上限時提醒", default=True)
    avatar = models.FileField("頭貼", upload_to=avatar_upload_to, blank=True)

    class Meta:
        verbose_name = "學生資料"
        verbose_name_plural = "學生資料"

    def __init__(self, *args, **kwargs):
        class_name = kwargs.pop("class_name", None)
        super().__init__(*args, **kwargs)
        if class_name is not None:
            self.class_name = class_name

    def _get_class_name(self):
        if self.school_class_id:
            return self.school_class.name
        return ""

    _get_class_name.short_description = "班級"

    def _set_class_name(self, value):
        label = (value or "").strip()
        if not label:
            self.school_class = None
            return
        if self.school_class_id and self.school_class.name == label:
            return
        self.school_class, _created = SchoolClass.objects.get_or_create(name=label)

    class_name = property(_get_class_name, _set_class_name)

    def __str__(self):
        return f"{self.student_number or self.user_id}: {self.class_name or '未填班級'}"

    def save(self, *args, **kwargs):
        number = (self.student_number or "").strip().upper()
        self.student_number = number or None
        super().save(*args, **kwargs)


class ModuleCreditLimit(models.Model):
    """模組學分上下限。0 表示這一端不額外限制，既有選課不會被刪除。"""
    module = models.CharField("模組", max_length=20, primary_key=True)
    min_credits = models.PositiveIntegerField("最低學分", default=0)
    max_credits = models.PositiveIntegerField(
        "最高學分",
        default=0,
        help_text="0 表示不限制上限。",
    )

    class Meta:
        verbose_name = "模組學分限制"
        verbose_name_plural = "模組學分限制"

    def __str__(self):
        upper = "不限" if not self.max_credits else str(self.max_credits)
        return f"{self.module}：{self.min_credits}–{upper}"

    def clean(self):
        super().clean()
        if self.max_credits and self.min_credits > self.max_credits:
            raise ValidationError({"max_credits": "最高學分不可低於最低學分。"})


class UserCreditLimit(models.Model):
    """使用者學分上限與下限"""
    user_id = models.CharField("使用者 ID", max_length=64, primary_key=True)
    credit_limit = models.PositiveIntegerField("學分上限", default=DEFAULT_CREDIT_LIMIT)
    credit_floor = models.PositiveIntegerField("學分下限", default=DEFAULT_CREDIT_FLOOR)

    def __str__(self):
        return f"{self.user_id}: {self.credit_floor}–{self.credit_limit}"
