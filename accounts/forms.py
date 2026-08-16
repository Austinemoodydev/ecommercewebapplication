from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import CustomUser, Address


class RegisterForm(UserCreationForm):

    class Meta:

        model = CustomUser

        fields = (
            "username",
            "email",
            "phone",
            "password1",
            "password2",
        )

class AddressForm(forms.ModelForm):

    class Meta:
        model = Address
        fields = [
            "full_name", "phone", "county", "city",
            "estate", "house_number", "landmark", "is_default",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Full name"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "07XXXXXXXX"}),
            "county": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "estate": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Westlands"}),
            "house_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "House / Building number"}),
            "landmark": forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional landmark"}),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

