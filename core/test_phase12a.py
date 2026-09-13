from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.test import (
    RequestFactory,
    TestCase,
)

from django.urls import reverse

from core.context_processors import (
    global_context,
)

from core.forms import (
    StoreSettingsForm,
)

from core.models import (
    StoreSettings,
)

from core.store_settings import (
    business_address,
    get_store_settings,
)

from orders.document_service import (
    _store_snapshot,
)


User = get_user_model()


class Phase12AStoreSettingsTests(
    TestCase
):

    def setUp(self):

        self.staff = (
            User.objects.create_user(
                username="phase12admin",
                password="pass12345",
                email="admin12@example.com",
                role=User.ADMIN,
                is_staff=True,
            )
        )


        self.customer = (
            User.objects.create_user(
                username="phase12customer",
                password="pass12345",
                email="customer12@example.com",
                role=User.CUSTOMER,
            )
        )


    def test_singleton_settings_are_created(
        self,
    ):

        first = get_store_settings()
        second = get_store_settings()


        self.assertEqual(
            first.pk,
            1,
        )


        self.assertEqual(
            first.pk,
            second.pk,
        )


        self.assertEqual(
            StoreSettings.objects.count(),
            1,
        )


    def test_staff_can_view_store_settings(
        self,
    ):

        self.client.login(
            username="phase12admin",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "admin_store_settings"
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            "Store Settings",
        )


    def test_customer_cannot_view_store_settings(
        self,
    ):

        self.client.login(
            username="phase12customer",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "admin_store_settings"
            )
        )


        self.assertIn(
            response.status_code,
            [
                302,
                403,
            ],
        )


    def test_staff_can_update_settings(
        self,
    ):

        self.client.login(
            username="phase12admin",
            password="pass12345",
        )


        response = self.client.post(
            reverse(
                "admin_store_settings"
            ),
            {
                "store_name":
                    "Austine Online Store",

                "legal_name":
                    "Austine Online Store Ltd",

                "support_email":
                    "support@example.com",

                "support_phone":
                    "0712345678",

                "whatsapp_number":
                    "0712345678",

                "website_url":
                    "https://example.com",

                "address":
                    "Moi Avenue",

                "city":
                    "Nairobi",

                "county":
                    "Nairobi",

                "country":
                    "Kenya",

                "currency_code":
                    "kes",

                "currency_symbol":
                    "KSh",

                "tax_rate":
                    "16.00",

                "tax_enabled":
                    "on",

                "orders_enabled":
                    "on",

                "minimum_order_amount":
                    "500.00",

                "document_footer":
                    "Thank you for your order.",
            },
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        store = get_store_settings()


        self.assertEqual(
            store.store_name,
            "Austine Online Store",
        )


        self.assertEqual(
            store.currency_code,
            "KES",
        )


        self.assertEqual(
            store.tax_rate,
            Decimal("16.00"),
        )


        self.assertEqual(
            store.minimum_order_amount,
            Decimal("500.00"),
        )


        self.assertEqual(
            store.updated_by,
            self.staff,
        )


    def test_invalid_tax_rate_rejected(
        self,
    ):

        store = get_store_settings()


        form = StoreSettingsForm(
            {
                "store_name":
                    "Test Store",

                "country":
                    "Kenya",

                "currency_code":
                    "KES",

                "currency_symbol":
                    "KSh",

                "tax_rate":
                    "150",

                "minimum_order_amount":
                    "0",

                "orders_enabled":
                    "on",
            },
            instance=store,
        )


        self.assertFalse(
            form.is_valid()
        )


        self.assertIn(
            "tax_rate",
            form.errors,
        )


    def test_business_address_builder(
        self,
    ):

        store = get_store_settings()

        store.address = "ABC Plaza"
        store.city = "Nairobi"
        store.county = "Nairobi"
        store.country = "Kenya"

        store.save()


        self.assertEqual(
            business_address(
                store
            ),
            (
                "ABC Plaza, Nairobi, "
                "Nairobi, Kenya"
            ),
        )


    def test_document_snapshot_uses_store_settings(
        self,
    ):

        store = get_store_settings()

        store.store_name = (
            "Phase 12 Shop"
        )

        store.support_email = (
            "shop@example.com"
        )

        store.support_phone = (
            "0711000000"
        )

        store.currency_code = "KES"
        store.currency_symbol = "KSh"

        store.save()


        snapshot = _store_snapshot()


        self.assertEqual(
            snapshot["name"],
            "Phase 12 Shop",
        )


        self.assertEqual(
            snapshot["email"],
            "shop@example.com",
        )


        self.assertEqual(
            snapshot["currency_code"],
            "KES",
        )
