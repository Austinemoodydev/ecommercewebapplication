from decimal import Decimal, ROUND_HALF_UP
from django import forms
from django.core.exceptions import ValidationError

from products.models import Product, ProductImage, ProductVariant
from orders.models import Order
from core.upload_security import validate_uploaded_image


RETAIL_PRICE_UNIT = Decimal("1")


def normalize_retail_price(value):
    """
    Store customer-facing retail prices
    using whole Kenyan shillings.

    DecimalField remains decimal_places=2,
    therefore 75000 is stored as 75000.00.
    """

    if value is None:
        return None

    return value.quantize(
        RETAIL_PRICE_UNIT,
        rounding=ROUND_HALF_UP,
    )




class AdminProductForm(forms.ModelForm):

    class Meta:
        model = Product

        fields = [
            "name",
            "sku",
            "category",
            "brand",
            "description",
            "price",
            "cost_price",
            "low_stock_threshold",
            "discount_price",
            "image",
            "featured",
            "is_active",
        ]

        widgets = {

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Product name",
                }
            ),

            "sku": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. HP-840-G6-001",
                }
            ),

            "category": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "brand": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": (
                        "Describe the product..."
                    ),
                }
            ),

            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "1",
                }
            ),

            "discount_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "1",
                    "placeholder": "e.g. 75000",
                }
            ),

            "stock": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                }
            ),

            "image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),

            "featured": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["category"].queryset = (
            self.fields["category"]
            .queryset
            .order_by("name")
        )

        self.fields["brand"].queryset = (
            self.fields["brand"]
            .queryset
            .order_by("name")
        )

        self.fields["brand"].required = False

        # Existing products should not be forced
        # to upload the primary image again.
        if self.instance and self.instance.pk:
            self.fields["image"].required = False


    def __init__(
        self,
        *args,
        **kwargs,
    ):

        super().__init__(
            *args,
            **kwargs,
        )

        self.fields[
            "cost_price"
        ].required = False

        self.fields[
            "cost_price"
        ].widget.attrs.update(
            {
                "class": "form-control",
                "min": "0",
                "step": "0.01",
                "placeholder": (
                    "Business cost per unit"
                ),
            }
        )

        self.fields[
            "low_stock_threshold"
        ].widget.attrs.update(
            {
                "class": "form-control",
                "min": "0",
            }
        )

        self.fields[
            "low_stock_threshold"
        ].help_text = (
            "Inventory warning level. "
            "Stock is considered low when "
            "available quantity is at or "
            "below this number."
        )


    def clean_price(self):

        return normalize_retail_price(
            self.cleaned_data.get(
                "price"
            )
        )


    def clean_discount_price(self):

        return normalize_retail_price(
            self.cleaned_data.get(
                "discount_price"
            )
        )


    def clean_image(self):

        image = self.cleaned_data.get(
            "image"
        )

        if image:

            validate_uploaded_image(
                image,
                max_size_mb=5,
                max_width=6000,
                max_height=6000,
                max_pixels=25_000_000,
            )

        return image


    def clean_sku(self):

        sku = self.cleaned_data["sku"].strip().upper()

        existing = Product.objects.filter(
            sku__iexact=sku
        )

        if self.instance.pk:
            existing = existing.exclude(
                pk=self.instance.pk
            )

        if existing.exists():
            raise ValidationError(
                "Another product already uses this SKU."
            )

        return sku

    def clean(self):

        cleaned_data = super().clean()

        price = cleaned_data.get("price")

        discount_price = cleaned_data.get(
            "discount_price"
        )

        if (
            price is not None
            and discount_price is not None
            and discount_price >= price
        ):
            self.add_error(
                "discount_price",
                (
                    "Sale price must be lower "
                    "than the regular price."
                ),
            )

        return cleaned_data


class AdminOrderShippingForm(forms.ModelForm):
    class Meta:
        model = Order

        fields = [
            "courier",
            "tracking_number",
            "tracking_url",
        ]

        widgets = {
            "courier": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. G4S, Fargo Courier",
                }
            ),

            "tracking_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Tracking number",
                }
            ),

            "tracking_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://...",
                }
            ),
        }

class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):

    def __init__(self, *args, **kwargs):

        kwargs.setdefault(
            "widget",
            MultipleImageInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),
        )

        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):

        single_image_clean = super().clean

        if isinstance(
            data,
            (list, tuple),
        ):
            result = [
                single_image_clean(
                    image,
                    initial,
                )
                for image in data
            ]
        else:
            result = [
                single_image_clean(
                    data,
                    initial,
                )
            ]

        return result


class AdminProductGalleryForm(forms.Form):

    images = MultipleImageField(
        required=True,
        help_text=(
            "You can select multiple images. "
            "Maximum 10 images per upload."
        ),
    )

    def clean_images(self):

        images = self.cleaned_data["images"]

        if len(images) > 10:
            raise ValidationError(
                "Upload a maximum of 10 images at once."
            )

        for image in images:

            validate_uploaded_image(
                image,
                max_size_mb=5,
                max_width=6000,
                max_height=6000,
                max_pixels=25_000_000,
            )

        return images


class AdminProductVariantForm(forms.ModelForm):

    class Meta:

        model = ProductVariant

        fields = [
            "name",
            "sku",
            "price",
            "cost_price",
            "low_stock_threshold",
            "is_active",
        ]

        widgets = {

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "e.g. 16GB RAM / 512GB SSD"
                    ),
                }
            ),

            "sku": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "e.g. HP840-16-512"
                    ),
                }
            ),

            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "1",
                    "placeholder": (
                        "Leave blank to use "
                        "product price"
                    ),
                }
            ),

            "stock": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }


    def __init__(
        self,
        *args,
        **kwargs,
    ):

        super().__init__(
            *args,
            **kwargs,
        )

        self.fields[
            "cost_price"
        ].required = False

        self.fields[
            "cost_price"
        ].widget.attrs.update(
            {
                "class": "form-control",
                "min": "0",
                "step": "0.01",
                "placeholder": (
                    "Variant cost per unit"
                ),
            }
        )

        self.fields[
            "low_stock_threshold"
        ].widget.attrs.update(
            {
                "class": "form-control",
                "min": "0",
            }
        )

    def clean_name(self):

        name = self.cleaned_data["name"].strip()

        if not name:
            raise ValidationError(
                "Variant name is required."
            )

        return name

    def clean_sku(self):

        sku = (
            self.cleaned_data["sku"]
            .strip()
            .upper()
        )

        queryset = (
            ProductVariant.objects
            .filter(
                sku__iexact=sku
            )
        )

        if self.instance.pk:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise ValidationError(
                (
                    "Another product variant "
                    "already uses this SKU."
                )
            )

        return sku

    def clean_price(self):

        price = self.cleaned_data.get(
            "price"
        )

        if (
            price is not None
            and price < 0
        ):
            raise ValidationError(
                "Price cannot be negative."
            )

        return price

    def clean_stock(self):

        stock = self.cleaned_data.get(
            "stock"
        )

        if stock is None:
            return stock

        if (
            self.instance.pk
            and stock
            < self.instance.reserved_stock
        ):
            raise ValidationError(
                (
                    "Stock cannot be lower than "
                    f"the reserved quantity "
                    f"({self.instance.reserved_stock})."
                )
            )

        return stock
