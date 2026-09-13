from pathlib import Path
import shutil


ROOT = Path.cwd()

MODELS = ROOT / "core" / "models.py"
FORMS = ROOT / "core" / "forms.py"
SERVICE = ROOT / "core" / "store_settings.py"
VIEWS = ROOT / "core" / "settings_views.py"
CONTEXT = ROOT / "core" / "context_processors.py"

URLS = ROOT / "dashboard" / "urls.py"

SIDEBAR = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "base.html"
)

TEMPLATE = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "settings.html"
)

DOCUMENT_SERVICE = (
    ROOT
    / "orders"
    / "document_service.py"
)

TESTS = (
    ROOT
    / "core"
    / "test_phase12a.py"
)


required = [
    MODELS,
    CONTEXT,
    URLS,
    SIDEBAR,
    DOCUMENT_SERVICE,
]

for path in required:

    if not path.exists():
        raise RuntimeError(
            f"Missing required file: {path}"
        )


for path in required:

    backup = Path(
        str(path)
        + ".phase12abackup"
    )

    if not backup.exists():
        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# 1. STORE SETTINGS MODEL
# ============================================================

MODELS.write_text(
r'''
from decimal import Decimal

from django.conf import settings
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models


class StoreSettings(models.Model):

    """
    Singleton business configuration.

    The application always uses primary key 1.
    """

    SINGLETON_PK = 1


    # --------------------------------------------------------
    # BUSINESS IDENTITY
    # --------------------------------------------------------

    store_name = models.CharField(
        max_length=150,
        default="Online Shop",
    )

    legal_name = models.CharField(
        max_length=200,
        blank=True,
    )


    # --------------------------------------------------------
    # CONTACT DETAILS
    # --------------------------------------------------------

    support_email = models.EmailField(
        blank=True,
    )

    support_phone = models.CharField(
        max_length=30,
        blank=True,
    )

    whatsapp_number = models.CharField(
        max_length=30,
        blank=True,
    )

    website_url = models.URLField(
        blank=True,
    )


    # --------------------------------------------------------
    # BUSINESS LOCATION
    # --------------------------------------------------------

    address = models.CharField(
        max_length=255,
        blank=True,
    )

    city = models.CharField(
        max_length=100,
        blank=True,
    )

    county = models.CharField(
        max_length=100,
        blank=True,
    )

    country = models.CharField(
        max_length=100,
        default="Kenya",
    )


    # --------------------------------------------------------
    # CURRENCY / FINANCE
    # --------------------------------------------------------

    currency_code = models.CharField(
        max_length=10,
        default="KES",
    )

    currency_symbol = models.CharField(
        max_length=10,
        default="KSh",
    )

    tax_enabled = models.BooleanField(
        default=False,
    )

    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(
                Decimal("0.00")
            ),
            MaxValueValidator(
                Decimal("100.00")
            ),
        ],
        help_text="Percentage from 0 to 100.",
    )


    # --------------------------------------------------------
    # ORDER SETTINGS
    # --------------------------------------------------------

    orders_enabled = models.BooleanField(
        default=True,
    )

    minimum_order_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(
                Decimal("0.00")
            ),
        ],
    )


    # --------------------------------------------------------
    # DOCUMENT SETTINGS
    # --------------------------------------------------------

    document_footer = models.TextField(
        blank=True,
        default=(
            "Thank you for shopping with us."
        ),
    )


    # --------------------------------------------------------
    # AUDIT
    # --------------------------------------------------------

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=(
            "store_settings_updates"
        ),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )


    class Meta:

        verbose_name = (
            "Store Settings"
        )

        verbose_name_plural = (
            "Store Settings"
        )


    def save(
        self,
        *args,
        **kwargs,
    ):

        # Enforce singleton storage.
        self.pk = self.SINGLETON_PK

        self.currency_code = (
            self.currency_code
            .strip()
            .upper()
        )

        super().save(
            *args,
            **kwargs,
        )


    def delete(
        self,
        *args,
        **kwargs,
    ):

        # Business configuration should never
        # disappear accidentally.
        return


    def __str__(self):

        return self.store_name
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "StoreSettings model created."
)


# ============================================================
# 2. SETTINGS SERVICE
# ============================================================

SERVICE.write_text(
r'''
from .models import StoreSettings


def get_store_settings():

    """
    Return the singleton store settings record.
    """

    settings_obj, _created = (
        StoreSettings.objects.get_or_create(
            pk=StoreSettings.SINGLETON_PK
        )
    )

    return settings_obj


def business_address(
    settings_obj=None,
):

    settings_obj = (
        settings_obj
        or get_store_settings()
    )


    parts = [
        settings_obj.address,
        settings_obj.city,
        settings_obj.county,
        settings_obj.country,
    ]


    return ", ".join(
        str(part).strip()
        for part in parts
        if part
        and str(part).strip()
    )
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Store settings service created."
)


# ============================================================
# 3. FORM
# ============================================================

FORMS.write_text(
r'''
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
            "minimum_order_amount",
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
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Store settings form created."
)


# ============================================================
# 4. ADMIN SETTINGS VIEW
# ============================================================

VIEWS.write_text(
r'''
from django.contrib import messages

from django.contrib.admin.views.decorators import (
    staff_member_required,
)

from django.shortcuts import (
    redirect,
    render,
)

from django.views.decorators.http import (
    require_http_methods,
)

from .forms import StoreSettingsForm

from .store_settings import (
    get_store_settings,
)


@staff_member_required
@require_http_methods(
    [
        "GET",
        "POST",
    ]
)
def admin_store_settings(
    request,
):

    settings_obj = (
        get_store_settings()
    )


    form = StoreSettingsForm(
        request.POST or None,
        instance=settings_obj,
    )


    if (
        request.method == "POST"
        and form.is_valid()
    ):

        store_settings = (
            form.save(
                commit=False
            )
        )

        store_settings.updated_by = (
            request.user
        )

        store_settings.save()


        messages.success(
            request,
            "Store settings updated successfully.",
        )


        return redirect(
            "admin_store_settings"
        )


    return render(
        request,
        "dashboard/admin/settings.html",
        {
            "form":
                form,

            "store_settings":
                settings_obj,
        },
    )
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Admin store settings view created."
)


# ============================================================
# 5. GLOBAL CONTEXT
# ============================================================

text = CONTEXT.read_text(
    encoding="utf-8-sig"
)


if (
    "from core.store_settings import "
    "get_store_settings"
    not in text
):

    text = text.replace(
        '''from django.conf import settings
''',
        '''from django.conf import settings

from core.store_settings import (
    get_store_settings,
)
''',
        1,
    )


old = '''    return {

        "wishlist_count": wishlist_count,
'''

new = '''    store_settings = (
        get_store_settings()
    )


    return {

        "store_settings":
            store_settings,

        "wishlist_count": wishlist_count,
'''


if old not in text:

    raise RuntimeError(
        "Could not locate global_context return."
    )


text = text.replace(
    old,
    new,
    1,
)


CONTEXT.write_text(
    text,
    encoding="utf-8",
)

print(
    "Global store settings context added."
)


# ============================================================
# 6. DASHBOARD ROUTE
# ============================================================

text = URLS.read_text(
    encoding="utf-8-sig"
)


if (
    "from core import settings_views"
    not in text
):

    text = text.replace(
        '''from . import reports_views
''',
        '''from . import reports_views
from core import settings_views
''',
        1,
    )


if (
    'name="admin_store_settings"'
    not in text
):

    marker = '''    # =========================================================
    # STORE MANAGEMENT DASHBOARD
    # =========================================================

    path(
        "admin/",
        views.admin_dashboard,
        name="admin_dashboard",
    ),
'''


    addition = marker + '''

    # =========================================================
    # STORE SETTINGS
    # =========================================================

    path(
        "admin/settings/",
        settings_views.admin_store_settings,
        name="admin_store_settings",
    ),
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate admin dashboard route."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


URLS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Store settings route added."
)


# ============================================================
# 7. SIDEBAR
# ============================================================

text = SIDEBAR.read_text(
    encoding="utf-8-sig"
)


old = '''            <!-- SETTINGS -->

            <a
                href="#"
                class="sidebar-link"
            >

                <i class="bi bi-gear"></i>

                <span>
                    Settings
                </span>

            </a>
'''


new = '''            <!-- SETTINGS -->

            <a
                href="{% url 'admin_store_settings' %}"
                class="
                    sidebar-link
                    {% if request.resolver_match.url_name == 'admin_store_settings' %}
                        active
                    {% endif %}
                "
            >

                <i class="bi bi-gear"></i>

                <span>
                    Settings
                </span>

            </a>
'''


if old not in text:

    raise RuntimeError(
        "Could not locate Settings sidebar placeholder."
    )


text = text.replace(
    old,
    new,
    1,
)


SIDEBAR.write_text(
    text,
    encoding="utf-8",
)

print(
    "Settings sidebar linked."
)


# ============================================================
# 8. ADMIN TEMPLATE
# ============================================================

TEMPLATE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


TEMPLATE.write_text(
r'''
{% extends "dashboard/admin/base.html" %}


{% block title %}
Store Settings
{% endblock %}


{% block page_heading %}
Store Settings
{% endblock %}


{% block admin_content %}

<div class="container-fluid">

    <div class="mb-4">

        <h1 class="h3 mb-1">
            Store Settings
        </h1>

        <p class="text-muted mb-0">
            Manage business identity, contact details,
            currency and ordering configuration.
        </p>

    </div>


    <form method="post">

        {% csrf_token %}


        {% if form.non_field_errors %}

            <div class="alert alert-danger">
                {{ form.non_field_errors }}
            </div>

        {% endif %}


        <!-- BUSINESS IDENTITY -->

        <div class="dashboard-card mb-4">

            <h5 class="mb-3">
                Business Identity
            </h5>


            <div class="row g-3">

                <div class="col-md-6">

                    <label class="form-label">
                        Store Name
                    </label>

                    {{ form.store_name }}

                    {% for error in form.store_name.errors %}
                        <div class="text-danger small">
                            {{ error }}
                        </div>
                    {% endfor %}

                </div>


                <div class="col-md-6">

                    <label class="form-label">
                        Legal / Registered Name
                    </label>

                    {{ form.legal_name }}

                </div>


                <div class="col-md-6">

                    <label class="form-label">
                        Support Email
                    </label>

                    {{ form.support_email }}

                </div>


                <div class="col-md-6">

                    <label class="form-label">
                        Support Phone
                    </label>

                    {{ form.support_phone }}

                </div>


                <div class="col-md-6">

                    <label class="form-label">
                        WhatsApp Number
                    </label>

                    {{ form.whatsapp_number }}

                </div>


                <div class="col-md-6">

                    <label class="form-label">
                        Website
                    </label>

                    {{ form.website_url }}

                </div>

            </div>

        </div>


        <!-- ADDRESS -->

        <div class="dashboard-card mb-4">

            <h5 class="mb-3">
                Business Address
            </h5>


            <div class="row g-3">

                <div class="col-12">

                    <label class="form-label">
                        Street / Building Address
                    </label>

                    {{ form.address }}

                </div>


                <div class="col-md-4">

                    <label class="form-label">
                        City / Town
                    </label>

                    {{ form.city }}

                </div>


                <div class="col-md-4">

                    <label class="form-label">
                        County
                    </label>

                    {{ form.county }}

                </div>


                <div class="col-md-4">

                    <label class="form-label">
                        Country
                    </label>

                    {{ form.country }}

                </div>

            </div>

        </div>


        <!-- FINANCE -->

        <div class="dashboard-card mb-4">

            <h5 class="mb-3">
                Currency & Tax
            </h5>


            <div class="row g-3">

                <div class="col-md-4">

                    <label class="form-label">
                        Currency Code
                    </label>

                    {{ form.currency_code }}

                    {% for error in form.currency_code.errors %}
                        <div class="text-danger small">
                            {{ error }}
                        </div>
                    {% endfor %}

                </div>


                <div class="col-md-4">

                    <label class="form-label">
                        Currency Symbol
                    </label>

                    {{ form.currency_symbol }}

                </div>


                <div class="col-md-4">

                    <label class="form-label">
                        Tax Rate (%)
                    </label>

                    {{ form.tax_rate }}

                    {% for error in form.tax_rate.errors %}
                        <div class="text-danger small">
                            {{ error }}
                        </div>
                    {% endfor %}

                </div>


                <div class="col-12">

                    <div class="form-check form-switch">

                        {{ form.tax_enabled }}

                        <label
                            class="form-check-label"
                            for="{{ form.tax_enabled.id_for_label }}"
                        >
                            Enable tax calculation
                        </label>

                    </div>

                </div>

            </div>

        </div>


        <!-- ORDER SETTINGS -->

        <div class="dashboard-card mb-4">

            <h5 class="mb-3">
                Order Controls
            </h5>


            <div class="row g-3">

                <div class="col-md-6">

                    <label class="form-label">
                        Minimum Order Amount
                    </label>

                    {{ form.minimum_order_amount }}

                    {% for error in form.minimum_order_amount.errors %}
                        <div class="text-danger small">
                            {{ error }}
                        </div>
                    {% endfor %}

                </div>


                <div class="col-md-6 d-flex align-items-end">

                    <div class="form-check form-switch mb-2">

                        {{ form.orders_enabled }}

                        <label
                            class="form-check-label"
                            for="{{ form.orders_enabled.id_for_label }}"
                        >
                            Accept new customer orders
                        </label>

                    </div>

                </div>

            </div>

        </div>


        <!-- DOCUMENTS -->

        <div class="dashboard-card mb-4">

            <h5 class="mb-3">
                Invoice & Receipt Footer
            </h5>

            {{ form.document_footer }}

        </div>


        <div class="d-flex justify-content-between align-items-center flex-wrap gap-3">

            <div class="small text-muted">

                {% if store_settings.updated_at %}

                    Last updated:
                    {{ store_settings.updated_at|date:"d M Y H:i" }}

                    {% if store_settings.updated_by %}
                        by {{ store_settings.updated_by.username }}
                    {% endif %}

                {% endif %}

            </div>


            <button
                type="submit"
                class="btn btn-primary"
            >
                <i class="bi bi-check-lg me-1"></i>
                Save Settings
            </button>

        </div>

    </form>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Store settings UI created."
)


# ============================================================
# 9. BOOTSTRAP FORM STYLING
# ============================================================

text = FORMS.read_text(
    encoding="utf-8-sig"
)


append = r'''


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
'''


if (
    "# Bootstrap-friendly widgets"
    not in text
):

    text = text.rstrip() + append + "\n"


FORMS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Settings form Bootstrap classes added."
)


# ============================================================
# 10. DOCUMENT SNAPSHOT INTEGRATION
# ============================================================

text = DOCUMENT_SERVICE.read_text(
    encoding="utf-8-sig"
)


if (
    "from core.store_settings import"
    not in text
):

    marker = '''from orders.models import (
    Order,
    OrderDocument,
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
            "Could not locate document service imports."
        )

    text = text.replace(
        marker,
        replacement,
        1,
    )


start = text.find(
    "def _store_snapshot():"
)

end = text.find(
    "\n\n\ndef _successful_payment(",
    start,
)


if start == -1 or end == -1:

    raise RuntimeError(
        "Could not locate _store_snapshot()."
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

        "email":
            store.support_email,

        "phone":
            store.support_phone,

        "whatsapp":
            store.whatsapp_number,

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


DOCUMENT_SERVICE.write_text(
    text,
    encoding="utf-8",
)

print(
    "Invoice/receipt store snapshots now use database settings."
)


# ============================================================
# 11. TESTS
# ============================================================

TESTS.write_text(
r'''
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
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Phase 12A tests created."
)


print()
print("=" * 72)
print("PHASE 12A INSTALLED")
print("=" * 72)
print()
print("Added:")
print("  Singleton StoreSettings model")
print("  Business identity")
print("  Contact details")
print("  Business address")
print("  Currency configuration")
print("  Tax configuration")
print("  Order enable/disable setting")
print("  Minimum order setting")
print("  Invoice/receipt footer")
print("  Staff settings UI")
print("  Last-updated audit")
print("  Global store settings template context")
print("  Invoice/receipt snapshot integration")
print()
print("Migration required.")
