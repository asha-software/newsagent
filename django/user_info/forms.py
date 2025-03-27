from django import forms
from .models import UserQuery


class UserQueryForm(forms.ModelForm):
    class Meta:
        model = UserQuery
        fields = ["username", "password", "email"]  # Removed 'query' field
        widgets = {
            "password": forms.PasswordInput(),
        }
