from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase

from core.forms import StoreSettingsForm

from core.store_settings import (
    get_store_settings,
)

from orders.document_service import (
    _document_number,
)

from orders.credit_note_service import (
    _credit_note_number,
)

from orders.models import Order

from payments.models import RefundRequest


User = get_user_model()


class Phase12CSettingsTests(
    TestCase
):

    def setUp(self):

        self.user = (
            User.objects.create_user(
                username="phase12c",
                password="pass12345",
            )
        )


        self.store = (
            get_store_settings()
        )


    def test_safe_defaults_do_not_block_store(
        self,
    ):

        self.assertTrue(
            self.store.orders_enabled
        )

        self.assertEqual(
            self.store.minimum_order_amount,
            Decimal("0.00"),
        )

        self.assertFalse(
            self.store.tax_enabled
        )

        self.assertEqual(
            self.store.invoice_prefix,
            "INV",
        )

        self.assertEqual(
            self.store.receipt_prefix,
            "RCP",
        )

        self.assertEqual(
            self.store.credit_note_prefix,
            "CN",
        )


    def test_optional_business_identifiers_can_be_blank(
        self,
    ):

        self.assertEqual(
            self.store.tax_pin,
            "",
        )

        self.assertEqual(
            self.store.business_registration_number,
            "",
        )


    def test_prefixes_are_normalised(
        self,
    ):

        form = StoreSettingsForm(
            {
                "store_name":
                    "Test Shop",

                "country":
                    "Kenya",

                "currency_code":
                    "KES",

                "currency_symbol":
                    "KSh",

                "tax_rate":
                    "0",

                "minimum_order_amount":
                    "0",

                "orders_enabled":
                    "on",

                "invoice_prefix":
                    " inv ",

                "receipt_prefix":
                    " receipt ",

                "credit_note_prefix":
                    " cn ",

                "document_footer":
                    "",
            },
            instance=self.store,
        )


        self.assertTrue(
            form.is_valid(),
            form.errors,
        )


        self.assertEqual(
            form.cleaned_data[
                "invoice_prefix"
            ],
            "INV",
        )

        self.assertEqual(
            form.cleaned_data[
                "receipt_prefix"
            ],
            "RECEIPT",
        )


    def test_invalid_prefix_characters_are_removed(
        self,
    ):

        form = StoreSettingsForm(
            {
                "store_name":
                    "Test Shop",

                "country":
                    "Kenya",

                "currency_code":
                    "KES",

                "currency_symbol":
                    "KSh",

                "tax_rate":
                    "0",

                "minimum_order_amount":
                    "0",

                "orders_enabled":
                    "on",

                "invoice_prefix":
                    " INV / 2026 ",

                "receipt_prefix":
                    "RCP",

                "credit_note_prefix":
                    "CN",

                "document_footer":
                    "",
            },
            instance=self.store,
        )


        self.assertTrue(
            form.is_valid(),
            form.errors,
        )


        self.assertEqual(
            form.cleaned_data[
                "invoice_prefix"
            ],
            "INV2026",
        )


    def test_invoice_number_uses_configured_prefix(
        self,
    ):

        self.store.invoice_prefix = (
            "TAXINV"
        )

        self.store.save()


        order = Order(
            order_number="ORD-12001"
        )


        self.assertEqual(
            _document_number(
                order,
                "invoice",
            ),
            "TAXINV-ORD-12001",
        )


    def test_receipt_number_uses_configured_prefix(
        self,
    ):

        self.store.receipt_prefix = (
            "PAY"
        )

        self.store.save()


        order = Order(
            order_number="ORD-12002"
        )


        self.assertEqual(
            _document_number(
                order,
                "receipt",
            ),
            "PAY-ORD-12002",
        )


    def test_credit_note_number_uses_configured_prefix(
        self,
    ):

        self.store.credit_note_prefix = (
            "CRN"
        )

        self.store.save()


        order = Order.objects.create(
            user=self.user,
            order_number="ORD-12003",
            full_name="Customer",
            phone="0712345678",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("1000.00"),
            total_amount=Decimal("1000.00"),
        )


        refund = RefundRequest.objects.create(
            order=order,
            amount=Decimal("100.00"),
            reason="Test",
        )


        self.assertEqual(
            _credit_note_number(
                refund
            ),
            (
                f"CRN-ORD-12003-"
                f"{refund.pk:02d}"
            ),
        )


    def test_blank_checkout_message_is_allowed(
        self,
    ):

        self.store.checkout_closed_message = ""

        self.store.save()

        self.store.refresh_from_db()


        self.assertEqual(
            self.store.checkout_closed_message,
            "",
        )
