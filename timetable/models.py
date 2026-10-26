"""
課程與選課相關資料模型（SQLite）
"""

from django.db import models

DEFAULT_CREDIT_LIMIT = 25

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


class UserCreditLimit(models.Model):
    """使用者學分上限"""
    user_id = models.CharField("使用者 ID", max_length=64, primary_key=True)
    credit_limit = models.PositiveIntegerField("學分上限", default=DEFAULT_CREDIT_LIMIT)

    def __str__(self):
        return f"{self.user_id}: {self.credit_limit}"
