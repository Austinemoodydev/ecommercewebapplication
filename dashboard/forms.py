from decimal import Decimal, ROUND_HALF_UP
from django import forms
from django.core.exceptions import ValidationError

from products.models import (
    Product,
    ProductImage,
    ProductOption,
    ProductOptionValue,
    ProductVariant,
)
from orders.models import Order
from core.upload_security import validate_uploaded_image


RETAIL_PRICE_UNIT = Decimal("1")


class AdminProductOptionForm(forms.Form):
    name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. Size, Storage or Material",
        }),
    )
    values = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "e.g. Small, Medium, Large",
        }),
        help_text="Separate values with commas.",
    )

    def clean_values(self):
        values = [value.strip() for value in self.cleaned_data["values"].split(",")]
        values = list(dict.fromkeys(value for value in values if value))
        if not values:
            raise ValidationError("Enter at least one option value.")
        return values


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
            "stock",
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
                    "placeholder": "Leave blank to generate automatically",
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

    def __init__(
        self,
        *args,
        **kwargs,
    ):

        super().__init__(
            *args,
            **kwargs,
        )
        self.fields["category"].queryset = self.fields["category"].queryset.order_by("name")
        self.fields["brand"].queryset = self.fields["brand"].queryset.order_by("name")
        self.fields["brand"].required = False
        self.fields["sku"].required = False
        self.fields["sku"].help_text = "Leave blank for CATEGORY-BRAND-NUMBER, for example ELE-SAM-0001. You may enter a unique SKU manually."
        if self.instance and self.instance.pk:
            self.fields["image"].required = False

        self.fields["image"].help_text = (
            "Required for new products. Upload JPG, PNG or WebP up to 5 MB."
            if not (self.instance and self.instance.pk)
            else "Upload a new image only when replacing the current one."
        )
        self.fields["image"].label = "Primary image"

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

        sku = self.cleaned_data.get("sku", "").strip().upper()

        if not sku:
            return ""

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

    option_values = forms.ModelMultipleChoiceField(
        queryset=ProductOptionValue.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Choose exactly one value from each option used by this product.",
    )

    class Meta:

        model = ProductVariant

        fields = [
            "name",
            "colour",
            "colour_code",
            "image",
            "option_values",
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

            "colour": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Navy Blue",
                }
            ),

            "colour_code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "type": "color",
                }
            ),

            "image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),

            "sku": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Leave blank to generate automatically"
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
        product=None,
        **kwargs,
    ):

        super().__init__(
            *args,
            **kwargs,
        )

        product = product or getattr(self.instance, "product", None)
        self.product = product
        self.fields["sku"].required = False
        self.fields["sku"].help_text = "Leave blank to generate from the product SKU. Manual unique values are also allowed."
        if product and getattr(product, "pk", None):
            self.fields["option_values"].queryset = (
                ProductOptionValue.objects
                .filter(option__product=product)
                .select_related("option")
                .order_by("option__position", "position", "id")
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

    def clean_colour_code(self):
        colour_code = self.cleaned_data.get("colour_code", "").strip()
        if colour_code and (
            len(colour_code) != 7
            or not colour_code.startswith("#")
            or any(character not in "0123456789abcdefABCDEF" for character in colour_code[1:])
        ):
            raise ValidationError("Enter a valid colour in #RRGGBB format.")
        return colour_code

    def clean_option_values(self):
        values = self.cleaned_data.get("option_values")
        option_ids = [value.option_id for value in values]
        if len(option_ids) != len(set(option_ids)):
            raise ValidationError("Choose only one value from each product option.")
        required_option_ids = set()
        if self.product and getattr(self.product, "pk", None):
            required_option_ids = set(
                self.product.options.values_list("id", flat=True)
            )
        if required_option_ids and set(option_ids) != required_option_ids:
            raise ValidationError("Choose one value from every configured product option.")
        return values

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and hasattr(image, "content_type"):
            validate_uploaded_image(
                image,
                max_size_mb=5,
                max_width=6000,
                max_height=6000,
                max_pixels=25_000_000,
            )
        return image

    def clean_sku(self):

        sku = (
            self.cleaned_data.get("sku", "")
            .strip()
            .upper()
        )

        if not sku:
            return ""

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
