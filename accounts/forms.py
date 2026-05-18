from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class ApplicantRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, label="Name")
    last_name = forms.CharField(max_length=150, label="Surname")

    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = f"{user.first_name} {user.last_name}"
        user.role = "applicant"
        if commit:
            user.save()
        return user