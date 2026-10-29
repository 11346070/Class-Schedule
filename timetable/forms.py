"""前台登入與註冊表單。"""

from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


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
        for field in self.fields.values():
            field.help_text = ""
            field.widget.attrs["class"] = "form-control"
