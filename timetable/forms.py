"""前台登入、註冊與改密碼表單。"""

from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserCreationForm,
)
from django.core.exceptions import ValidationError

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
