"""
Django Admin 設定（搭配 SimpleUI）
"""

from django.contrib import admin

from .data_store import course_store
from .models import (
    Course,
    Enrollment,
    Favorite,
    GraduationRequirement,
    StudentProfile,
    StudyRecord,
    UserCreditLimit,
)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "course_id",
        "name",
        "teacher",
        "course_type",
        "weekday",
        "start_period",
        "end_period",
        "credits",
        "enrolled_count",
        "total_quota",
        "target_class",
        "module",
    )
    list_filter = ("course_type", "module", "weekday", "target_class")
    search_fields = ("course_id", "name", "teacher")
    ordering = ("course_id",)
    list_per_page = 25
    readonly_fields = ("enrolled_count",)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user_id", "course", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user_id", "course__course_id", "course__name")
    autocomplete_fields = ("course",)
    ordering = ("-created_at",)
    list_per_page = 25

    def delete_model(self, request, obj):
        """管理員退選不受學分下限限制，並同步名額。"""
        course_store.drop_course(obj.user_id, obj.course_id, force=True)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            course_store.drop_course(obj.user_id, obj.course_id, force=True)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user_id", "course", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user_id", "course__course_id", "course__name")
    autocomplete_fields = ("course",)
    ordering = ("-created_at",)
    list_per_page = 25


@admin.register(GraduationRequirement)
class GraduationRequirementAdmin(admin.ModelAdmin):
    list_display = (
        "total_credits",
        "required_credits",
        "elective_credits",
        "general_credits",
        "recognition_cap",
    )


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user_id", "module")
    search_fields = ("user_id",)
    list_filter = ("module",)


@admin.register(StudyRecord)
class StudyRecordAdmin(admin.ModelAdmin):
    list_display = (
        "user_id",
        "semester",
        "course_code",
        "course_name",
        "course_type",
        "credits",
        "status",
    )
    list_filter = ("status", "course_type", "semester")
    search_fields = ("user_id", "course_code", "course_name")
    ordering = ("-semester", "course_code")
    list_per_page = 25


@admin.register(UserCreditLimit)
class UserCreditLimitAdmin(admin.ModelAdmin):
    list_display = ("user_id", "credit_floor", "credit_limit")
    search_fields = ("user_id",)
    ordering = ("user_id",)
