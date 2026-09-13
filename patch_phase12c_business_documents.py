from pathlib import Path
import shutil


ROOT = Path.cwd()

MODELS = ROOT / "core" / "models.py"
FORMS = ROOT / "core" / "forms.py"

SETTINGS_TEMPLATE = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "settings.html"
)

ORDER_VIEWS = (
    ROOT
    / "orders"
    / "views.py"
)

DOCUMENT_SERVICE = (
    ROOT
    / "orders"
    / "document_service.py"
)

CREDIT_SERVICE = (
    ROOT
    / "orders"
    / "credit_note_service.py"
)

TESTS = (
    ROOT
    / "core"
    / "test_phase12c.py"
)


required = [
    MODELS,
    FORMS,
    SETTINGS_TEMPLATE,
    ORDER_VIEWS,
    DOCUMENT_SERVICE,
    CREDIT_SERVICE,
]


for path in required:

    if not path.exists():

        raise RuntimeError(
            f"Missing required file: {path}"
        )


for path in required:

    backup = Path(
        str(path)
        + ".phase12cbackup"
    )

    if not backup.exists():

        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# 1. STORE SETTINGS MODEL
# ============================================================

text = MODELS.read_text(
    encoding="utf-8-sig"
)


if "business_registration_number" not in text:

    marker = '''    legal_name = models.CharField(
        max_length=200,
        blank=True,
    )
'''


    addition = marker + '''

    business_registration_number = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            "Optional company or business "
            "registration number."
        ),
    )

    tax_pin = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            "Optional tax/KRA PIN shown on "
            "business documents."
        ),
    )
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate legal_name field."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


if "checkout_closed_message" not in text:

    marker = '''    orders_enabled = models.BooleanField(
        default=True,
    )
'''


    addition = marker + '''

    checkout_closed_message = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=(
            "Optional message shown when "
            "online ordering is disabled."
        ),
    )
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate orders_enabled field."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


if "invoice_prefix" not in text:

    marker = '''    document_footer = models.TextField(
        blank=True,
        default=(
            "Thank you for shopping with us."
        ),
    )
'''


    addition = '''    invoice_prefix = models.CharField(
        max_length=20,
        default="INV",
    )

    receipt_prefix = models.CharField(
        max_length=20,
        default="RCP",
    )

    credit_note_prefix = models.CharField(
        max_length=20,
        default="CN",
    )


''' + marker


    if marker not in text:

        raise RuntimeError(
            "Could not locate document_footer."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


MODELS.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 2. FORM FIELDS + VALIDATION
# ============================================================

text = FORMS.read_text(
    encoding="utf-8-sig"
)


# Add business fields.
text = text.replace(
    '''            "legal_name",
            "support_email",
''',
    '''            "legal_name",
            "business_registration_number",
            "tax_pin",
            "support_email",
''',
    1,
)


# Add checkout message.
text = text.replace(
    '''            "orders_enabled",
            "minimum_order_amount",
            "document_footer",
''',
    '''            "orders_enabled",
            "checkout_closed_message",
            "minimum_order_amount",
            "invoice_prefix",
            "receipt_prefix",
            "credit_note_prefix",
            "document_footer",
''',
    1,
)


if "def clean_invoice_prefix" not in text:

    marker = '''    def clean_minimum_order_amount(
        self,
    ):
'''


    methods = r'''    def _clean_document_prefix(
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


'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate minimum order "
            "validation."
        )


    text = text.replace(
        marker,
        methods + marker,
        1,
    )


FORMS.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 3. SETTINGS UI
# ============================================================

text = SETTINGS_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


if "Business Registration Number" not in text:

    marker = '''                <div class="col-md-6">

                    <label class="form-label">
                        Support Email
                    </label>
'''


    addition = '''                <div class="col-md-6">

                    <label class="form-label">
                        Business Registration Number
                    </label>

                    {{ form.business_registration_number }}

                </div>


                <div class="col-md-6">

                    <label class="form-label">
                        Tax / KRA PIN
                    </label>

                    {{ form.tax_pin }}

                </div>


''' + marker


    if marker not in text:

        raise RuntimeError(
            "Could not locate business identity "
            "form section."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


if "Checkout Closed Message" not in text:

    marker = '''                <div class="col-md-6 d-flex align-items-end">

                    <div class="form-check form-switch mb-2">
'''


    addition = '''                <div class="col-12">

                    <label class="form-label">
                        Checkout Closed Message
                    </label>

                    {{ form.checkout_closed_message }}

                    <div class="form-text">
                        Optional. If blank, the system uses
                        a safe default customer message.
                    </div>

                </div>


''' + marker


    if marker not in text:

        raise RuntimeError(
            "Could not locate order controls section."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


if "Invoice Prefix" not in text:

    marker = '''        <!-- DOCUMENTS -->

        <div class="dashboard-card mb-4">

            <h5 class="mb-3">
                Invoice & Receipt Footer
            </h5>

            {{ form.document_footer }}

        </div>
'''


    replacement = '''        <!-- DOCUMENTS -->

        <div class="dashboard-card mb-4">

            <h5 class="mb-3">
                Document Settings
            </h5>


            <div class="row g-3 mb-3">

                <div class="col-md-4">

                    <label class="form-label">
                        Invoice Prefix
                    </label>

                    {{ form.invoice_prefix }}

                    <div class="form-text">
                        Example: INV-ORD123
                    </div>

                </div>


                <div class="col-md-4">

                    <label class="form-label">
                        Receipt Prefix
                    </label>

                    {{ form.receipt_prefix }}

                    <div class="form-text">
                        Example: RCP-ORD123
                    </div>

                </div>


                <div class="col-md-4">

                    <label class="form-label">
                        Credit Note Prefix
                    </label>

                    {{ form.credit_note_prefix }}

                    <div class="form-text">
                        Example: CN-ORD123-01
                    </div>

                </div>

            </div>


            <label class="form-label">
                Invoice & Receipt Footer
            </label>

            {{ form.document_footer }}

        </div>
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate document settings section."
        )


    text = text.replace(
        marker,
        replacement,
        1,
    )


SETTINGS_TEMPLATE.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 4. CUSTOMER-FRIENDLY CLOSED CHECKOUT MESSAGE
# ============================================================

text = ORDER_VIEWS.read_text(
    encoding="utf-8-sig"
)


old = '''        messages.error(
            request,
            (
                "Online ordering is temporarily "
                "unavailable."
            ),
        )
'''


new = '''        messages.error(
            request,
            (
                store_settings.checkout_closed_message
                or
                "Online ordering is temporarily unavailable."
            ),
        )
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


old = '''                    messages.error(
                        request,
                        (
                            "Online ordering was disabled "
                            "before this order could be completed."
                        ),
                    )
'''


new = '''                    messages.error(
                        request,
                        (
                            store_settings.checkout_closed_message
                            or
                            (
                                "Online ordering is temporarily "
                                "unavailable."
                            )
                        ),
                    )
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


ORDER_VIEWS.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 5. INVOICE / RECEIPT STORE SNAPSHOT BUSINESS IDENTITY
# ============================================================

text = DOCUMENT_SERVICE.read_text(
    encoding="utf-8-sig"
)


if '"tax_pin"' not in text:

    marker = '''        "legal_name":
            store.legal_name,
'''


    replacement = marker + '''

        "business_registration_number":
            store.business_registration_number,

        "tax_pin":
            store.tax_pin,
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate Phase 12A store "
            "snapshot."
        )


    text = text.replace(
        marker,
        replacement,
        1,
    )


# ============================================================
# 6. CONFIGURABLE INVOICE / RECEIPT PREFIX
# ============================================================

old = '''def _document_number(
    order,
    document_type,
):

    if document_type == "invoice":

        prefix = "INV"

    elif document_type == "receipt":

        prefix = "RCP"

    else:

        raise ValueError(
            "Unknown document type."
        )


    return (
        f"{prefix}-"
        f"{order.order_number}"
    )
'''


new = '''def _document_number(
    order,
    document_type,
):

    store = (
        get_store_settings()
    )


    if document_type == "invoice":

        prefix = (
            store.invoice_prefix
            or "INV"
        )

    elif document_type == "receipt":

        prefix = (
            store.receipt_prefix
            or "RCP"
        )

    else:

        raise ValueError(
            "Unknown document type."
        )


    prefix = (
        prefix
        .strip()
        .upper()
    )


    return (
        f"{prefix}-"
        f"{order.order_number}"
    )
'''


if old not in text:

    raise RuntimeError(
        "Could not locate _document_number()."
    )


text = text.replace(
    old,
    new,
    1,
)


DOCUMENT_SERVICE.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 7. CREDIT NOTE STORE SETTINGS
# ============================================================

text = CREDIT_SERVICE.read_text(
    encoding="utf-8-sig"
)


if (
    "from core.store_settings import"
    not in text
):

    marker = '''from payments.models import (
    RefundRequest,
)
'''


    replacement = marker + '''

from core.store_settings import (
    business_address,
    get_store_settings,
)
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate credit note imports."
        )


    text = text.replace(
        marker,
        replacement,
        1,
    )


# Replace legacy credit-note store snapshot.
start = text.find(
    "def _store_snapshot():"
)

end = text.find(
    "\n\n\ndef build_credit_note_snapshot(",
    start,
)


if start == -1 or end == -1:

    raise RuntimeError(
        "Could not locate credit note "
        "_store_snapshot()."
    )


new_snapshot = r'''def _store_snapshot():

    store = (
        get_store_settings()
    )


    return {

        "name":
            store.store_name,

        "legal_name":
            store.legal_name,

        "business_registration_number":
            store.business_registration_number,

        "tax_pin":
            store.tax_pin,

        "email":
            store.support_email,

        "phone":
            store.support_phone,

        "address":
            business_address(
                store
            ),

        "website":
            store.website_url,

        "currency_code":
            store.currency_code,

        "currency_symbol":
            store.currency_symbol,

        "document_footer":
            store.document_footer,
    }
'''


text = (
    text[:start]
    + new_snapshot
    + text[end:]
)


old = '''def _credit_note_number(
    refund,
):

    # Refund ID provides stable uniqueness.
    return (
        f"CN-"
        f"{refund.order.order_number}-"
        f"{refund.pk:02d}"
    )
'''


new = '''def _credit_note_number(
    refund,
):

    store = (
        get_store_settings()
    )


    prefix = (
        store.credit_note_prefix
        or "CN"
    )


    prefix = (
        prefix
        .strip()
        .upper()
    )


    # Refund ID provides stable uniqueness.
    return (
        f"{prefix}-"
        f"{refund.order.order_number}-"
        f"{refund.pk:02d}"
    )
'''


if old not in text:

    raise RuntimeError(
        "Could not locate _credit_note_number()."
    )


text = text.replace(
    old,
    new,
    1,
)


CREDIT_SERVICE.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 8. TESTS
# ============================================================

TESTS.write_text(
r'''
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
'''.strip() + "\n",
encoding="utf-8",
)


print()
print("=" * 72)
print("PHASE 12C INSTALLED")
print("=" * 72)
print()
print("Added:")
print("  Optional business registration number")
print("  Optional tax/KRA PIN")
print("  Configurable checkout-closed message")
print("  Configurable invoice prefix")
print("  Configurable receipt prefix")
print("  Configurable credit-note prefix")
print("  Credit notes now use database store identity")
print("  Existing documents remain immutable")
print("  Safe defaults remain purchase-friendly")
print()
print("Migration required.")
