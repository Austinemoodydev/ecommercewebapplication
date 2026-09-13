from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()

if not (ROOT / "manage.py").exists():
    raise SystemExit(
        "ERROR: Run this command from the project folder containing manage.py."
    )

STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
BACKUP = ROOT / ".staff_management_backups" / STAMP
BACKUP.mkdir(parents=True, exist_ok=True)


def backup(path):
    if not path.exists():
        return

    target = BACKUP / path.relative_to(ROOT)

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        path,
        target,
    )


def write(rel, content):
    path = ROOT / rel

    if path.exists():
        backup(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        content,
        encoding="utf-8",
    )

    print("[CREATED/UPDATED]", rel)


print("=" * 76)
print("STORE STAFF ROLES + MANAGEMENT")
print("=" * 76)


# ============================================================
# 1. STORE ROLE DEFINITIONS
# ============================================================

write(
    "accounts/store_roles.py",
r'''STORE_OWNER = "Store Owner"
STORE_MANAGER = "Store Manager"
ORDER_STAFF = "Orders Staff"
INVENTORY_STAFF = "Inventory Staff"
FINANCE_STAFF = "Finance Staff"
SUPPORT_STAFF = "Support Staff"


STORE_ROLE_NAMES = [
    STORE_OWNER,
    STORE_MANAGER,
    ORDER_STAFF,
    INVENTORY_STAFF,
    FINANCE_STAFF,
    SUPPORT_STAFF,
]


ROLE_PERMISSION_MAP = {

    STORE_OWNER: [
        ("orders", "view_order"),
        ("orders", "add_order"),
        ("orders", "change_order"),
        ("orders", "delete_order"),

        ("orders", "view_orderitem"),
        ("orders", "add_orderitem"),
        ("orders", "change_orderitem"),
        ("orders", "delete_orderitem"),

        ("orders", "view_coupon"),
        ("orders", "add_coupon"),
        ("orders", "change_coupon"),
        ("orders", "delete_coupon"),

        ("products", "view_product"),
        ("products", "add_product"),
        ("products", "change_product"),
        ("products", "delete_product"),

        ("products", "view_productvariant"),
        ("products", "add_productvariant"),
        ("products", "change_productvariant"),
        ("products", "delete_productvariant"),

        ("products", "view_brand"),
        ("products", "add_brand"),
        ("products", "change_brand"),
        ("products", "delete_brand"),

        ("categories", "view_category"),
        ("categories", "add_category"),
        ("categories", "change_category"),
        ("categories", "delete_category"),

        ("inventory", "view_inventorymovement"),
        ("inventory", "add_inventorymovement"),
        ("inventory", "change_inventorymovement"),

        ("payments", "view_mpesatransaction"),
        ("payments", "change_mpesatransaction"),

        ("payments", "view_refundrequest"),
        ("payments", "change_refundrequest"),

        ("payments", "view_returnrequest"),
        ("payments", "change_returnrequest"),

        ("delivery", "view_delivery"),
        ("delivery", "add_delivery"),
        ("delivery", "change_delivery"),

        ("delivery", "view_deliveryprovider"),
        ("delivery", "add_deliveryprovider"),
        ("delivery", "change_deliveryprovider"),

        ("delivery", "view_deliveryzone"),
        ("delivery", "add_deliveryzone"),
        ("delivery", "change_deliveryzone"),

        ("crm", "view_customernote"),
        ("crm", "add_customernote"),
        ("crm", "change_customernote"),
        ("crm", "delete_customernote"),

        ("reviews", "view_review"),
        ("reviews", "change_review"),
        ("reviews", "delete_review"),

        ("notifications", "view_notification"),
        ("notifications", "change_notification"),

        ("core", "view_storesettings"),
        ("core", "change_storesettings"),
    ],


    STORE_MANAGER: [
        ("orders", "view_order"),
        ("orders", "change_order"),
        ("orders", "view_orderitem"),

        ("orders", "view_coupon"),
        ("orders", "add_coupon"),
        ("orders", "change_coupon"),

        ("products", "view_product"),
        ("products", "add_product"),
        ("products", "change_product"),

        ("products", "view_productvariant"),
        ("products", "add_productvariant"),
        ("products", "change_productvariant"),

        ("products", "view_brand"),
        ("products", "add_brand"),
        ("products", "change_brand"),

        ("categories", "view_category"),
        ("categories", "add_category"),
        ("categories", "change_category"),

        ("inventory", "view_inventorymovement"),
        ("inventory", "add_inventorymovement"),
        ("inventory", "change_inventorymovement"),

        ("delivery", "view_delivery"),
        ("delivery", "add_delivery"),
        ("delivery", "change_delivery"),

        ("delivery", "view_deliveryprovider"),
        ("delivery", "change_deliveryprovider"),

        ("delivery", "view_deliveryzone"),
        ("delivery", "change_deliveryzone"),

        ("payments", "view_mpesatransaction"),
        ("payments", "view_refundrequest"),
        ("payments", "view_returnrequest"),

        ("crm", "view_customernote"),
        ("crm", "add_customernote"),
        ("crm", "change_customernote"),

        ("reviews", "view_review"),
        ("reviews", "change_review"),

        ("notifications", "view_notification"),
        ("notifications", "change_notification"),
    ],


    ORDER_STAFF: [
        ("orders", "view_order"),
        ("orders", "change_order"),
        ("orders", "view_orderitem"),

        ("delivery", "view_delivery"),
        ("delivery", "add_delivery"),
        ("delivery", "change_delivery"),
    ],


    INVENTORY_STAFF: [
        ("products", "view_product"),
        ("products", "add_product"),
        ("products", "change_product"),

        ("products", "view_productvariant"),
        ("products", "add_productvariant"),
        ("products", "change_productvariant"),

        ("products", "view_brand"),

        ("categories", "view_category"),

        ("inventory", "view_inventorymovement"),
        ("inventory", "add_inventorymovement"),
        ("inventory", "change_inventorymovement"),
    ],


    FINANCE_STAFF: [
        ("orders", "view_order"),
        ("orders", "view_orderitem"),

        ("payments", "view_mpesatransaction"),
        ("payments", "change_mpesatransaction"),

        ("payments", "view_refundrequest"),
        ("payments", "change_refundrequest"),

        ("payments", "view_returnrequest"),
        ("payments", "change_returnrequest"),
    ],


    SUPPORT_STAFF: [
        ("orders", "view_order"),
        ("orders", "view_orderitem"),

        ("crm", "view_customernote"),
        ("crm", "add_customernote"),
        ("crm", "change_customernote"),

        ("reviews", "view_review"),
        ("reviews", "change_review"),

        ("notifications", "view_notification"),
        ("notifications", "change_notification"),
    ],
}
'''
)


# ============================================================
# 2. ACCESS CONTROL
# ============================================================

write(
    "accounts/staff_access.py",
r'''from django.contrib import messages
from django.shortcuts import redirect
from django.urls import resolve

from .store_roles import (
    STORE_OWNER,
    STORE_MANAGER,
    ORDER_STAFF,
    INVENTORY_STAFF,
    FINANCE_STAFF,
    SUPPORT_STAFF,
)


ALL_MANAGEMENT_ROLES = {
    STORE_OWNER,
    STORE_MANAGER,
    ORDER_STAFF,
    INVENTORY_STAFF,
    FINANCE_STAFF,
    SUPPORT_STAFF,
}


def user_store_roles(user):
    if not user.is_authenticated:
        return set()

    return set(
        user.groups.values_list(
            "name",
            flat=True,
        )
    )


def is_store_owner(user):

    if not user.is_authenticated:
        return False

    return (
        user.is_superuser
        or STORE_OWNER in user_store_roles(user)
    )


def can_access_store_management(user):

    if not user.is_authenticated:
        return False

    if not user.is_active or not user.is_staff:
        return False

    if user.is_superuser:
        return True

    return bool(
        user_store_roles(user)
        & ALL_MANAGEMENT_ROLES
    )


ROLE_URL_ACCESS = {

    STORE_OWNER: "*",

    STORE_MANAGER: {
        "admin_dashboard",
        "admin_analytics",
        "admin_sales_export",
        "admin_sales_reports",
        "admin_sales_reports_csv",

        "admin_order_list",
        "admin_order_detail",
        "admin_order_invoice",
        "admin_order_receipt",
        "admin_order_document_email",
        "admin_order_update_status",
        "admin_order_update_shipping",

        "admin_product_list",
        "admin_product_create",
        "admin_product_detail",
        "admin_product_edit",
        "admin_product_toggle_active",
        "admin_product_toggle_featured",
        "admin_product_gallery",
        "admin_product_gallery_delete",
        "admin_product_variant_create",
        "admin_product_variant_edit",
        "admin_product_variant_toggle",
        "admin_product_variant_archive",

        "admin_category_list",
        "admin_category_create",
        "admin_category_edit",
        "admin_category_toggle",

        "admin_brand_list",
        "admin_brand_create",
        "admin_brand_edit",
        "admin_brand_toggle",

        "inventory_dashboard",
        "inventory_export_csv",
        "inventory_movement_list",
        "inventory_product_detail",
        "inventory_product_adjust",
        "inventory_variant_adjust",

        "crm_customer_list",
        "crm_customer_export_csv",
        "crm_customer_detail",
        "crm_customer_toggle_status",
        "crm_customer_note_add",
        "crm_customer_note_toggle_pin",
        "crm_customer_note_delete",

        "delivery_list",
        "delivery_detail",
        "delivery_assign",
        "delivery_update_status",
        "delivery_add_attempt",
        "delivery_set_quote",
        "delivery_zone_list",
        "delivery_provider_list",

        "admin_payment_list",
        "admin_payment_detail",

        "admin_returns_refunds",
        "admin_return_detail",
        "admin_refund_detail",

        "admin_notifications",
        "admin_notification_detail",

        "admin_abandoned_cart_list",
        "admin_abandoned_cart_detail",
    },


    ORDER_STAFF: {
        "admin_dashboard",

        "admin_order_list",
        "admin_order_detail",
        "admin_order_invoice",
        "admin_order_receipt",
        "admin_order_document_email",
        "admin_order_update_status",
        "admin_order_update_shipping",

        "delivery_list",
        "delivery_detail",
        "delivery_assign",
        "delivery_update_status",
        "delivery_add_attempt",
        "delivery_set_quote",
    },


    INVENTORY_STAFF: {
        "admin_dashboard",

        "admin_product_list",
        "admin_product_create",
        "admin_product_detail",
        "admin_product_edit",
        "admin_product_toggle_active",
        "admin_product_toggle_featured",
        "admin_product_gallery",
        "admin_product_gallery_delete",
        "admin_product_variant_create",
        "admin_product_variant_edit",
        "admin_product_variant_toggle",
        "admin_product_variant_archive",

        "admin_category_list",
        "admin_category_create",
        "admin_category_edit",
        "admin_category_toggle",

        "admin_brand_list",
        "admin_brand_create",
        "admin_brand_edit",
        "admin_brand_toggle",

        "inventory_dashboard",
        "inventory_export_csv",
        "inventory_movement_list",
        "inventory_product_detail",
        "inventory_product_adjust",
        "inventory_variant_adjust",
    },


    FINANCE_STAFF: {
        "admin_dashboard",
        "admin_analytics",
        "admin_sales_export",
        "admin_sales_reports",
        "admin_sales_reports_csv",

        "admin_order_list",
        "admin_order_detail",
        "admin_order_invoice",
        "admin_order_receipt",

        "admin_payment_list",
        "admin_payment_export_csv",
        "admin_payment_detail",
        "admin_payment_review_resolve",
        "admin_payment_review_reopen",

        "admin_returns_refunds",
        "admin_return_detail",
        "admin_return_review",
        "admin_return_complete",
        "admin_refund_detail",
        "admin_refund_review",
        "admin_refund_process",

        "admin_credit_note",
        "admin_credit_note_email",
    },


    SUPPORT_STAFF: {
        "admin_dashboard",

        "admin_order_list",
        "admin_order_detail",
        "admin_order_invoice",
        "admin_order_receipt",

        "crm_customer_list",
        "crm_customer_detail",
        "crm_customer_note_add",
        "crm_customer_note_toggle_pin",

        "admin_notifications",
        "admin_notification_detail",

        "admin_abandoned_cart_list",
        "admin_abandoned_cart_detail",
    },
}


class StoreStaffPermissionMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        path = request.path

        protected = (
            path.startswith("/dashboard/admin/")
            or path.startswith("/staff/manage/")
        )

        if not protected:
            return self.get_response(request)

        user = request.user

        if not user.is_authenticated:
            return self.get_response(request)

        if not user.is_staff:
            return self.get_response(request)

        if user.is_superuser:
            return self.get_response(request)

        try:
            match = resolve(request.path_info)
            url_name = match.url_name
        except Exception:
            return self.get_response(request)

        roles = user_store_roles(user)

        if path.startswith("/staff/manage/"):

            if STORE_OWNER not in roles:
                messages.error(
                    request,
                    "Only the Store Owner can manage staff accounts.",
                )

                return redirect(
                    "admin_dashboard"
                )

            return self.get_response(request)


        for role in roles:

            allowed = ROLE_URL_ACCESS.get(
                role,
                set(),
            )

            if allowed == "*":
                return self.get_response(request)

            if url_name in allowed:
                return self.get_response(request)


        messages.error(
            request,
            (
                "You do not have permission to access "
                "that management area."
            ),
        )

        return redirect(
            "admin_dashboard"
        )
'''
)


# ============================================================
# 3. STAFF MANAGEMENT FORMS
# ============================================================

write(
    "accounts/staff_forms.py",
r'''from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group

from .store_roles import STORE_ROLE_NAMES


User = get_user_model()


class StoreStaffCreateForm(UserCreationForm):

    email = forms.EmailField(
        required=True,
    )

    first_name = forms.CharField(
        required=True,
    )

    last_name = forms.CharField(
        required=True,
    )

    role_group = forms.ModelChoiceField(
        queryset=Group.objects.none(),
        label="Staff role",
        empty_label=None,
    )


    class Meta:

        model = User

        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "role_group",
            "password1",
            "password2",
        )


    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["role_group"].queryset = (
            Group.objects
            .filter(
                name__in=STORE_ROLE_NAMES
            )
            .order_by("name")
        )

        for field in self.fields.values():

            if isinstance(
                field.widget,
                forms.CheckboxInput,
            ):
                field.widget.attrs["class"] = (
                    "form-check-input"
                )

            else:
                field.widget.attrs["class"] = (
                    "form-control"
                )


    def clean_email(self):

        email = (
            self.cleaned_data["email"]
            .strip()
            .lower()
        )

        if User.objects.filter(
            email__iexact=email
        ).exists():

            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email


    def save(self, commit=True):

        user = super().save(
            commit=False
        )

        user.is_staff = True
        user.is_active = True

        if hasattr(user, "role"):
            user.role = "admin"

        if commit:

            user.save()

            user.groups.clear()

            role_group = (
                self.cleaned_data[
                    "role_group"
                ]
            )

            user.groups.add(
                role_group
            )

        return user



class StoreStaffUpdateForm(forms.ModelForm):

    role_group = forms.ModelChoiceField(
        queryset=Group.objects.none(),
        label="Staff role",
        empty_label=None,
    )


    class Meta:

        model = User

        fields = (
            "first_name",
            "last_name",
            "email",
            "phone",
            "role_group",
            "is_active",
        )


    def __init__(
        self,
        *args,
        **kwargs,
    ):

        super().__init__(
            *args,
            **kwargs,
        )

        self.fields["role_group"].queryset = (
            Group.objects
            .filter(
                name__in=STORE_ROLE_NAMES
            )
            .order_by("name")
        )

        if self.instance.pk:

            current_group = (
                self.instance.groups
                .filter(
                    name__in=STORE_ROLE_NAMES
                )
                .first()
            )

            if current_group:

                self.fields[
                    "role_group"
                ].initial = current_group


        for field in self.fields.values():

            if isinstance(
                field.widget,
                forms.CheckboxInput,
            ):

                field.widget.attrs[
                    "class"
                ] = "form-check-input"

            else:

                field.widget.attrs[
                    "class"
                ] = "form-control"


    def clean_email(self):

        email = (
            self.cleaned_data["email"]
            .strip()
            .lower()
        )

        qs = User.objects.filter(
            email__iexact=email
        ).exclude(
            pk=self.instance.pk
        )

        if qs.exists():

            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email


    def save(self, commit=True):

        user = super().save(
            commit=False
        )

        user.is_staff = True

        if hasattr(user, "role"):
            user.role = "admin"

        if commit:

            user.save()

            user.groups.remove(
                *Group.objects.filter(
                    name__in=STORE_ROLE_NAMES
                )
            )

            user.groups.add(
                self.cleaned_data[
                    "role_group"
                ]
            )

        return user
'''
)


# ============================================================
# 4. OWNER-ONLY STAFF MANAGEMENT VIEWS
# ============================================================

write(
    "accounts/staff_management.py",
r'''from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import require_POST

from .staff_access import is_store_owner
from .staff_forms import (
    StoreStaffCreateForm,
    StoreStaffUpdateForm,
)
from .store_roles import STORE_ROLE_NAMES


User = get_user_model()


def owner_required(view_func):

    return user_passes_test(
        is_store_owner,
        login_url="staff_login",
    )(
        view_func
    )


@owner_required
def staff_list(request):

    staff = (
        User.objects
        .filter(
            is_staff=True,
            is_superuser=False,
        )
        .prefetch_related(
            "groups"
        )
        .order_by(
            "first_name",
            "last_name",
            "username",
        )
    )

    return render(
        request,
        "accounts/staff_management/list.html",
        {
            "staff_members": staff,
            "store_role_names": STORE_ROLE_NAMES,
        },
    )


@owner_required
def staff_create(request):

    if request.method == "POST":

        form = StoreStaffCreateForm(
            request.POST
        )

        if form.is_valid():

            user = form.save()

            messages.success(
                request,
                (
                    f"Staff account "
                    f"{user.username} created."
                ),
            )

            return redirect(
                "staff_manage_list"
            )

    else:

        form = StoreStaffCreateForm()


    return render(
        request,
        "accounts/staff_management/form.html",
        {
            "form": form,
            "title": "Add staff member",
            "submit_label": "Create staff account",
        },
    )


@owner_required
def staff_edit(request, pk):

    user = get_object_or_404(
        User,
        pk=pk,
        is_staff=True,
        is_superuser=False,
    )

    if request.method == "POST":

        form = StoreStaffUpdateForm(
            request.POST,
            instance=user,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                (
                    f"{user.username} "
                    f"was updated."
                ),
            )

            return redirect(
                "staff_manage_list"
            )

    else:

        form = StoreStaffUpdateForm(
            instance=user
        )


    return render(
        request,
        "accounts/staff_management/form.html",
        {
            "form": form,
            "staff_member": user,
            "title": "Edit staff member",
            "submit_label": "Save changes",
        },
    )


@owner_required
@require_POST
def staff_toggle_active(
    request,
    pk,
):

    user = get_object_or_404(
        User,
        pk=pk,
        is_staff=True,
        is_superuser=False,
    )

    if user.pk == request.user.pk:

        messages.error(
            request,
            (
                "You cannot deactivate "
                "your own account."
            ),
        )

        return redirect(
            "staff_manage_list"
        )


    user.is_active = not user.is_active

    user.save(
        update_fields=[
            "is_active"
        ]
    )


    if user.is_active:

        message = (
            f"{user.username} was activated."
        )

    else:

        message = (
            f"{user.username} was deactivated."
        )


    messages.success(
        request,
        message,
    )

    return redirect(
        "staff_manage_list"
    )
'''
)


# ============================================================
# 5. MANAGEMENT URLS
# ============================================================

staff_urls = ROOT / "accounts/staff_urls.py"
backup(staff_urls)

text = staff_urls.read_text(
    encoding="utf-8-sig"
)

if "from . import staff_management" not in text:

    text = text.replace(
        "from .views import StoreStaffLoginView",
        (
            "from .views import StoreStaffLoginView\n"
            "from . import staff_management"
        ),
        1,
    )


if 'name="staff_manage_list"' not in text:

    marker = "]"

    additions = r'''
    path(
        "manage/",
        staff_management.staff_list,
        name="staff_manage_list",
    ),

    path(
        "manage/add/",
        staff_management.staff_create,
        name="staff_manage_create",
    ),

    path(
        "manage/<int:pk>/edit/",
        staff_management.staff_edit,
        name="staff_manage_edit",
    ),

    path(
        "manage/<int:pk>/toggle-active/",
        staff_management.staff_toggle_active,
        name="staff_manage_toggle_active",
    ),
'''

    pos = text.rfind(marker)

    text = (
        text[:pos]
        + additions
        + text[pos:]
    )


staff_urls.write_text(
    text,
    encoding="utf-8",
)

print("[UPDATED] accounts/staff_urls.py")


# ============================================================
# 6. MANAGEMENT COMMAND TO CREATE ROLES
# ============================================================

write(
    "accounts/management/__init__.py",
    "",
)

write(
    "accounts/management/commands/__init__.py",
    "",
)

write(
    "accounts/management/commands/setup_store_roles.py",
r'''from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from accounts.store_roles import (
    ROLE_PERMISSION_MAP,
)


class Command(BaseCommand):

    help = (
        "Create or update store staff "
        "groups and model permissions."
    )


    def handle(
        self,
        *args,
        **options,
    ):

        for group_name, permission_specs in (
            ROLE_PERMISSION_MAP.items()
        ):

            group, created = (
                Group.objects.get_or_create(
                    name=group_name
                )
            )

            permissions = []

            for (
                app_label,
                codename,
            ) in permission_specs:

                permission = (
                    Permission.objects
                    .filter(
                        content_type__app_label=app_label,
                        codename=codename,
                    )
                    .first()
                )

                if permission is None:

                    self.stdout.write(
                        self.style.WARNING(
                            (
                                f"Permission not found: "
                                f"{app_label}.{codename}"
                            )
                        )
                    )

                    continue

                permissions.append(
                    permission
                )


            group.permissions.set(
                permissions
            )

            status = (
                "created"
                if created
                else "updated"
            )

            self.stdout.write(
                self.style.SUCCESS(
                    (
                        f"{group_name}: "
                        f"{status} "
                        f"({len(permissions)} permissions)"
                    )
                )
            )


        self.stdout.write(
            self.style.SUCCESS(
                "Store roles are ready."
            )
        )
'''
)


# ============================================================
# 7. STAFF LIST TEMPLATE
# ============================================================

write(
    "templates/accounts/staff_management/list.html",
r'''{% extends "dashboard/admin/base.html" %}

{% block title %}
Staff Management
{% endblock %}

{% block page_heading %}
Staff Management
{% endblock %}


{% block content %}

<div class="container-fluid py-3">

    <div
        class="d-flex flex-column flex-md-row
               justify-content-between
               align-items-md-center
               gap-3 mb-4"
    >

        <div>

            <h2 class="mb-1">
                Staff Management
            </h2>

            <p class="text-muted mb-0">

                Create staff accounts,
                assign roles and control access.

            </p>

        </div>

        <a
            href="{% url 'staff_manage_create' %}"
            class="btn btn-primary"
        >

            <i class="bi bi-person-plus me-2"></i>

            Add Staff Member

        </a>

    </div>


    <div class="card border-0 shadow-sm">

        <div class="card-body p-0">

            {% if staff_members %}

                <div class="table-responsive">

                    <table
                        class="table align-middle mb-0"
                    >

                        <thead class="table-light">

                            <tr>

                                <th>
                                    Staff Member
                                </th>

                                <th>
                                    Role
                                </th>

                                <th>
                                    Status
                                </th>

                                <th>
                                    Last Login
                                </th>

                                <th class="text-end">
                                    Actions
                                </th>

                            </tr>

                        </thead>


                        <tbody>

                            {% for staff in staff_members %}

                                <tr>

                                    <td>

                                        <strong>

                                            {{ staff.get_full_name|default:staff.username }}

                                        </strong>

                                        <small
                                            class="d-block text-muted"
                                        >

                                            {{ staff.email }}

                                        </small>

                                        <small
                                            class="d-block text-muted"
                                        >

                                            @{{ staff.username }}

                                        </small>

                                    </td>


                                    <td>

                                        {% for group in staff.groups.all %}

                                            {% if group.name in store_role_names %}

                                                <span
                                                    class="badge
                                                           text-bg-primary"
                                                >

                                                    {{ group.name }}

                                                </span>

                                            {% endif %}

                                        {% empty %}

                                            <span
                                                class="badge
                                                       text-bg-warning"
                                            >
                                                No role
                                            </span>

                                        {% endfor %}

                                    </td>


                                    <td>

                                        {% if staff.is_active %}

                                            <span
                                                class="badge bg-success"
                                            >
                                                Active
                                            </span>

                                        {% else %}

                                            <span
                                                class="badge bg-secondary"
                                            >
                                                Disabled
                                            </span>

                                        {% endif %}

                                    </td>


                                    <td>

                                        {% if staff.last_login %}

                                            {{ staff.last_login|date:"d M Y H:i" }}

                                        {% else %}

                                            <span class="text-muted">
                                                Never
                                            </span>

                                        {% endif %}

                                    </td>


                                    <td class="text-end">

                                        <a
                                            href="{% url 'staff_manage_edit' staff.pk %}"
                                            class="btn
                                                   btn-outline-primary
                                                   btn-sm"
                                        >
                                            Edit
                                        </a>


                                        <form
                                            method="post"
                                            action="{% url 'staff_manage_toggle_active' staff.pk %}"
                                            class="d-inline"
                                        >

                                            {% csrf_token %}

                                            {% if staff.is_active %}

                                                <button
                                                    type="submit"
                                                    class="btn
                                                           btn-outline-danger
                                                           btn-sm"
                                                >
                                                    Disable
                                                </button>

                                            {% else %}

                                                <button
                                                    type="submit"
                                                    class="btn
                                                           btn-outline-success
                                                           btn-sm"
                                                >
                                                    Activate
                                                </button>

                                            {% endif %}

                                        </form>

                                    </td>

                                </tr>

                            {% endfor %}

                        </tbody>

                    </table>

                </div>

            {% else %}

                <div class="text-center py-5">

                    <i
                        class="bi bi-people fs-1 text-muted"
                    ></i>

                    <h5 class="mt-3">
                        No staff accounts yet
                    </h5>

                    <p class="text-muted">
                        Create your first store
                        staff account.
                    </p>

                    <a
                        href="{% url 'staff_manage_create' %}"
                        class="btn btn-primary"
                    >
                        Add Staff Member
                    </a>

                </div>

            {% endif %}

        </div>

    </div>

</div>

{% endblock %}
'''
)


# ============================================================
# 8. STAFF FORM TEMPLATE
# ============================================================

write(
    "templates/accounts/staff_management/form.html",
r'''{% extends "dashboard/admin/base.html" %}

{% block title %}
{{ title }}
{% endblock %}

{% block page_heading %}
{{ title }}
{% endblock %}


{% block content %}

<div class="container-fluid py-3">

    <div class="row justify-content-center">

        <div class="col-xl-7 col-lg-8">

            <div
                class="card border-0 shadow-sm"
            >

                <div class="card-body p-4">

                    <div class="mb-4">

                        <h3 class="mb-1">
                            {{ title }}
                        </h3>

                        <p class="text-muted mb-0">

                            Staff permissions are controlled
                            by the selected role.

                        </p>

                    </div>


                    <form method="post">

                        {% csrf_token %}


                        {% if form.non_field_errors %}

                            <div
                                class="alert alert-danger"
                            >

                                {{ form.non_field_errors }}

                            </div>

                        {% endif %}


                        {% for field in form %}

                            <div class="mb-3">

                                {% if field.field.widget.input_type == "checkbox" %}

                                    <div class="form-check">

                                        {{ field }}

                                        <label
                                            class="form-check-label"
                                            for="{{ field.id_for_label }}"
                                        >

                                            {{ field.label }}

                                        </label>

                                    </div>

                                {% else %}

                                    <label
                                        class="form-label"
                                        for="{{ field.id_for_label }}"
                                    >

                                        {{ field.label }}

                                    </label>

                                    {{ field }}

                                {% endif %}


                                {% if field.help_text %}

                                    <div
                                        class="form-text"
                                    >
                                        {{ field.help_text|safe }}
                                    </div>

                                {% endif %}


                                {% for error in field.errors %}

                                    <div
                                        class="text-danger small mt-1"
                                    >
                                        {{ error }}
                                    </div>

                                {% endfor %}

                            </div>

                        {% endfor %}


                        <div
                            class="d-flex gap-2 mt-4"
                        >

                            <button
                                type="submit"
                                class="btn btn-primary"
                            >

                                {{ submit_label }}

                            </button>


                            <a
                                href="{% url 'staff_manage_list' %}"
                                class="btn btn-outline-secondary"
                            >

                                Cancel

                            </a>

                        </div>

                    </form>

                </div>

            </div>

        </div>

    </div>

</div>

{% endblock %}
'''
)


# ============================================================
# 9. TEMPLATE FILTER FOR OWNER SIDEBAR
# ============================================================

write(
    "accounts/templatetags/__init__.py",
    "",
)

write(
    "accounts/templatetags/store_permissions.py",
r'''from django import template

from accounts.staff_access import (
    is_store_owner,
)


register = template.Library()


@register.filter
def store_owner(user):

    return is_store_owner(user)
'''
)


# ============================================================
# 10. ADD STAFF MENU TO ADMIN SIDEBAR
# ============================================================

admin_base = (
    ROOT
    / "templates/dashboard/admin/base.html"
)

backup(admin_base)

text = admin_base.read_text(
    encoding="utf-8-sig"
)


if "{% load store_permissions %}" not in text:

    text = text.replace(
        "{% load static %}",
        (
            "{% load static %}\n"
            "{% load store_permissions %}"
        ),
        1,
    )


if "staff_manage_list" not in text:

    marker = '''            <!-- SETTINGS -->'''

    staff_menu = r'''
            {% if request.user|store_owner %}

            <!-- STAFF MANAGEMENT -->

            <a
                href="{% url 'staff_manage_list' %}"
                class="
                    sidebar-link
                    {% if 'staff_manage' in request.resolver_match.url_name %}
                        active
                    {% endif %}
                "
            >

                <i class="bi bi-person-gear"></i>

                <span>
                    Staff
                </span>

            </a>

            {% endif %}


'''

    if marker not in text:
        raise RuntimeError(
            "Could not locate sidebar Settings marker."
        )

    text = text.replace(
        marker,
        staff_menu + marker,
        1,
    )


admin_base.write_text(
    text,
    encoding="utf-8",
)

print(
    "[UPDATED] templates/dashboard/admin/base.html"
)


# ============================================================
# 11. ADD MIDDLEWARE
# ============================================================

settings_file = ROOT / "config/settings.py"
backup(settings_file)

text = settings_file.read_text(
    encoding="utf-8-sig"
)


middleware_line = (
    "'accounts.staff_access."
    "StoreStaffPermissionMiddleware',"
)


if middleware_line not in text:

    anchor = (
        "'django.contrib.messages.middleware."
        "MessageMiddleware',"
    )

    if anchor not in text:
        raise RuntimeError(
            "Could not locate MessageMiddleware."
        )

    text = text.replace(
        anchor,
        (
            anchor
            + "\n    "
            + middleware_line
        ),
        1,
    )


settings_file.write_text(
    text,
    encoding="utf-8",
)

print("[UPDATED] config/settings.py")


# ============================================================
# 12. STAFF LOGIN SHOULD REQUIRE AN ACTUAL STORE ROLE
# ============================================================

views_file = ROOT / "accounts/views.py"
backup(views_file)

text = views_file.read_text(
    encoding="utf-8-sig"
)


if "can_access_store_management" not in text:

    import_anchor = (
        "from django.views.decorators.http "
        "import require_POST"
    )

    if import_anchor in text:

        text = text.replace(
            import_anchor,
            (
                import_anchor
                + "\n"
                + "from .staff_access import "
                + "can_access_store_management"
            ),
            1,
        )

    else:

        # safe fallback near top
        text = (
            "from .staff_access import "
            "can_access_store_management\n"
            + text
        )


old = '''        if not user.is_staff:

            form.add_error(
                None,
                (
                    "This login is only for "
                    "the store owner and "
                    "authorized staff."
                ),
            )

            return self.form_invalid(form)
'''

new = '''        if not can_access_store_management(user):

            form.add_error(
                None,
                (
                    "Your account does not have "
                    "an authorized store staff role."
                ),
            )

            return self.form_invalid(form)
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif (
    "can_access_store_management(user)"
    in text
):

    print(
        "[OK] Staff login already validates store roles."
    )

else:

    print(
        "[NOTICE] Staff login condition formatting differed."
    )
    print(
        "Middleware still protects management areas."
    )


views_file.write_text(
    text,
    encoding="utf-8",
)

print("[UPDATED] accounts/views.py")


# ============================================================
# 13. TESTS
# ============================================================

write(
    "accounts/test_staff_management.py",
r'''from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.store_roles import (
    STORE_OWNER,
    ORDER_STAFF,
    INVENTORY_STAFF,
    FINANCE_STAFF,
    SUPPORT_STAFF,
)


User = get_user_model()


class StaffManagementTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        call_command(
            "setup_store_roles"
        )

        cls.owner = (
            User.objects.create_user(
                username="owner",
                email="owner@example.com",
                password="StrongPass123!",
                is_staff=True,
                is_active=True,
            )
        )

        cls.owner.groups.add(
            Group.objects.get(
                name=STORE_OWNER
            )
        )


        cls.order_staff = (
            User.objects.create_user(
                username="orders",
                email="orders@example.com",
                password="StrongPass123!",
                is_staff=True,
                is_active=True,
            )
        )

        cls.order_staff.groups.add(
            Group.objects.get(
                name=ORDER_STAFF
            )
        )


        cls.customer = (
            User.objects.create_user(
                username="customer",
                email="customer@example.com",
                password="StrongPass123!",
                is_staff=False,
                is_active=True,
            )
        )


    def test_owner_can_view_staff_management(self):

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            reverse(
                "staff_manage_list"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Staff Management",
        )


    def test_regular_staff_cannot_manage_staff(self):

        self.client.force_login(
            self.order_staff
        )

        response = self.client.get(
            reverse(
                "staff_manage_list"
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "admin_dashboard"
            ),
        )


    def test_customer_cannot_manage_staff(self):

        self.client.force_login(
            self.customer
        )

        response = self.client.get(
            reverse(
                "staff_manage_list"
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )


    def test_owner_can_create_inventory_staff(self):

        self.client.force_login(
            self.owner
        )

        role = Group.objects.get(
            name=INVENTORY_STAFF
        )

        response = self.client.post(
            reverse(
                "staff_manage_create"
            ),
            {
                "username": "inventoryuser",
                "first_name": "Inventory",
                "last_name": "User",
                "email": "inventory@example.com",
                "phone": "0712345678",
                "role_group": role.pk,
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        created = User.objects.get(
            username="inventoryuser"
        )

        self.assertTrue(
            created.is_staff
        )

        self.assertTrue(
            created.groups.filter(
                name=INVENTORY_STAFF
            ).exists()
        )


    def test_staff_toggle_requires_post(self):

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            reverse(
                "staff_manage_toggle_active",
                args=[
                    self.order_staff.pk
                ],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )


    def test_owner_can_disable_staff(self):

        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            reverse(
                "staff_manage_toggle_active",
                args=[
                    self.order_staff.pk
                ],
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "staff_manage_list"
            ),
        )

        self.order_staff.refresh_from_db()

        self.assertFalse(
            self.order_staff.is_active
        )


class StoreRoleCreationTests(TestCase):

    def test_setup_command_creates_all_roles(self):

        call_command(
            "setup_store_roles"
        )

        for role_name in [
            STORE_OWNER,
            ORDER_STAFF,
            INVENTORY_STAFF,
            FINANCE_STAFF,
            SUPPORT_STAFF,
        ]:

            self.assertTrue(
                Group.objects.filter(
                    name=role_name
                ).exists()
            )
'''
)


# ============================================================
# 14. RUN SETUP + VALIDATION
# ============================================================

commands = [

    [
        sys.executable,
        "manage.py",
        "check",
    ],

    [
        sys.executable,
        "manage.py",
        "makemigrations",
        "--check",
        "--dry-run",
    ],

    [
        sys.executable,
        "manage.py",
        "setup_store_roles",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "accounts.test_staff_management",
        "-v",
        "2",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "accounts",
        "-v",
        "1",
    ],
]


print()
print("=" * 76)
print("VALIDATING STAFF MANAGEMENT")
print("=" * 76)


for command in commands:

    print()
    print(
        ">",
        " ".join(command),
    )

    result = subprocess.run(
        command,
        cwd=ROOT,
    )

    if result.returncode != 0:

        print()
        print("=" * 76)
        print("VALIDATION FAILED")
        print("=" * 76)

        print()
        print(
            "Backup directory:"
        )
        print(BACKUP)

        raise SystemExit(
            result.returncode
        )


print()
print("=" * 76)
print("STAFF MANAGEMENT CREATED")
print("=" * 76)

print()
print("Roles:")
print("  Store Owner")
print("  Store Manager")
print("  Orders Staff")
print("  Inventory Staff")
print("  Finance Staff")
print("  Support Staff")

print()
print("Management URL:")
print("  /staff/manage/")

print()
print(
    "Only Store Owner or superuser "
    "can manage staff accounts."
)

print()
print(
    "Normal staff access is limited "
    "to assigned management areas."
)

print()
print("Backup:")
print(BACKUP)

