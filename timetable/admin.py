"""
Django Admin 設定（搭配 SimpleUI）
"""

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db.models import Q
from django.forms import ModelForm
from django.http import HttpResponseRedirect

from .data_store import course_store
from .models import (
    Course,
    CourseReview,
    Enrollment,
    Favorite,
    GraduationRequirement,
    ModuleCreditLimit,
    StudentProfile,
    StudyRecord,
    UserCreditLimit,
)


def lookup_user(user_id):
    key = str(user_id or "")
    if not key.isdigit():
        return None
    return User.objects.filter(pk=int(key)).first()


class UserIdentityMixin:
    """在列表顯示帳號、姓名與信箱，而不只是 user_id。"""

    def _cached_user(self, user_id):
        cache = getattr(self, "_user_cache", None)
        if cache is None:
            cache = self._user_cache = {}
        key = str(user_id)
        if key not in cache:
            cache[key] = lookup_user(key)
        return cache[key]

    @admin.display(description="帳號", ordering="user_id")
    def account_name(self, obj):
        user = self._cached_user(obj.user_id)
        return user.username if user else "—"

    @admin.display(description="姓名")
    def account_full_name(self, obj):
        user = self._cached_user(obj.user_id)
        if user is None:
            return "—"
        return user.get_full_name() or "—"

    @admin.display(description="電子郵件")
    def account_email(self, obj):
        user = self._cached_user(obj.user_id)
        return user.email if user and user.email else "—"

    def get_search_results(self, request, queryset, search_term):
        matched, use_distinct = super().get_search_results(request, queryset, search_term)
        term = (search_term or "").strip()
        if not term:
            return matched, use_distinct
        user_ids = [
            str(pk)
            for pk in User.objects.filter(
                Q(username__icontains=term)
                | Q(email__icontains=term)
                | Q(first_name__icontains=term)
                | Q(last_name__icontains=term)
            ).values_list("pk", flat=True)
        ]
        if not user_ids:
            return matched, use_distinct
        return (matched | queryset.filter(user_id__in=user_ids)).distinct(), True


admin.site.unregister(User)


@admin.register(User)
class TimetableUserAdmin(DjangoUserAdmin):
    list_display = (
        "id",
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "date_joined",
    )
    search_fields = ("username", "email", "first_name", "last_name")
    list_filter = ("is_staff", "is_superuser", "is_active")
    ordering = ("username",)
    list_per_page = 25


class CourseAdminForm(ModelForm):
    class Meta:
        model = Course
        fields = "__all__"

    def clean_syllabus(self):
        uploaded = self.cleaned_data.get("syllabus")
        if not isinstance(uploaded, UploadedFile):
            return uploaded
        if not uploaded.name.lower().endswith(".pdf"):
            raise ValidationError("請上傳 PDF 檔。")
        header = uploaded.read(5)
        uploaded.seek(0)
        if header != b"%PDF-":
            raise ValidationError("檔案內容不是 PDF。")
        if uploaded.size > 10 * 1024 * 1024:
            raise ValidationError("PDF 不能超過 10MB。")
        return uploaded


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    form = CourseAdminForm
    list_display = (
        "course_id",
        "name",
        "teacher",
        "course_type",
        "module",
        "weekday",
        "start_period",
        "end_period",
        "credits",
        "enrolled_count",
        "total_quota",
        "target_class",
        "has_syllabus",
    )
    list_filter = ("course_type", "module", "weekday", "target_class")
    search_fields = ("course_id", "name", "teacher", "target_class")
    ordering = ("course_id",)
    list_per_page = 25
    fieldsets = (
        (None, {"fields": ("course_id", "name", "teacher", "course_type", "module", "target_class")}),
        ("時間與學分", {"fields": ("weekday", "start_period", "end_period", "credits")}),
        ("名額", {"fields": ("total_quota", "enrolled_count")}),
        ("課程大綱", {"fields": ("syllabus",)}),
    )

    @admin.display(description="課程大綱", boolean=True)
    def has_syllabus(self, obj):
        return bool(obj.syllabus)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("course_id", "enrolled_count")
        return ("enrolled_count",)


class EnrollmentAdminForm(ModelForm):
    class Meta:
        model = Enrollment
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk:
            return cleaned
        user_id = cleaned.get("user_id")
        course = cleaned.get("course")
        if user_id and course:
            ok, message = course_store.check_enrollment_eligibility(user_id, course.pk)
            if not ok:
                raise ValidationError(message)
        return cleaned


@admin.register(Enrollment)
class EnrollmentAdmin(UserIdentityMixin, admin.ModelAdmin):
    form = EnrollmentAdminForm
    list_display = (
        "user_id",
        "account_name",
        "account_full_name",
        "account_email",
        "course",
        "created_at",
    )
    list_filter = ("created_at", "course__course_type", "course__module")
    search_fields = ("user_id", "course__course_id", "course__name", "course__teacher")
    autocomplete_fields = ("course",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 25

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("user_id", "course", "created_at")
        return ("created_at",)

    def save_model(self, request, obj, form, change):
        if change:
            return
        ok, message = course_store.enroll_course(obj.user_id, obj.course_id)
        self._enroll_ok = ok
        self._enroll_message = message
        if not ok:
            return
        saved = Enrollment.objects.get(user_id=obj.user_id, course_id=obj.course_id)
        obj.pk = saved.pk
        obj._state.adding = False
        obj._state.db = saved._state.db

    def log_addition(self, request, obj, message):
        if not getattr(obj, "pk", None):
            return
        return super().log_addition(request, obj, message)

    def response_add(self, request, obj, post_url_continue=None):
        if not getattr(self, "_enroll_ok", True):
            self.message_user(request, self._enroll_message, messages.ERROR)
            return HttpResponseRedirect(request.get_full_path())
        return super().response_add(request, obj, post_url_continue)

    def delete_model(self, request, obj):
        """管理員退選不受學分下限限制，並同步名額。"""
        course_store.drop_course(obj.user_id, obj.course_id, force=True)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            course_store.drop_course(obj.user_id, obj.course_id, force=True)


@admin.register(Favorite)
class FavoriteAdmin(UserIdentityMixin, admin.ModelAdmin):
    list_display = (
        "user_id",
        "account_name",
        "account_full_name",
        "account_email",
        "course",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("user_id", "course__course_id", "course__name")
    autocomplete_fields = ("course",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 25
    readonly_fields = ("created_at",)


@admin.register(GraduationRequirement)
class GraduationRequirementAdmin(admin.ModelAdmin):
    list_display = (
        "total_credits",
        "required_credits",
        "elective_credits",
        "general_credits",
        "recognition_cap",
    )
    list_per_page = 25


@admin.register(ModuleCreditLimit)
class ModuleCreditLimitAdmin(admin.ModelAdmin):
    list_display = ("module", "min_credits", "max_credits")
    ordering = ("module",)
    list_per_page = 25


@admin.register(CourseReview)
class CourseReviewAdmin(UserIdentityMixin, admin.ModelAdmin):
    list_display = (
        "user_id",
        "account_name",
        "account_full_name",
        "course",
        "homework",
        "exam",
        "updated_at",
    )
    list_filter = ("homework", "exam")
    search_fields = ("user_id", "course__course_id", "course__name")
    autocomplete_fields = ("course",)
    date_hierarchy = "updated_at"
    ordering = ("-updated_at",)
    list_per_page = 25
    list_select_related = ("course",)
    readonly_fields = ("updated_at",)


@admin.register(StudentProfile)
class StudentProfileAdmin(UserIdentityMixin, admin.ModelAdmin):
    list_display = (
        "user_id",
        "account_name",
        "account_full_name",
        "account_email",
        "module",
        "has_avatar",
    )
    search_fields = ("user_id", "module")
    list_filter = ("module",)
    list_per_page = 25
    readonly_fields = ("user_id",)

    @admin.display(description="頭貼", boolean=True)
    def has_avatar(self, obj):
        return bool(obj.avatar)


@admin.register(StudyRecord)
class StudyRecordAdmin(UserIdentityMixin, admin.ModelAdmin):
    list_display = (
        "user_id",
        "account_name",
        "account_full_name",
        "semester",
        "course_code",
        "course_name",
        "course_type",
        "credits",
        "status",
    )
    list_display_links = ("course_code",)
    list_editable = ("status",)
    list_filter = ("status", "course_type", "semester", "module")
    search_fields = ("user_id", "course_code", "course_name")
    autocomplete_fields = ("course",)
    ordering = ("-semester", "course_code")
    list_per_page = 25
    list_select_related = ("course",)
    readonly_fields = ("created_at",)
    actions = ("mark_passed", "mark_failed", "mark_in_progress")

    def save_model(self, request, obj, form, change):
        course = obj.course
        if course is not None:
            obj.course_code = obj.course_code or course.course_id
            obj.course_name = obj.course_name or course.name
            obj.course_type = obj.course_type or course.course_type
            obj.module = obj.module or course.module
            if not obj.credits:
                obj.credits = course.credits
        super().save_model(request, obj, form, change)

    def _set_status(self, request, queryset, status, label):
        count = queryset.update(status=status)
        self.message_user(request, f"已將 {count} 筆修課紀錄改為{label}。")

    # 不用 @admin.action：Django 6 會在函式上放無法序列化的 locations，
    # SimpleUI 把動作屬性轉成 JSON 時，整個列表頁會壞掉。
    def mark_passed(self, request, queryset):
        self._set_status(request, queryset, StudyRecord.STATUS_PASSED, "已通過")

    def mark_failed(self, request, queryset):
        self._set_status(request, queryset, StudyRecord.STATUS_FAILED, "未通過")

    def mark_in_progress(self, request, queryset):
        self._set_status(request, queryset, StudyRecord.STATUS_IN_PROGRESS, "正在修")

    mark_passed.short_description = "標為已通過"
    mark_failed.short_description = "標為未通過"
    mark_in_progress.short_description = "標為正在修"


@admin.register(UserCreditLimit)
class UserCreditLimitAdmin(UserIdentityMixin, admin.ModelAdmin):
    list_display = (
        "user_id",
        "account_name",
        "account_full_name",
        "account_email",
        "credit_floor",
        "credit_limit",
    )
    search_fields = ("user_id",)
    ordering = ("user_id",)
    list_per_page = 25
    readonly_fields = ("user_id",)
