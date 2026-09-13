from decimal import Decimal

from django import forms

from .models import StoreSettings


class StoreSettingsForm(
    forms.ModelForm
):

    class Meta:

        model = StoreSettings

        fields = [
            "store_name",
            "legal_name",
            "business_registration_number",
            "tax_pin",
            "support_email",
            "support_phone",
            "whatsapp_number",
            "website_url",
            "address",
            "city",
            "county",
            "country",
            "currency_code",
            "currency_symbol",
            "tax_enabled",
            "tax_rate",
            "orders_enabled",
            "checkout_closed_message",
            "minimum_order_amount",
            "invoice_prefix",
            "receipt_prefix",
            "credit_note_prefix",
            "document_footer",
        ]

        widgets = {

            "document_footer":
                forms.Textarea(
                    attrs={
                        "rows": 3,
                    }
                ),
        }


    def clean_currency_code(
        self,
    ):

        value = (
            self.cleaned_data[
                "currency_code"
            ]
            .strip()
            .upper()
        )


        if len(value) < 3:

            raise forms.ValidationError(
                "Enter a valid currency code "
                "such as KES, USD or EUR."
            )


        return value


    def clean_tax_rate(
        self,
    ):

        value = (
            self.cleaned_data.get(
                "tax_rate"
            )
        )


        if value is None:

            return Decimal("0.00")


        if (
            value
            < Decimal("0.00")
            or
            value
            > Decimal("100.00")
        ):

            raise forms.ValidationError(
                "Tax rate must be between "
                "0 and 100."
            )


        return value


    def _clean_document_prefix(
        self,
        field_name,
        default,
    ):

        value = (
            self.cleaned_data.get(
                field_name
            )
            or default
        )

        value = (
            value
            .strip()
            .upper()
        )


        # Keep document identifiers URL/file safe.
        cleaned = "".join(
            character
            for character in value
            if (
                character.isalnum()
                or character in {"-", "_"}
            )
        )


        if not cleaned:

            cleaned = default


        if len(cleaned) > 20:

            raise forms.ValidationError(
                "Document prefix cannot exceed "
                "20 characters."
            )


        return cleaned


    def clean_invoice_prefix(
        self,
    ):

        return self._clean_document_prefix(
            "invoice_prefix",
            "INV",
        )


    def clean_receipt_prefix(
        self,
    ):

        return self._clean_document_prefix(
            "receipt_prefix",
            "RCP",
        )


    def clean_credit_note_prefix(
        self,
    ):

        return self._clean_document_prefix(
            "credit_note_prefix",
            "CN",
        )


    def clean(
        self,
    ):

        cleaned_data = super().clean()


        if not getattr(
            self.instance,
            "pk",
            None,
        ):

            return cleaned_data


        new_code = (
            cleaned_data.get(
                "currency_code"
            )
            or self.instance.currency_code
        )

        new_symbol = (
            cleaned_data.get(
                "currency_symbol"
            )
            or self.instance.currency_symbol
        )


        old_code = (
            self.instance.currency_code
            or ""
        )

        old_symbol = (
            self.instance.currency_symbol
            or ""
        )


        currency_changed = (
            new_code != old_code
            or
            new_symbol != old_symbol
        )


        if currency_changed:

            from orders.models import Order


            active_unpaid_orders = (
                Order.objects
                .filter(
                    status__in=[
                        "pending",
                        "confirmed",
                        "processing",
                        "shipped",
                    ],
                    payment_status__in=[
                        "pending",
                        "failed",
                    ],
                )
                .exists()
            )


            if active_unpaid_orders:

                raise forms.ValidationError(
                    (
                        "Currency cannot be changed while "
                        "active unpaid orders exist. "
                        "Complete, cancel, or resolve those "
                        "orders first."
                    )
                )


        return cleaned_data



    def clean_minimum_order_amount(
        self,
    ):

        value = (
            self.cleaned_data.get(
                "minimum_order_amount"
            )
        )


        if (
            value is not None
            and value
            < Decimal("0.00")
        ):

            raise forms.ValidationError(
                "Minimum order amount "
                "cannot be negative."
            )


        return value


# Bootstrap-friendly widgets
for field_name, field in (
    StoreSettingsForm.base_fields.items()
):

    widget = field.widget


    if isinstance(
        widget,
        forms.CheckboxInput,
    ):

        widget.attrs.setdefault(
            "class",
            "form-check-input",
        )

    else:

        widget.attrs.setdefault(
            "class",
            "form-control",
        )

