from accounts.store_roles import STORE_OWNER
from django.contrib.auth.models import Group
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import (
    get_user_model,
)

from django.forms.models import (
    model_to_dict,
)

from django.test import (
    RequestFactory,
    TestCase,
)

from django.urls import reverse

from core.forms import (
    StoreSettingsForm,
)

from core.store_settings import (
    get_store_settings,
)

from dashboard.reports_views import (
    build_sales_report,
)

from orders.credit_note_views import (
    _customer_credit_note_url,
)

from orders.document_views import (
    customer_document_view_url,
)

from orders.models import (
    CreditNoteDocument,
    Order,
    OrderDocument,
)

from payments.models import (
    RefundRequest,
)


User = get_user_model()


class Phase12DFinancialReportTests(
    TestCase
):

    def setUp(self):

        self.user = (
            User.objects.create_user(
                username="phase12d-customer",
                password="pass12345",
                email="customer@example.com",
            )
        )


        self.staff = (
            User.objects.create_user(
                username="phase12d-admin",
                password="pass12345",
                email="admin@example.com",
                is_staff=True,
            )
        )

        store_owner_group, _ = Group.objects.get_or_create(
            name=STORE_OWNER,
        )

        self.staff.groups.add(
            store_owner_group
        )


        self.factory = (
            RequestFactory()
        )


    def create_paid_order(
        self,
        *,
        number,
        subtotal,
        discount,
        tax,
        delivery,
        total,
        code="KES",
        symbol="KSh",
        tax_rate="16.00",
    ):

        return Order.objects.create(
            user=self.user,
            order_number=number,
            full_name="Phase 12D Customer",
            phone="0712345678",
            email="customer@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal(
                subtotal
            ),
            discount=Decimal(
                discount
            ),
            tax_enabled_at_checkout=(
                Decimal(tax) > 0
            ),
            tax_rate_at_checkout=Decimal(
                tax_rate
            ),
            tax_amount=Decimal(
                tax
            ),
            shipping_cost=Decimal(
                delivery
            ),
            total_amount=Decimal(
                total
            ),
            currency_code_at_checkout=code,
            currency_symbol_at_checkout=symbol,
            payment_status="paid",
            status="confirmed",
        )


    def test_report_uses_historical_tax_snapshot(
        self,
    ):

        self.create_paid_order(
            number="P12D-001",
            subtotal="1000.00",
            discount="100.00",
            tax="144.00",
            delivery="200.00",
            total="1244.00",
        )


        request = (
            self.factory.get(
                "/dashboard/admin/reports/"
            )
        )


        report = build_sales_report(
            request
        )


        self.assertEqual(
            report[
                "merchandise_subtotal"
            ],
            Decimal("1000.00"),
        )


        self.assertEqual(
            report[
                "discounts_given"
            ],
            Decimal("100.00"),
        )


        self.assertEqual(
            report[
                "net_merchandise_before_tax"
            ],
            Decimal("900.00"),
        )


        self.assertEqual(
            report[
                "tax_collected"
            ],
            Decimal("144.00"),
        )


        self.assertEqual(
            report[
                "gross_revenue"
            ],
            Decimal("1244.00"),
        )


        self.assertEqual(
            report[
                "taxable_order_count"
            ],
            1,
        )


    def test_zero_tax_legacy_style_order_remains_valid(
        self,
    ):

        self.create_paid_order(
            number="P12D-002",
            subtotal="500.00",
            discount="0.00",
            tax="0.00",
            tax_rate="0.00",
            delivery="100.00",
            total="600.00",
        )


        request = (
            self.factory.get(
                "/dashboard/admin/reports/"
            )
        )


        report = build_sales_report(
            request
        )


        self.assertEqual(
            report[
                "tax_collected"
            ],
            Decimal("0.00"),
        )


        self.assertEqual(
            report[
                "non_taxable_order_count"
            ],
            1,
        )


    def test_mixed_currencies_are_detected(
        self,
    ):

        self.create_paid_order(
            number="P12D-KES",
            subtotal="1000.00",
            discount="0.00",
            tax="0.00",
            delivery="0.00",
            total="1000.00",
            code="KES",
            symbol="KSh",
            tax_rate="0.00",
        )


        self.create_paid_order(
            number="P12D-USD",
            subtotal="10.00",
            discount="0.00",
            tax="0.00",
            delivery="0.00",
            total="10.00",
            code="USD",
            symbol="$",
            tax_rate="0.00",
        )


        request = (
            self.factory.get(
                "/dashboard/admin/reports/"
            )
        )


        report = build_sales_report(
            request
        )


        self.assertTrue(
            report[
                "has_mixed_currencies"
            ]
        )


        self.assertEqual(
            report[
                "report_currency_label"
            ],
            "MIXED",
        )


        self.assertEqual(
            len(
                report[
                    "currency_breakdown"
                ]
            ),
            2,
        )


    def test_csv_contains_historical_tax_fields(
        self,
    ):

        self.create_paid_order(
            number="P12D-CSV",
            subtotal="2000.00",
            discount="100.00",
            tax="304.00",
            delivery="200.00",
            total="2404.00",
            code="KES",
            symbol="KSh",
        )


        self.client.force_login(
            self.staff
        )


        response = self.client.get(
            reverse(
                "admin_sales_reports_csv"
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        content = (
            response.content.decode(
                "utf-8"
            )
        )


        self.assertIn(
            "Order Financial Detail",
            content,
        )

        self.assertIn(
            "Tax Rate %",
            content,
        )

        self.assertIn(
            "Tax Amount",
            content,
        )

        self.assertIn(
            "P12D-CSV",
            content,
        )

        self.assertIn(
            "304.00",
            content,
        )


class Phase12DDocumentURLTests(
    TestCase
):

    def setUp(self):

        self.user = (
            User.objects.create_user(
                username="phase12d-doc",
                password="pass12345",
            )
        )


        self.order = (
            Order.objects.create(
                user=self.user,
                order_number="P12D-DOC",
                full_name="Document Customer",
                phone="0712345678",
                email="customer@example.com",
                county="Nairobi",
                city="Nairobi",
                estate="CBD",
                house_number="1",
                subtotal=Decimal("1000.00"),
                total_amount=Decimal("1000.00"),
            )
        )


    def test_invoice_email_helper_is_customer_route(
        self,
    ):

        document = OrderDocument(
            order=self.order,
            document_type="invoice",
        )


        self.assertEqual(
            customer_document_view_url(
                document
            ),
            reverse(
                "customer_order_invoice",
                args=[
                    self.order.order_number
                ],
            ),
        )


    def test_receipt_email_helper_is_customer_route(
        self,
    ):

        document = OrderDocument(
            order=self.order,
            document_type="receipt",
        )


        self.assertEqual(
            customer_document_view_url(
                document
            ),
            reverse(
                "customer_order_receipt",
                args=[
                    self.order.order_number
                ],
            ),
        )


    def test_credit_note_email_helper_is_customer_route(
        self,
    ):

        refund = (
            RefundRequest.objects.create(
                order=self.order,
                amount=Decimal("100.00"),
                reason="Phase 12D",
            )
        )


        document = CreditNoteDocument(
            order=self.order,
            refund_request=refund,
        )


        self.assertEqual(
            _customer_credit_note_url(
                document
            ),
            reverse(
                "customer_credit_note",
                args=[
                    refund.pk
                ],
            ),
        )


class Phase12DCurrencySafetyTests(
    TestCase
):

    def setUp(self):

        self.user = (
            User.objects.create_user(
                username="phase12d-money",
                password="pass12345",
            )
        )


        self.store = (
            get_store_settings()
        )


    def _form_data(self):

        data = model_to_dict(
            self.store,
            fields=(
                StoreSettingsForm
                .Meta
                .fields
            ),
        )


        # ModelForm accepts normal Python values,
        # but ensure optional fields do not become None.
        for field_name in (
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
            "checkout_closed_message",
            "document_footer",
        ):

            if data.get(
                field_name
            ) is None:

                data[
                    field_name
                ] = ""


        return data


    def test_currency_change_blocked_with_active_unpaid_order(
        self,
    ):

        Order.objects.create(
            user=self.user,
            order_number="P12D-UNPAID",
            full_name="Pending Customer",
            phone="0712345678",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("500.00"),
            total_amount=Decimal("500.00"),
            status="pending",
            payment_status="pending",
        )


        data = self._form_data()

        data[
            "currency_code"
        ] = "USD"

        data[
            "currency_symbol"
        ] = "$"


        form = StoreSettingsForm(
            data=data,
            instance=self.store,
        )


        self.assertFalse(
            form.is_valid()
        )


        self.assertIn(
            "Currency cannot be changed",
            str(
                form.non_field_errors()
            ),
        )


    def test_currency_change_allowed_without_active_unpaid_orders(
        self,
    ):

        data = self._form_data()

        data[
            "currency_code"
        ] = "USD"

        data[
            "currency_symbol"
        ] = "$"


        form = StoreSettingsForm(
            data=data,
            instance=self.store,
        )


        self.assertTrue(
            form.is_valid(),
            form.errors,
        )
