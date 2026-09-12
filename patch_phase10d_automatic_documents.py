from pathlib import Path
import shutil


ROOT = Path.cwd()

ORDERS_APPS = (
    ROOT
    / "orders"
    / "apps.py"
)

SIGNALS = (
    ROOT
    / "orders"
    / "signals.py"
)

CUSTOMER_DETAIL = (
    ROOT
    / "templates"
    / "dashboard"
    / "order_detail.html"
)

TESTS = (
    ROOT
    / "dashboard"
    / "test_phase10d.py"
)


# ============================================================
# VALIDATION
# ============================================================

for path in [
    ORDERS_APPS,
    CUSTOMER_DETAIL,
]:

    if not path.exists():

        raise RuntimeError(
            f"Missing required file: {path}"
        )


# ============================================================
# BACKUPS
# ============================================================

for path in [
    ORDERS_APPS,
    CUSTOMER_DETAIL,
]:

    backup = Path(
        str(path)
        + ".phase10dbackup"
    )

    if not backup.exists():

        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# 1. REFUND -> CREDIT NOTE SIGNAL
# ============================================================

SIGNALS.write_text(
r'''
from django.db.models.signals import (
    post_save,
)

from django.dispatch import receiver

from payments.models import (
    RefundRequest,
)


@receiver(
    post_save,
    sender=RefundRequest,
)
def create_credit_note_for_processed_refund(
    sender,
    instance,
    **kwargs,
):

    """
    Automatically issue the immutable credit note once a
    refund has genuinely reached 'processed'.

    Important:
    - requested/approved/rejected refunds create nothing;
    - an external refund reference is required;
    - get_or_issue_credit_note() is idempotent;
    - repeated saves cannot create duplicate credit notes.
    """

    if instance.status != "processed":
        return


    if not (
        instance.external_reference
        or ""
    ).strip():

        return


    # Local import avoids application-loading circular imports.
    from orders.credit_note_service import (
        get_or_issue_credit_note,
    )


    get_or_issue_credit_note(
        refund=instance,
        issued_by=instance.processed_by,
    )
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Automatic processed-refund signal created."
)


# ============================================================
# 2. LOAD SIGNALS FROM ORDERS APP
# ============================================================

text = ORDERS_APPS.read_text(
    encoding="utf-8-sig"
)


if "def ready(self):" not in text:

    # Add ready() inside the first AppConfig class.
    lines = text.splitlines()

    class_index = None

    for index, line in enumerate(
        lines
    ):

        if (
            line.startswith("class ")
            and "AppConfig" in line
        ):

            class_index = index
            break


    if class_index is None:

        raise RuntimeError(
            "Could not locate orders AppConfig class."
        )


    insert_index = len(lines)


    for index in range(
        class_index + 1,
        len(lines),
    ):

        if (
            lines[index]
            and
            not lines[index].startswith(
                (" ", "\t")
            )
        ):

            insert_index = index
            break


    ready_method = [
        "",
        "    def ready(self):",
        "        from . import signals  # noqa: F401",
    ]


    lines[
        insert_index:insert_index
    ] = ready_method


    text = "\n".join(
        lines
    ) + "\n"


elif (
    "from . import signals"
    not in text
):

    marker = "    def ready(self):\n"

    replacement = (
        "    def ready(self):\n"
        "        from . import signals  # noqa: F401\n"
    )

    text = text.replace(
        marker,
        replacement,
        1,
    )


else:

    print(
        "orders.apps already loads signals."
    )


ORDERS_APPS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Orders AppConfig loads document signals."
)


# ============================================================
# 3. CUSTOMER FINANCIAL DOCUMENT HISTORY
# ============================================================

text = CUSTOMER_DETAIL.read_text(
    encoding="utf-8-sig"
)


if "My Financial Documents" not in text:

    marker = "{% endblock %}"


    if marker not in text:

        raise RuntimeError(
            "Could not locate final "
            "{% endblock %} in customer order detail."
        )


    block = r'''

<!-- ===================================================== -->
<!-- CUSTOMER FINANCIAL DOCUMENT HISTORY -->
<!-- ===================================================== -->

<div class="card shadow-sm border-0 mt-4">

    <div class="card-body">

        <div
            class="
                d-flex
                justify-content-between
                align-items-center
                flex-wrap
                gap-2
                mb-3
            "
        >

            <div>

                <h5 class="mb-1">
                    My Financial Documents
                </h5>

                <div class="text-muted small">
                    Invoices, payment receipts and refund credit notes
                </div>

            </div>

        </div>


        <div class="table-responsive">

            <table
                class="
                    table
                    table-hover
                    align-middle
                    mb-0
                "
            >

                <thead>

                    <tr>

                        <th>
                            Type
                        </th>

                        <th>
                            Document Number
                        </th>

                        <th>
                            Issued
                        </th>

                        <th class="text-end">
                            Action
                        </th>

                    </tr>

                </thead>


                <tbody>

                    {% for document in order.documents.all %}

                        <tr>

                            <td>

                                {% if document.document_type == "invoice" %}

                                    <span
                                        class="
                                            badge
                                            bg-primary-subtle
                                            text-primary
                                        "
                                    >
                                        Invoice
                                    </span>

                                {% else %}

                                    <span
                                        class="
                                            badge
                                            bg-success-subtle
                                            text-success
                                        "
                                    >
                                        Receipt
                                    </span>

                                {% endif %}

                            </td>


                            <td>

                                <strong>
                                    {{ document.document_number }}
                                </strong>

                            </td>


                            <td>

                                {{ document.issued_at|date:"d M Y H:i" }}

                            </td>


                            <td class="text-end">

                                {% if document.document_type == "invoice" %}

                                    <a
                                        href="{% url 'customer_order_invoice' order.order_number %}"
                                        class="
                                            btn
                                            btn-sm
                                            btn-outline-primary
                                        "
                                        target="_blank"
                                    >
                                        Open
                                    </a>

                                {% else %}

                                    <a
                                        href="{% url 'customer_order_receipt' order.order_number %}"
                                        class="
                                            btn
                                            btn-sm
                                            btn-outline-success
                                        "
                                        target="_blank"
                                    >
                                        Open
                                    </a>

                                {% endif %}

                            </td>

                        </tr>

                    {% endfor %}


                    {% for credit_note in order.credit_notes.all %}

                        <tr>

                            <td>

                                <span
                                    class="
                                        badge
                                        bg-danger-subtle
                                        text-danger
                                    "
                                >
                                    Credit Note
                                </span>

                            </td>


                            <td>

                                <strong>
                                    {{ credit_note.document_number }}
                                </strong>

                            </td>


                            <td>

                                {{ credit_note.issued_at|date:"d M Y H:i" }}

                            </td>


                            <td class="text-end">

                                <a
                                    href="{% url 'customer_credit_note' credit_note.refund_request_id %}"
                                    class="
                                        btn
                                        btn-sm
                                        btn-outline-danger
                                    "
                                    target="_blank"
                                >
                                    Open
                                </a>

                            </td>

                        </tr>

                    {% endfor %}


                    {% if not order.documents.all and not order.credit_notes.all %}

                        <tr>

                            <td
                                colspan="4"
                                class="
                                    text-center
                                    text-muted
                                    py-4
                                "
                            >
                                No financial documents have been issued yet.
                            </td>

                        </tr>

                    {% endif %}

                </tbody>

            </table>

        </div>

    </div>

</div>


'''


    text = text.replace(
        marker,
        block + marker,
        1,
    )


    CUSTOMER_DETAIL.write_text(
        text,
        encoding="utf-8",
    )

    print(
        "Customer financial document history added."
    )

else:

    print(
        "Customer document history already exists."
    )


# ============================================================
# 4. PHASE 10D TESTS
# ============================================================

TESTS.write_text(
r'''
from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase

from django.urls import reverse

from categories.models import Category

from orders.models import (
    CreditNoteDocument,
    Order,
    OrderDocument,
    OrderItem,
)

from payments.models import (
    RefundRequest,
)

from products.models import Product


User = get_user_model()


class Phase10DAutomaticDocumentTests(
    TestCase
):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="phase10dcustomer",
                password="pass12345",
                email="phase10d@example.com",
                role=User.CUSTOMER,
            )
        )


        self.staff = (
            User.objects.create_user(
                username="phase10dstaff",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )


        self.category = (
            Category.objects.create(
                name="Phase 10D",
                slug="phase-10d",
            )
        )


        self.product = (
            Product.objects.create(
                category=self.category,
                name="Phase 10D Laptop",
                slug="phase-10d-laptop",
                sku="P10D-001",
                price=Decimal(
                    "70000.00"
                ),
                cost_price=Decimal(
                    "50000.00"
                ),
                stock=10,
                reserved_stock=0,
                is_active=True,
            )
        )


        self.order = (
            Order.objects.create(
                user=self.customer,
                order_number="PHASE10D-001",
                full_name="Phase 10D Customer",
                phone="0712345678",
                email="phase10d@example.com",
                county="Nairobi",
                city="Nairobi",
                estate="CBD",
                house_number="10",
                subtotal=Decimal(
                    "70000.00"
                ),
                shipping_cost=Decimal(
                    "500.00"
                ),
                discount=Decimal(
                    "0.00"
                ),
                total_amount=Decimal(
                    "70500.00"
                ),
                status="delivered",
                payment_status="paid",
                inventory_status="consumed",
                payment_method="mpesa",
            )
        )


        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=(
                "Phase 10D Laptop"
            ),
            price=Decimal(
                "70000.00"
            ),
            unit_cost_at_sale=Decimal(
                "50000.00"
            ),
            cost_subtotal_at_sale=Decimal(
                "50000.00"
            ),
            quantity=1,
            subtotal=Decimal(
                "70000.00"
            ),
        )


    def test_processed_refund_automatically_creates_credit_note(
        self
    ):

        refund = (
            RefundRequest.objects.create(
                order=self.order,
                amount=Decimal(
                    "5000.00"
                ),
                reason="Automatic refund",
                status="processed",
                external_reference=(
                    "AUTO-REF-001"
                ),
                processed_by=self.staff,
            )
        )


        self.assertTrue(
            CreditNoteDocument.objects
            .filter(
                refund_request=refund
            )
            .exists()
        )


    def test_requested_refund_does_not_create_credit_note(
        self
    ):

        refund = (
            RefundRequest.objects.create(
                order=self.order,
                amount=Decimal(
                    "5000.00"
                ),
                reason="Not processed",
                status="requested",
            )
        )


        self.assertFalse(
            CreditNoteDocument.objects
            .filter(
                refund_request=refund
            )
            .exists()
        )


    def test_processed_without_reference_does_not_create_credit_note(
        self
    ):

        refund = (
            RefundRequest.objects.create(
                order=self.order,
                amount=Decimal(
                    "5000.00"
                ),
                reason="Missing reference",
                status="processed",
                external_reference="",
                processed_by=self.staff,
            )
        )


        self.assertFalse(
            CreditNoteDocument.objects
            .filter(
                refund_request=refund
            )
            .exists()
        )


    def test_credit_note_created_when_reference_added_later(
        self
    ):

        refund = (
            RefundRequest.objects.create(
                order=self.order,
                amount=Decimal(
                    "5000.00"
                ),
                reason="Reference later",
                status="processed",
                external_reference="",
                processed_by=self.staff,
            )
        )


        self.assertFalse(
            CreditNoteDocument.objects
            .filter(
                refund_request=refund
            )
            .exists()
        )


        refund.external_reference = (
            "LATE-REF-001"
        )

        refund.save(
            update_fields=[
                "external_reference",
                "updated_at",
            ]
        )


        self.assertTrue(
            CreditNoteDocument.objects
            .filter(
                refund_request=refund
            )
            .exists()
        )


    def test_repeated_processed_save_does_not_duplicate_credit_note(
        self
    ):

        refund = (
            RefundRequest.objects.create(
                order=self.order,
                amount=Decimal(
                    "5000.00"
                ),
                reason="Repeated save",
                status="processed",
                external_reference=(
                    "AUTO-REF-002"
                ),
                processed_by=self.staff,
            )
        )


        refund.staff_note = (
            "Updated after processing"
        )

        refund.save(
            update_fields=[
                "staff_note",
                "updated_at",
            ]
        )


        self.assertEqual(
            CreditNoteDocument.objects
            .filter(
                refund_request=refund
            )
            .count(),
            1,
        )


    def test_customer_order_page_lists_documents(
        self
    ):

        OrderDocument.objects.create(
            order=self.order,
            document_type="invoice",
            document_number=(
                "INV-PHASE10D-001"
            ),
            snapshot={
                "order": {
                    "order_number":
                        "PHASE10D-001"
                }
            },
            issued_by=self.customer,
        )


        refund = (
            RefundRequest.objects.create(
                order=self.order,
                amount=Decimal(
                    "5000.00"
                ),
                reason="History test",
                status="processed",
                external_reference=(
                    "HISTORY-REF-001"
                ),
                processed_by=self.staff,
            )
        )


        credit_note = (
            CreditNoteDocument.objects.get(
                refund_request=refund
            )
        )


        self.client.login(
            username="phase10dcustomer",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "order_detail",
                args=[
                    self.order.order_number
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            "My Financial Documents",
        )


        self.assertContains(
            response,
            "INV-PHASE10D-001",
        )


        self.assertContains(
            response,
            credit_note.document_number,
        )
'''.strip() + "\n",
encoding="utf-8",
)


print(
    "Phase 10D tests created."
)


print()
print("=" * 72)
print("PHASE 10D AUTOMATIC DOCUMENT WORKFLOW INSTALLED")
print("=" * 72)
print()
print("Added:")
print("  Automatic credit-note creation")
print("  Processed-refund signal")
print("  External-reference safety")
print("  Duplicate credit-note protection")
print("  Customer financial document history")
print("  Invoice history")
print("  Receipt history")
print("  Credit-note history")
print()
print("No migration required.")
