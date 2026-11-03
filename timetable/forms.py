"""前台登入、註冊、個人資料與改密碼表單。"""

import re

from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserCreationForm,
)
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import StudentProfile

STUDENT_NUMBER_PATTERN = re.compile(r"^[A-Z0-9]{5,12}$")

MAX_AVATAR_BYTES = 2 * 1024 * 1024


def avatar_extension(header: bytes) -> str:
    if header.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return ".webp"
    return ""


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "帳號"
        self.fields["password"].label = "密碼"
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class RegisterForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "帳號"
        self.fields["password1"].label = "密碼"
        self.fields["password2"].label = "確認密碼"
        self.fields["password1"].widget.attrs["data-password-rules"] = "register-password-rules"
        for field in self.fields.values():
            field.help_text = ""
            field.widget.attrs["class"] = "form-control"


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "目前密碼"
        self.fields["new_password1"].label = "新密碼"
        self.fields["new_password2"].label = "確認新密碼"
        self.fields["new_password1"].widget.attrs["data-password-rules"] = "settings-password-rules"
        for field in self.fields.values():
            field.help_text = ""
            field.widget.attrs["class"] = "form-control"


def normalize_student_number(value: str) -> str:
    return (value or "").strip().upper()


def validate_student_number(value: str) -> str:
    number = normalize_student_number(value)
    if not STUDENT_NUMBER_PATTERN.fullmatch(number):
        raise ValidationError("學號須為 5 到 12 碼英數。")
    return number


def user_for_profile(user_id: str):
    key = str(user_id or "")
    if not key.isdigit():
        return None
    return User.objects.filter(pk=int(key)).first()


class StudentIdentityForm(forms.Form):
    """學生填寫姓名、學號與班級。學號存檔後不可再改。"""

    name = forms.CharField(
        label="姓名",
        max_length=30,
        error_messages={"required": "請填寫姓名。"},
    )
    student_number = forms.CharField(
        label="學號",
        max_length=12,
        required=False,
        error_messages={"required": "請填寫學號。"},
    )
    class_name = forms.ChoiceField(
        label="班級",
        error_messages={
            "required": "請選擇班級。",
            "invalid_choice": "請選擇班級。",
        },
    )

    def __init__(self, *args, user, profile, class_names, **kwargs):
        self.user = user
        self.profile = profile
        self.number_locked = bool(profile.student_number)
        super().__init__(*args, **kwargs)
        self.fields["class_name"].choices = [("", "請選擇班級")] + [
            (name, name) for name in class_names
        ]
        self.fields["name"].widget.attrs["autocomplete"] = "name"
        if self.number_locked:
            self.fields["student_number"].disabled = True
            self.fields["student_number"].help_text = "學號如需更正，請聯絡管理員。"
        else:
            self.fields["student_number"].required = True
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.initial.setdefault("name", (user.get_full_name() or "").strip())
        self.initial.setdefault("student_number", profile.student_number or "")
        self.initial.setdefault("class_name", profile.class_name)

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise ValidationError("請填寫姓名。")
        return name

    def clean_student_number(self):
        if self.number_locked:
            return self.profile.student_number
        number = validate_student_number(self.cleaned_data.get("student_number"))
        taken = (
            StudentProfile.objects.filter(student_number=number)
            .exclude(user_id=self.profile.user_id)
            .first()
        )
        if taken is not None:
            raise ValidationError("這個學號已經有人使用。")
        return number

    def clean_class_name(self):
        value = (self.cleaned_data.get("class_name") or "").strip()
        allowed = {choice for choice, _label in self.fields["class_name"].choices if choice}
        if value not in allowed:
            raise ValidationError("請選擇班級。")
        return value


class StudentProfileAdminForm(forms.ModelForm):
    """後台可更正學號，並把姓名寫回帳號。"""

    name = forms.CharField(label="姓名", max_length=30, required=False)

    class Meta:
        model = StudentProfile
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .data_store import course_store

        current = ""
        if getattr(self.instance, "class_name", ""):
            current = self.instance.class_name
        names = course_store.class_names(extra=current)
        self.fields["class_name"].widget = forms.Select(
            choices=[("", "尚未填寫")] + [(name, name) for name in names]
        )
        self.fields["student_number"].required = False
        self.fields["student_number"].help_text = "留白代表尚未填寫。學生填過之後只能在這裡更正。"
        user = user_for_profile(getattr(self.instance, "user_id", ""))
        if user is not None and not self.is_bound:
            self.fields["name"].initial = (user.get_full_name() or "").strip()

    def clean_name(self):
        return (self.cleaned_data.get("name") or "").strip()

    def clean_student_number(self):
        raw = self.cleaned_data.get("student_number")
        if not (raw or "").strip():
            return None
        number = validate_student_number(raw)
        taken = StudentProfile.objects.filter(student_number=number)
        if self.instance.pk:
            taken = taken.exclude(pk=self.instance.pk)
        other = taken.first()
        if other is not None:
            owner = user_for_profile(other.user_id)
            who = owner.username if owner else other.user_id
            raise ValidationError(f"這個學號已經由帳號 {who} 使用。")
        return number

    def clean_class_name(self):
        value = (self.cleaned_data.get("class_name") or "").strip()
        if not value:
            return ""
        allowed = {choice for choice, _label in self.fields["class_name"].widget.choices if choice}
        if value not in allowed:
            raise ValidationError("請選擇課程裡已有的開課班級。")
        return value

    def save(self, commit=True):
        profile = super().save(commit=False)
        if not (profile.student_number or "").strip():
            profile.student_number = None
        if commit:
            profile.save()
            self.save_m2m()
        user = user_for_profile(profile.user_id)
        if user is not None:
            user.first_name = self.cleaned_data.get("name") or ""
            user.last_name = ""
            user.save(update_fields=["first_name", "last_name"])
        return profile


class AvatarUploadForm(forms.Form):
    avatar = forms.FileField(label="頭貼")

    def clean_avatar(self):
        uploaded = self.cleaned_data["avatar"]
        if uploaded.size > MAX_AVATAR_BYTES:
            raise ValidationError("圖片不能超過 2MB。")
        header = uploaded.read(16)
        uploaded.seek(0)
        extension = avatar_extension(header)
        if not extension:
            raise ValidationError("只接受 JPG、JPEG、PNG 或 WEBP。")
        uploaded.verified_extension = extension
        return uploaded
