"""
Django Admin 設定（搭配 SimpleUI）
"""

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db.models import Q
from django import forms
from django.http import HttpResponseRedirect

from .data_store import course_store
from .forms import StudentProfileAdminForm
from .models import (
    Course,
    CourseMeeting,
    CourseReview,
    Enrollment,
    Favorite,
    GraduationRequirement,
    ModuleCreditLimit,
    Classroom,
    SchoolClass,
    Semester,
    StudentProfile,
    Teacher,
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
        """只在這一次請求裡暫存。後台物件會一直重複使用，不能留到下一頁。"""
        cache = getattr(self, "_user_cache", None)
        if cache is None:
            cache = self._user_cache = {}
        key = str(user_id)
        if key not in cache:
            cache[key] = lookup_user(key)
        return cache[key]

    def changelist_view(self, request, extra_context=None):
        self._user_cache = {}
        return super().changelist_view(request, extra_context)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        self._user_cache = {}
        return super().changeform_view(request, object_id, form_url, extra_context)

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


class CourseAdminForm(forms.ModelForm):
    teacher = forms.ChoiceField(label="授課教師", required=False)
    new_teacher = forms.CharField(
        label="新增教師",
        max_length=50,
        required=False,
        help_text="下拉選單沒有這位老師時，直接輸入姓名。儲存這門課後就會建立。",
    )
    classroom = forms.ChoiceField(label="教室", required=False)
    new_classroom = forms.CharField(
        label="新增教室",
        max_length=50,
        required=False,
        help_text="下拉選單沒有這間教室時，直接輸入名稱。可以留空。",
    )
    target_class = forms.ChoiceField(label="開課班級", required=False)
    new_class = forms.CharField(
        label="新增班級",
        max_length=50,
        required=False,
        help_text="下拉選單沒有這個班級時，直接輸入名稱。儲存這門課後就會建立，學生的班級選單也會出現。",
    )

    class Meta:
        model = Course
        exclude = ("school_class", "opens_to_all")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        course_store.ensure_seeded()
        modules = [("", "不屬於模組")]
        for rule in course_store.module_rules():
            modules.append((rule.module, rule.module))
        self.fields["module"].widget = forms.Select(choices=modules)
        self.fields["module"].help_text = "選項來自「模組學分限制」。新模組請先到那裡新增。"

        teacher_names = [("", "請選擇授課教師")]
        for name in Teacher.objects.order_by("name").values_list("name", flat=True):
            teacher_names.append((name, name))
        current_teacher = self.instance.teacher.name if self.instance.teacher_id else ""
        if current_teacher and current_teacher not in {value for value, _label in teacher_names}:
            teacher_names.append((current_teacher, current_teacher))
        self.fields["teacher"].choices = teacher_names
        self.fields["teacher"].help_text = "從清單選擇，或在下面的「新增教師」直接輸入。"
        if not self.is_bound:
            self.initial["teacher"] = current_teacher

        room_names = [("", "尚未安排教室")]
        for name in Classroom.objects.order_by("name").values_list("name", flat=True):
            room_names.append((name, name))
        current_room = self.instance.classroom.name if self.instance.classroom_id else ""
        if current_room and current_room not in {value for value, _label in room_names}:
            room_names.append((current_room, current_room))
        self.fields["classroom"].choices = room_names
        if not self.is_bound:
            self.initial["classroom"] = current_room

        class_names = [("", "請選擇開課班級")]
        for name in course_store.class_names():
            class_names.append((name, name))
        class_names.append(("全校", "全校"))
        current = (getattr(self.instance, "target_class", "") or "").strip()
        if current and current not in {value for value, _label in class_names}:
            class_names.append((current, current))
        self.fields["target_class"].choices = class_names
        self.fields["target_class"].required = False
        self.fields["target_class"].help_text = (
            "從清單選擇，或在下面的「新增班級」直接輸入。全校代表每個已填班級的學生都會遇到這門必修。"
        )
        if not self.is_bound:
            self.initial["target_class"] = current

    def clean_module(self):
        value = (self.cleaned_data.get("module") or "").strip()
        allowed = {choice for choice, _label in self.fields["module"].widget.choices}
        if value not in allowed:
            raise ValidationError("請選擇已建立的模組，或留「不屬於模組」。")
        return value

    def clean_teacher(self):
        value = (self.cleaned_data.get("teacher") or "").strip()
        if (self.data.get("new_teacher") or "").strip():
            return value
        allowed = {choice for choice, _label in self.fields["teacher"].choices if choice}
        if value not in allowed:
            raise ValidationError("請選擇已建立的教師，或在新增教師填姓名。")
        return value

    def clean_classroom(self):
        value = (self.cleaned_data.get("classroom") or "").strip()
        if (self.data.get("new_classroom") or "").strip() or not value:
            return value
        allowed = {choice for choice, _label in self.fields["classroom"].choices if choice}
        if value not in allowed:
            raise ValidationError("請選擇已建立的教室，或在新增教室填名稱。")
        return value

    def clean_target_class(self):
        value = (self.cleaned_data.get("target_class") or "").strip()
        if (self.data.get("new_class") or "").strip():
            return value
        allowed = {choice for choice, _label in self.fields["target_class"].choices if choice}
        if value not in allowed:
            raise ValidationError("請選擇已建立的班級，或在新增班級填名稱。")
        return value

    def _assign_target_class(self, label):
        if label == "全校":
            self.instance.opens_to_all = True
            self.instance.school_class = None
            return
        self.instance.opens_to_all = False
        self.instance.school_class, _created = SchoolClass.objects.get_or_create(name=label)

    def _assign_classroom(self, label):
        if not label:
            self.instance.classroom = None
            return None
        self.instance.classroom, _created = Classroom.objects.get_or_create(name=label)
        return self.instance.classroom

    def _assign_teacher(self, label):
        self.instance.teacher, _created = Teacher.objects.get_or_create(name=label)
        return self.instance.teacher

    def clean(self):
        cleaned = super().clean()
        new_teacher = (cleaned.get("new_teacher") or "").strip()
        raw_teacher = cleaned.get("teacher") or ""
        if isinstance(raw_teacher, Teacher):
            raw_teacher = raw_teacher.name
        teacher_name = new_teacher or str(raw_teacher).strip()
        if not teacher_name:
            if "teacher" not in self.errors:
                self.add_error("teacher", "請選擇已建立的教師，或在新增教師填姓名。")
        else:
            cleaned["teacher"] = self._assign_teacher(teacher_name)
        new_room = (cleaned.get("new_classroom") or "").strip()
        raw_room = cleaned.get("classroom") or ""
        if isinstance(raw_room, Classroom):
            raw_room = raw_room.name
        room_name = new_room or str(raw_room).strip()
        if "classroom" not in self.errors:
            cleaned["classroom"] = self._assign_classroom(room_name)
        new_name = (cleaned.get("new_class") or "").strip()
        if not new_name:
            label = (cleaned.get("target_class") or "").strip()
            if not label:
                self.add_error("target_class", "請選擇已建立的班級，或在新增班級填名稱。")
                return cleaned
            self._assign_target_class(label)
            return cleaned
        if new_name == "全校":
            self.add_error("new_class", "「全校」不用另外建立，直接在開課班級選擇全校。")
            return cleaned
        self._assign_target_class(new_name)
        cleaned["target_class"] = new_name
        return cleaned

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


class CourseMeetingInline(admin.TabularInline):
    model = CourseMeeting
    extra = 0
    fields = ("weekday", "start_period", "end_period", "classroom")
    verbose_name = "其他上課時段"
    verbose_name_plural = "其他上課時段"


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    form = CourseAdminForm
    inlines = (CourseMeetingInline,)
    list_display = (
        "course_id",
        "name",
        "semester",
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
        "classroom",
        "has_syllabus",
    )
    list_filter = ("semester", "course_type", "module", "weekday", "school_class", "opens_to_all")
    search_fields = ("course_id", "name", "teacher__name", "school_class__name")
    list_select_related = ("school_class", "teacher", "classroom", "semester")
    ordering = ("course_id",)
    list_per_page = 25
    fieldsets = (
        (None, {"fields": ("course_id", "name", "semester", "teacher", "new_teacher", "classroom", "new_classroom", "course_type", "module", "target_class", "new_class")}),
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

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        if not obj.teacher_id:
            return
        overlaps = []
        others = (
            Course.objects.filter(teacher_id=obj.teacher_id)
            .exclude(pk=obj.pk)
            .prefetch_related("extra_meetings")
        )
        for other in others:
            if obj.overlaps_course(other):
                overlaps.append(f"{other.course_id} {other.name}")
        if overlaps:
            self.message_user(
                request,
                "這位老師在同一時段還有其他課程：" + "、".join(overlaps) + "。",
                messages.WARNING,
            )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if (obj.course_type or "").strip() != "必修":
            return
        if not obj.opens_to_all and not obj.school_class_id:
            return
        user_ids = [
            profile.user_id
            for profile in StudentProfile.objects.exclude(school_class__isnull=True)
            if obj.opens_to_all or profile.school_class_id == obj.school_class_id
        ]
        added_students = 0
        displaced = []
        conflicts = []
        for user_id in user_ids:
            result = course_store.assign_required_courses(user_id)
            if result:
                added_students += 1
            displaced.extend(result.displaced)
            conflicts.extend(result.conflicts)
        if added_students:
            message = f"已把必修加入 {added_students} 位學生的課表，學生不能自行退選。"
            if displaced:
                message += "衝堂的課程已退選：" + "、".join(dict.fromkeys(displaced)) + "。"
            self.message_user(request, message)
        if conflicts:
            self.message_user(
                request,
                "這門必修與其他必修時間重疊，兩門都會留在課表，請調整上課時間。",
                messages.WARNING,
            )


class EnrollmentAdminForm(forms.ModelForm):
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
        "required_lock_label",
        "created_at",
    )
    list_filter = ("created_at", "course__course_type", "course__module")
    list_select_related = ("course",)
    search_fields = ("user_id", "course__course_id", "course__name", "course__teacher__name")
    autocomplete_fields = ("course",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 25

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("user_id", "course", "created_at")
        return ("created_at",)

    @admin.display(description="退選")
    def required_lock_label(self, obj):
        if course_store.is_required_locked(obj.user_id, obj.course):
            return "學生不可退選"
        return "—"

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


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_current")
    search_fields = ("code", "name")
    ordering = ("-is_current", "code")
    list_per_page = 25

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["code"].help_text = "例如 114-1。可以修改代碼，已開課程會跟著這個學期。"
        form.base_fields["is_current"].help_text = "學生的課表和選課清單只顯示目前學期。同一時間只保留一個。"
        return form


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)
    list_per_page = 25

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["name"].help_text = (
            "可以修改名稱。已經指定這間教室的課程會顯示新名稱。有課程使用時不能刪除。"
        )
        return form


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)
    list_per_page = 25

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["name"].help_text = (
            "可以修改姓名。已經指定這位老師的課程會顯示新姓名。有課程使用時不能刪除。"
        )
        return form


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)
    list_per_page = 25

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["name"].help_text = (
            "可以修改名稱。已經指定這個班級的課程和學生會顯示新名稱。"
            "有課程或學生使用時不能刪除。不用建立「全校」。"
        )
        return form


@admin.register(ModuleCreditLimit)
class ModuleCreditLimitAdmin(admin.ModelAdmin):
    list_display = ("module", "min_credits", "max_credits")
    ordering = ("module",)
    list_per_page = 25

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["module"].help_text = "輸入新名稱就會新增這個模組，學生選單會跟著出現。"
        return form


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
    form = StudentProfileAdminForm
    list_display = (
        "user_id",
        "account_name",
        "account_full_name",
        "account_email",
        "student_number_display",
        "class_name_display",
        "module",
        "has_avatar",
    )
    search_fields = ("user_id", "module", "student_number", "school_class__name")
    list_filter = ("school_class", "module")
    list_select_related = ("school_class",)
    list_per_page = 25
    readonly_fields = ("user_id",)
    fields = ("user_id", "name", "student_number", "class_name", "module", "avatar")

    @admin.display(description="學號", ordering="student_number")
    def student_number_display(self, obj):
        return obj.student_number or "—"

    @admin.display(description="班級", ordering="school_class__name")
    def class_name_display(self, obj):
        return obj.class_name or "—"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not obj.class_name:
            return
        result = course_store.assign_required_courses(obj.user_id)
        if result:
            message = "已把必修課程加入這位學生的課表。學生不能自行退選。"
            if result.displaced:
                message += "衝堂的課程已退選：" + "、".join(result.displaced) + "。"
            self.message_user(request, message)
        if result.conflicts:
            self.message_user(
                request,
                "必修之間時間重疊，兩門都會留在課表，請調整上課時間。",
                messages.WARNING,
            )

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
    actions = ("mark_passed", "mark_unrecognized", "mark_failed", "mark_in_progress")

    def get_queryset(self, request):
        course_store.sync_enrollment_study_records()
        return super().get_queryset(request)

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

    def mark_unrecognized(self, request, queryset):
        self._set_status(request, queryset, StudyRecord.STATUS_UNRECOGNIZED, "已過但不認列")

    def mark_failed(self, request, queryset):
        self._set_status(request, queryset, StudyRecord.STATUS_FAILED, "未通過")

    def mark_in_progress(self, request, queryset):
        self._set_status(request, queryset, StudyRecord.STATUS_IN_PROGRESS, "正在修")

    mark_passed.short_description = "標為已通過"
    mark_unrecognized.short_description = "標為已過但不認列"
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
