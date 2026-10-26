"""
Django Admin 設定（搭配 SimpleUI）
"""

from django.contrib import admin
from .models import Course, Enrollment, Favorite, UserCreditLimit


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
    )
    list_filter = ("course_type", "weekday", "target_class")
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


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user_id", "course", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user_id", "course__course_id", "course__name")
    autocomplete_fields = ("course",)
    ordering = ("-created_at",)
    list_per_page = 25


@admin.register(UserCreditLimit)
class UserCreditLimitAdmin(admin.ModelAdmin):
    list_display = ("user_id", "credit_limit")
    search_fields = ("user_id",)
    ordering = ("user_id",)
