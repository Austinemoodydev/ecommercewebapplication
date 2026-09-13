from pathlib import Path
import shutil

ROOT = Path.cwd()

SERVICES = ROOT / "delivery" / "services.py"
TEST_FILE = ROOT / "delivery" / "test_ship_phase1.py"

if not SERVICES.exists():
    raise RuntimeError("delivery/services.py not found")

backup = Path(str(SERVICES) + ".shipphase1backup")

if not backup.exists():
    shutil.copy2(SERVICES, backup)

text = SERVICES.read_text(encoding="utf-8-sig")

old = """
        if order.payment_status not in SETTLED_DELIVERY_PAYMENT_STATUSES:

            raise ValidationError(
"""

new = """
        if order.payment_status not in FULFILLABLE_PAYMENT_STATUSES:

            raise ValidationError(
"""

if old not in text:
    if "SETTLED_DELIVERY_PAYMENT_STATUSES" in text:
        raise RuntimeError(
            "Found old payment status reference but not in expected location."
        )
    elif "FULFILLABLE_PAYMENT_STATUSES" in text:
        print("Delivery payment-status fix appears already applied.")
    else:
        raise RuntimeError(
            "Could not safely identify delivery payment-status check."
        )
else:
    text = text.replace(old, new, 1)
    SERVICES.write_text(text, encoding="utf-8")
    print("Fixed delivery payment-status validation.")

TEST_FILE.write_text(
r'''
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from delivery.models import Delivery
from delivery.services import change_delivery_status
from orders.models import Order


User = get_user_model()


class ShipPhase1DeliverySafetyTests(TestCase):

    def setUp(self):

        self.customer = User.objects.create_user(
            username="ship-phase1-customer",
            email="customer@example.com",
            password="pass12345",
            role=User.CUSTOMER,
        )

        self.staff = User.objects.create_user(
            username="ship-phase1-staff",
            email="staff@example.com",
            password="pass12345",
            role=User.ADMIN,
            is_staff=True,
        )

    def create_order(
        self,
        *,
        order_number,
        payment_status,
    ):

        return Order.objects.create(
            user=self.customer,
            order_number=order_number,
            full_name="Phase 1 Customer",
            phone="0712345678",
            email="customer@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("5000.00"),
            shipping_cost=Decimal("300.00"),
            discount=Decimal("0.00"),
            total_amount=Decimal("5300.00"),
            status="processing",
            payment_status=payment_status,
            inventory_status="consumed",
        )

    def create_assigned_delivery(
        self,
        order,
    ):

        return Delivery.objects.create(
            order=order,
            management_type="internal",
            method="local_door",
            status="assigned",
            destination="Nairobi",
            customer_delivery_fee=Decimal("300.00"),
            actual_delivery_cost=Decimal("0.00"),
        )

    def test_paid_order_can_be_dispatched(self):

        order = self.create_order(
            order_number="SHIP-PHASE1-PAID",
            payment_status="paid",
        )

        delivery = self.create_assigned_delivery(
            order
        )

        changed = change_delivery_status(
            delivery=delivery,
            status="dispatched",
            user=self.staff,
            message="Dispatch test",
        )

        changed.refresh_from_db()

        self.assertEqual(
            changed.status,
            "dispatched",
        )

    def test_partially_refunded_order_can_continue_fulfillment(self):

        order = self.create_order(
            order_number="SHIP-PHASE1-PARTIAL",
            payment_status="partially_refunded",
        )

        delivery = self.create_assigned_delivery(
            order
        )

        changed = change_delivery_status(
            delivery=delivery,
            status="dispatched",
            user=self.staff,
        )

        changed.refresh_from_db()

        self.assertEqual(
            changed.status,
            "dispatched",
        )

    def test_fully_refunded_order_cannot_be_dispatched(self):

        order = self.create_order(
            order_number="SHIP-PHASE1-REFUNDED",
            payment_status="refunded",
        )

        delivery = self.create_assigned_delivery(
            order
        )

        with self.assertRaises(
            ValidationError
        ):
            change_delivery_status(
                delivery=delivery,
                status="dispatched",
                user=self.staff,
            )

        delivery.refresh_from_db()

        self.assertEqual(
            delivery.status,
            "assigned",
        )

    def test_pending_payment_cannot_be_dispatched(self):

        order = self.create_order(
            order_number="SHIP-PHASE1-PENDING",
            payment_status="pending",
        )

        delivery = self.create_assigned_delivery(
            order
        )

        with self.assertRaises(
            ValidationError
        ):
            change_delivery_status(
                delivery=delivery,
                status="dispatched",
                user=self.staff,
            )

        delivery.refresh_from_db()

        self.assertEqual(
            delivery.status,
            "assigned",
        )

    def test_failed_payment_cannot_be_dispatched(self):

        order = self.create_order(
            order_number="SHIP-PHASE1-FAILED",
            payment_status="failed",
        )

        delivery = self.create_assigned_delivery(
            order
        )

        with self.assertRaises(
            ValidationError
        ):
            change_delivery_status(
                delivery=delivery,
                status="dispatched",
                user=self.staff,
            )
'''.strip() + "\n",
encoding="utf-8",
)

print()
print("=" * 70)
print("SHIP PHASE 1A PATCH APPLIED")
print("=" * 70)
print("Fixed:")
print(" - delivery NameError")
print(" - fully refunded orders cannot start fulfillment")
print("Added:")
print(" - delivery fulfillment regression tests")
