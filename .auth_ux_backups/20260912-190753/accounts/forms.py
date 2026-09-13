from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import CustomUser, Address


class RegisterForm(UserCreationForm):

    email = forms.EmailField(required=True)

    class Meta:

        model = CustomUser

        fields = (
            "username",
            "email",
            "phone",
            "password1",
            "password2",
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if CustomUser.objects.filter(
            email__iexact=email
        ).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email

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


class ProfileForm(forms.ModelForm):

    class Meta:
        model = CustomUser
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone",
            "avatar",
            "email_notifications",
            "sms_notifications",
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        queryset = CustomUser.objects.filter(
            email__iexact=email
        )

        if self.instance and self.instance.pk:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email

