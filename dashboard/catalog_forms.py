from django import forms
from django.core.exceptions import ValidationError

from categories.models import Category
from products.models import Brand


class AdminCategoryForm(forms.ModelForm):

    class Meta:

        model = Category

        fields = [
            "name",
            "description",
            "image",
            "is_active",
        ]

        widgets = {

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "e.g. Laptops"
                    ),
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": (
                        "Category description..."
                    ),
                }
            ),

            "image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def clean_name(self):

        name = (
            self.cleaned_data["name"]
            .strip()
        )

        queryset = (
            Category.objects
            .filter(
                name__iexact=name
            )
        )

        if self.instance.pk:

            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():

            raise ValidationError(
                (
                    "A category with this "
                    "name already exists."
                )
            )

        return name


class AdminBrandForm(forms.ModelForm):

    class Meta:

        model = Brand

        fields = [
            "name",
            "logo",
            "is_active",
        ]

        widgets = {

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "e.g. HP"
                    ),
                }
            ),

            "logo": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def clean_name(self):

        name = (
            self.cleaned_data["name"]
            .strip()
        )

        queryset = (
            Brand.objects
            .filter(
                name__iexact=name
            )
        )

        if self.instance.pk:

            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():

            raise ValidationError(
                (
                    "A brand with this "
                    "name already exists."
                )
            )

        return name
