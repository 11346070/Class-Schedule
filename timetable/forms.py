"""前台登入、註冊與改密碼表單。"""

from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserCreationForm,
)


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
