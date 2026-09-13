from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group

from .store_roles import STORE_ROLE_NAMES


User = get_user_model()


class StoreStaffCreateForm(UserCreationForm):

    email = forms.EmailField(
        required=True,
    )

    first_name = forms.CharField(
        required=True,
    )

    last_name = forms.CharField(
        required=True,
    )

    role_group = forms.ModelChoiceField(
        queryset=Group.objects.none(),
        label="Staff role",
        empty_label=None,
    )


    class Meta:

        model = User

        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "role_group",
            "password1",
            "password2",
        )


    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["role_group"].queryset = (
            Group.objects
            .filter(
                name__in=STORE_ROLE_NAMES
            )
            .order_by("name")
        )

        for field in self.fields.values():

            if isinstance(
                field.widget,
                forms.CheckboxInput,
            ):
                field.widget.attrs["class"] = (
                    "form-check-input"
                )

            else:
                field.widget.attrs["class"] = (
                    "form-control"
                )


    def clean_email(self):

        email = (
            self.cleaned_data["email"]
            .strip()
            .lower()
        )

        if User.objects.filter(
            email__iexact=email
        ).exists():

            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email


    def save(self, commit=True):

        user = super().save(
            commit=False
        )

        user.is_staff = True
        user.is_active = True

        if hasattr(user, "role"):
            user.role = "admin"

        if commit:

            user.save()

            user.groups.clear()

            role_group = (
                self.cleaned_data[
                    "role_group"
                ]
            )

            user.groups.add(
                role_group
            )

        return user



class StoreStaffUpdateForm(forms.ModelForm):

    role_group = forms.ModelChoiceField(
        queryset=Group.objects.none(),
        label="Staff role",
        empty_label=None,
    )


    class Meta:

        model = User

        fields = (
            "first_name",
            "last_name",
            "email",
            "phone",
            "role_group",
            "is_active",
        )


    def __init__(
        self,
        *args,
        **kwargs,
    ):

        super().__init__(
            *args,
            **kwargs,
        )

        self.fields["role_group"].queryset = (
            Group.objects
            .filter(
                name__in=STORE_ROLE_NAMES
            )
            .order_by("name")
        )

        if self.instance.pk:

            current_group = (
                self.instance.groups
                .filter(
                    name__in=STORE_ROLE_NAMES
                )
                .first()
            )

            if current_group:

                self.fields[
                    "role_group"
                ].initial = current_group


        for field in self.fields.values():

            if isinstance(
                field.widget,
                forms.CheckboxInput,
            ):

                field.widget.attrs[
                    "class"
                ] = "form-check-input"

            else:

                field.widget.attrs[
                    "class"
                ] = "form-control"


    def clean_email(self):

        email = (
            self.cleaned_data["email"]
            .strip()
            .lower()
        )

        qs = User.objects.filter(
            email__iexact=email
        ).exclude(
            pk=self.instance.pk
        )

        if qs.exists():

            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email


    def save(self, commit=True):

        user = super().save(
            commit=False
        )

        user.is_staff = True

        if hasattr(user, "role"):
            user.role = "admin"

        if commit:

            user.save()

            user.groups.remove(
                *Group.objects.filter(
                    name__in=STORE_ROLE_NAMES
                )
            )

            user.groups.add(
                self.cleaned_data[
                    "role_group"
                ]
            )

        return user
