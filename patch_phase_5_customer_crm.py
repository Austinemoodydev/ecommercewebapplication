from pathlib import Path
import re
import shutil


ROOT = Path.cwd()

settings_path = ROOT / "config" / "settings.py"
config_urls = ROOT / "config" / "urls.py"

models_path = ROOT / "crm" / "models.py"
forms_path = ROOT / "crm" / "forms.py"
views_path = ROOT / "crm" / "views.py"
urls_path = ROOT / "crm" / "urls.py"
admin_path = ROOT / "crm" / "admin.py"
tests_path = ROOT / "crm" / "tests.py"

base_template = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "base.html"
)

template_dir = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "customers"
)

list_template = (
    template_dir / "list.html"
)

detail_template = (
    template_dir / "detail.html"
)


def backup(path):

    if path.exists():

        target = Path(
            str(path)
            + ".phase5backup"
        )

        shutil.copy2(
            path,
            target,
        )

        print(
            f"Backup: {target}"
        )


for path in [
    settings_path,
    config_urls,
    base_template,
]:
    backup(path)


# ============================================================
# 1. INSTALLED APPS
# ============================================================

text = settings_path.read_text(
    encoding="utf-8-sig"
)

if (
    '"crm"' not in text
    and "'crm'" not in text
):

    candidates = [
        "'inventory',",
        '"inventory",',
        "'accounts',",
        '"accounts",',
    ]

    inserted = False

    for marker in candidates:

        if marker in text:

            quote = (
                "'"
                if marker.startswith("'")
                else '"'
            )

            text = text.replace(
                marker,
                (
                    marker
                    + "\n    "
                    + quote
                    + "crm"
                    + quote
                    + ","
                ),
                1,
            )

            inserted = True
            break

    if not inserted:

        raise RuntimeError(
            (
                "Could not find a suitable "
                "INSTALLED_APPS insertion point."
            )
        )

    settings_path.write_text(
        text,
        encoding="utf-8",
    )

    print(
        "Added crm to INSTALLED_APPS"
    )

else:

    print(
        "crm already in INSTALLED_APPS"
    )


# ============================================================
# 2. CUSTOMER NOTE MODEL
# ============================================================

models_path.write_text(
r'''
from django.conf import settings
from django.db import models


class CustomerNote(models.Model):

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="crm_notes",
    )

    note = models.TextField()

    is_pinned = models.BooleanField(
        default=False,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_customer_notes",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        ordering = [
            "-is_pinned",
            "-created_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "customer",
                    "created_at",
                ]
            ),
        ]

    def __str__(self):

        return (
            f"Note for "
            f"{self.customer}"
        )
'''.strip() + "\n",
    encoding="utf-8",
)

print(
    "Created crm/models.py"
)


# ============================================================
# 3. CRM FORMS
# ============================================================

forms_path.write_text(
r'''
from django import forms

from .models import CustomerNote


class CustomerNoteForm(
    forms.ModelForm
):

    class Meta:

        model = CustomerNote

        fields = [
            "note",
            "is_pinned",
        ]

        widgets = {

            "note": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Add an internal "
                        "customer note..."
                    ),
                }
            ),

            "is_pinned": (
                forms.CheckboxInput(
                    attrs={
                        "class": (
                            "form-check-input"
                        ),
                    }
                )
            ),
        }

    def clean_note(self):

        note = (
            self.cleaned_data[
                "note"
            ].strip()
        )

        if len(note) < 2:

            raise forms.ValidationError(
                (
                    "Please enter a "
                    "meaningful note."
                )
            )

        return note
'''.strip() + "\n",
    encoding="utf-8",
)

print(
    "Created crm/forms.py"
)


# ============================================================
# 4. CRM VIEWS
# ============================================================

views_path.write_text(
r'''
import csv

from decimal import Decimal

from django.contrib import messages

from django.contrib.admin.views.decorators import (
    staff_member_required,
)

from django.contrib.auth import (
    get_user_model,
)

from django.core.paginator import (
    Paginator,
)

from django.db.models import (
    Count,
    DecimalField,
    Max,
    Q,
    Sum,
    Value,
)

from django.db.models.functions import (
    Coalesce,
)

from django.http import (
    HttpResponse,
)

from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from orders.models import Order

from .forms import CustomerNoteForm

from .models import CustomerNote


User = get_user_model()


def customer_queryset():

    return (
        User.objects
        .filter(
            role=User.CUSTOMER
        )
        .annotate(

            total_orders=Count(
                "orders",
                distinct=True,
            ),

            paid_orders=Count(
                "orders",
                filter=Q(
                    orders__payment_status=(
                        "paid"
                    )
                ),
                distinct=True,
            ),

            lifetime_spend=Coalesce(
                Sum(
                    "orders__total_amount",
                    filter=Q(
                        orders__payment_status=(
                            "paid"
                        )
                    ),
                ),
                Value(
                    Decimal("0.00")
                ),
                output_field=DecimalField(
                    max_digits=14,
                    decimal_places=2,
                ),
            ),

            last_order_at=Max(
                "orders__created_at"
            ),
        )
    )


# ============================================================
# CUSTOMER LIST
# ============================================================

@staff_member_required
def customer_list(request):

    customers = (
        customer_queryset()
        .order_by(
            "-date_joined"
        )
    )

    query = request.GET.get(
        "q",
        "",
    ).strip()

    status = request.GET.get(
        "status",
        "",
    )

    order_status = request.GET.get(
        "orders",
        "",
    )

    if query:

        customers = (
            customers.filter(
                Q(
                    username__icontains=query
                )
                | Q(
                    first_name__icontains=query
                )
                | Q(
                    last_name__icontains=query
                )
                | Q(
                    email__icontains=query
                )
                | Q(
                    phone__icontains=query
                )
            )
        )

    if status == "active":

        customers = customers.filter(
            is_active=True
        )

    elif status == "inactive":

        customers = customers.filter(
            is_active=False
        )

    elif status == "verified":

        customers = customers.filter(
            email_verified=True
        )

    elif status == "unverified":

        customers = customers.filter(
            email_verified=False
        )

    if order_status == "with_orders":

        customers = customers.filter(
            total_orders__gt=0
        )

    elif order_status == "no_orders":

        customers = customers.filter(
            total_orders=0
        )

    elif order_status == "buyers":

        customers = customers.filter(
            paid_orders__gt=0
        )

    total_customers = (
        User.objects
        .filter(
            role=User.CUSTOMER
        )
        .count()
    )

    active_customers = (
        User.objects
        .filter(
            role=User.CUSTOMER,
            is_active=True,
        )
        .count()
    )

    customers_with_orders = (
        User.objects
        .filter(
            role=User.CUSTOMER,
            orders__isnull=False,
        )
        .distinct()
        .count()
    )

    paying_customers = (
        User.objects
        .filter(
            role=User.CUSTOMER,
            orders__payment_status="paid",
        )
        .distinct()
        .count()
    )

    paginator = Paginator(
        customers,
        25,
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        (
            "dashboard/admin/"
            "customers/list.html"
        ),
        {
            "customers": (
                page_obj.object_list
            ),
            "page_obj": page_obj,
            "query": query,
            "selected_status": status,
            "selected_orders": (
                order_status
            ),
            "total_customers": (
                total_customers
            ),
            "active_customers": (
                active_customers
            ),
            "customers_with_orders": (
                customers_with_orders
            ),
            "paying_customers": (
                paying_customers
            ),
        },
    )


# ============================================================
# CUSTOMER DETAIL
# ============================================================

@staff_member_required
def customer_detail(
    request,
    pk,
):

    customer = get_object_or_404(
        User,
        pk=pk,
        role=User.CUSTOMER,
    )

    orders = (
        customer.orders
        .select_related(
            "coupon"
        )
        .prefetch_related(
            "items"
        )
        .order_by(
            "-created_at"
        )
    )

    paid_orders = orders.filter(
        payment_status="paid"
    )

    lifetime_spend = (
        paid_orders.aggregate(
            total=Sum(
                "total_amount"
            )
        )["total"]
        or Decimal("0.00")
    )

    total_orders = orders.count()

    paid_order_count = (
        paid_orders.count()
    )

    last_order = (
        orders.first()
    )

    addresses = (
        customer.addresses
        .order_by(
            "-is_default",
            "id",
        )
    )

    notes = (
        CustomerNote.objects
        .filter(
            customer=customer
        )
        .select_related(
            "created_by"
        )
    )

    note_form = (
        CustomerNoteForm()
    )

    paginator = Paginator(
        orders,
        15,
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        (
            "dashboard/admin/"
            "customers/detail.html"
        ),
        {
            "customer": customer,
            "orders": (
                page_obj.object_list
            ),
            "page_obj": page_obj,
            "addresses": addresses,
            "notes": notes,
            "note_form": note_form,
            "lifetime_spend": (
                lifetime_spend
            ),
            "total_orders": (
                total_orders
            ),
            "paid_order_count": (
                paid_order_count
            ),
            "last_order": last_order,
        },
    )


# ============================================================
# ADD INTERNAL NOTE
# ============================================================

@staff_member_required
def customer_note_add(
    request,
    pk,
):

    customer = get_object_or_404(
        User,
        pk=pk,
        role=User.CUSTOMER,
    )

    if request.method != "POST":

        return redirect(
            "crm_customer_detail",
            pk=customer.pk,
        )

    form = CustomerNoteForm(
        request.POST
    )

    if form.is_valid():

        note = form.save(
            commit=False
        )

        note.customer = customer
        note.created_by = (
            request.user
        )

        note.save()

        messages.success(
            request,
            "Customer note added.",
        )

    else:

        messages.error(
            request,
            (
                "The customer note "
                "could not be saved."
            ),
        )

    return redirect(
        "crm_customer_detail",
        pk=customer.pk,
    )


# ============================================================
# PIN / UNPIN NOTE
# ============================================================

@staff_member_required
def customer_note_toggle_pin(
    request,
    pk,
    note_id,
):

    customer = get_object_or_404(
        User,
        pk=pk,
        role=User.CUSTOMER,
    )

    note = get_object_or_404(
        CustomerNote,
        pk=note_id,
        customer=customer,
    )

    if request.method == "POST":

        note.is_pinned = (
            not note.is_pinned
        )

        note.save(
            update_fields=[
                "is_pinned",
                "updated_at",
            ]
        )

        messages.success(
            request,
            (
                "Note pinned."
                if note.is_pinned
                else "Note unpinned."
            ),
        )

    return redirect(
        "crm_customer_detail",
        pk=customer.pk,
    )


# ============================================================
# DELETE NOTE
# ============================================================

@staff_member_required
def customer_note_delete(
    request,
    pk,
    note_id,
):

    customer = get_object_or_404(
        User,
        pk=pk,
        role=User.CUSTOMER,
    )

    note = get_object_or_404(
        CustomerNote,
        pk=note_id,
        customer=customer,
    )

    if request.method == "POST":

        note.delete()

        messages.success(
            request,
            "Customer note deleted.",
        )

    return redirect(
        "crm_customer_detail",
        pk=customer.pk,
    )


# ============================================================
# ACTIVATE / DEACTIVATE CUSTOMER
# ============================================================

@staff_member_required
def customer_toggle_status(
    request,
    pk,
):

    customer = get_object_or_404(
        User,
        pk=pk,
        role=User.CUSTOMER,
    )

    if request.method != "POST":

        return redirect(
            "crm_customer_detail",
            pk=customer.pk,
        )

    customer.is_active = (
        not customer.is_active
    )

    customer.save(
        update_fields=[
            "is_active"
        ]
    )

    messages.success(
        request,
        (
            f'Customer "{customer.username}" '
            f'is now '
            f'{"active" if customer.is_active else "inactive"}.'
        ),
    )

    return redirect(
        "crm_customer_detail",
        pk=customer.pk,
    )


# ============================================================
# CUSTOMER CSV EXPORT
# ============================================================

@staff_member_required
def customer_export_csv(
    request,
):

    response = HttpResponse(
        content_type=(
            "text/csv; charset=utf-8"
        ),
    )

    response[
        "Content-Disposition"
    ] = (
        'attachment; '
        'filename="customers.csv"'
    )

    response.write(
        "\ufeff"
    )

    writer = csv.writer(
        response
    )

    writer.writerow([
        "Username",
        "First Name",
        "Last Name",
        "Email",
        "Phone",
        "Status",
        "Email Verified",
        "Total Orders",
        "Paid Orders",
        "Lifetime Spend",
        "Joined",
        "Last Order",
    ])

    customers = (
        customer_queryset()
        .order_by(
            "-date_joined"
        )
    )

    for customer in customers:

        writer.writerow([
            customer.username,
            customer.first_name,
            customer.last_name,
            customer.email,
            customer.phone,
            (
                "Active"
                if customer.is_active
                else "Inactive"
            ),
            (
                "Yes"
                if customer.email_verified
                else "No"
            ),
            customer.total_orders,
            customer.paid_orders,
            customer.lifetime_spend,
            customer.date_joined,
            (
                customer.last_order_at
                or ""
            ),
        ])

    return response
'''.strip() + "\n",
    encoding="utf-8",
)

print(
    "Created crm/views.py"
)


# ============================================================
# 5. CRM URLS
# ============================================================

urls_path.write_text(
r'''
from django.urls import path

from . import views


urlpatterns = [

    path(
        "",
        views.customer_list,
        name="crm_customer_list",
    ),

    path(
        "export/",
        views.customer_export_csv,
        name="crm_customer_export_csv",
    ),

    path(
        "<int:pk>/",
        views.customer_detail,
        name="crm_customer_detail",
    ),

    path(
        "<int:pk>/status/",
        views.customer_toggle_status,
        name="crm_customer_toggle_status",
    ),

    path(
        "<int:pk>/notes/add/",
        views.customer_note_add,
        name="crm_customer_note_add",
    ),

    path(
        (
            "<int:pk>/notes/"
            "<int:note_id>/pin/"
        ),
        views.customer_note_toggle_pin,
        name="crm_customer_note_toggle_pin",
    ),

    path(
        (
            "<int:pk>/notes/"
            "<int:note_id>/delete/"
        ),
        views.customer_note_delete,
        name="crm_customer_note_delete",
    ),
]
'''.strip() + "\n",
    encoding="utf-8",
)

print(
    "Created crm/urls.py"
)


# ============================================================
# 6. DJANGO ADMIN
# ============================================================

admin_path.write_text(
r'''
from django.contrib import admin

from .models import CustomerNote


@admin.register(CustomerNote)
class CustomerNoteAdmin(
    admin.ModelAdmin
):

    list_display = [
        "customer",
        "created_by",
        "is_pinned",
        "created_at",
    ]

    list_filter = [
        "is_pinned",
        "created_at",
    ]

    search_fields = [
        "customer__username",
        "customer__email",
        "customer__phone",
        "note",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]
'''.strip() + "\n",
    encoding="utf-8",
)

print(
    "Created crm/admin.py"
)


# ============================================================
# 7. CONNECT ROOT URLS
# ============================================================

text = config_urls.read_text(
    encoding="utf-8-sig"
)

if (
    'include("crm.urls")'
    not in text
):

    if (
        "from django.urls import path"
        in text
    ):

        text = text.replace(
            "from django.urls import path",
            (
                "from django.urls "
                "import include, path"
            ),
            1,
        )

    marker = "urlpatterns = ["

    if marker not in text:

        raise RuntimeError(
            (
                "Could not locate "
                "urlpatterns."
            )
        )

    route = r'''
    path(
        "dashboard/admin/customers/",
        include("crm.urls"),
    ),
'''

    text = text.replace(
        marker,
        marker + route,
        1,
    )

    config_urls.write_text(
        text,
        encoding="utf-8",
    )

    print(
        "Connected CRM URLs"
    )

else:

    print(
        "CRM URLs already connected"
    )


# ============================================================
# 8. CUSTOMER LIST TEMPLATE
# ============================================================

template_dir.mkdir(
    parents=True,
    exist_ok=True,
)


list_template.write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Customers | Store Management
{% endblock %}

{% block page_heading %}
Customers
{% endblock %}

{% block admin_content %}

<div class="d-flex justify-content-between align-items-center flex-wrap gap-3 mb-4">

    <div>

        <h1 class="h3 mb-1">
            Customer Management
        </h1>

        <p class="text-muted mb-0">
            Customer accounts, order history
            and lifetime value.
        </p>

    </div>

    <a
        href="{% url 'crm_customer_export_csv' %}"
        class="btn btn-outline-success"
    >
        <i class="bi bi-file-earmark-spreadsheet"></i>
        Export Customers
    </a>

</div>


<div class="row g-3 mb-4">

    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card mini-stat">

            <span>
                Customers
            </span>

            <strong>
                {{ total_customers }}
            </strong>

        </div>

    </div>


    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card mini-stat">

            <span>
                Active Accounts
            </span>

            <strong>
                {{ active_customers }}
            </strong>

        </div>

    </div>


    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card mini-stat">

            <span>
                With Orders
            </span>

            <strong>
                {{ customers_with_orders }}
            </strong>

        </div>

    </div>


    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card mini-stat">

            <span>
                Paying Customers
            </span>

            <strong>
                {{ paying_customers }}
            </strong>

        </div>

    </div>

</div>


<div class="dashboard-card mb-4">

    <form method="GET">

        <div class="row g-3">

            <div class="col-lg-6">

                <label class="form-label">
                    Search
                </label>

                <input
                    type="text"
                    name="q"
                    value="{{ query }}"
                    class="form-control"
                    placeholder="Name, username, email or phone..."
                >

            </div>


            <div class="col-lg-3">

                <label class="form-label">
                    Account
                </label>

                <select
                    name="status"
                    class="form-select"
                >

                    <option value="">
                        All Accounts
                    </option>

                    <option
                        value="active"
                        {% if selected_status == "active" %}
                            selected
                        {% endif %}
                    >
                        Active
                    </option>

                    <option
                        value="inactive"
                        {% if selected_status == "inactive" %}
                            selected
                        {% endif %}
                    >
                        Inactive
                    </option>

                    <option
                        value="verified"
                        {% if selected_status == "verified" %}
                            selected
                        {% endif %}
                    >
                        Email Verified
                    </option>

                    <option
                        value="unverified"
                        {% if selected_status == "unverified" %}
                            selected
                        {% endif %}
                    >
                        Email Unverified
                    </option>

                </select>

            </div>


            <div class="col-lg-3">

                <label class="form-label">
                    Purchase History
                </label>

                <select
                    name="orders"
                    class="form-select"
                >

                    <option value="">
                        All Customers
                    </option>

                    <option
                        value="with_orders"
                        {% if selected_orders == "with_orders" %}
                            selected
                        {% endif %}
                    >
                        Has Orders
                    </option>

                    <option
                        value="buyers"
                        {% if selected_orders == "buyers" %}
                            selected
                        {% endif %}
                    >
                        Paying Customers
                    </option>

                    <option
                        value="no_orders"
                        {% if selected_orders == "no_orders" %}
                            selected
                        {% endif %}
                    >
                        No Orders
                    </option>

                </select>

            </div>

        </div>


        <div class="mt-3">

            <button
                type="submit"
                class="btn btn-primary"
            >
                Filter
            </button>

            <a
                href="{% url 'crm_customer_list' %}"
                class="btn btn-outline-secondary"
            >
                Reset
            </a>

        </div>

    </form>

</div>


<div class="dashboard-card">

    <div class="table-responsive">

        <table class="table align-middle">

            <thead>

                <tr>
                    <th>Customer</th>
                    <th>Phone</th>
                    <th>Status</th>
                    <th>Orders</th>
                    <th>Paid</th>
                    <th>Lifetime Spend</th>
                    <th>Last Order</th>
                    <th></th>
                </tr>

            </thead>

            <tbody>

                {% for customer in customers %}

                    <tr>

                        <td>

                            <div class="d-flex align-items-center gap-3">

                                {% if customer.avatar %}

                                    <img
                                        src="{{ customer.avatar.url }}"
                                        width="42"
                                        height="42"
                                        class="rounded-circle"
                                        style="object-fit:cover;"
                                        alt=""
                                    >

                                {% else %}

                                    <div
                                        class="rounded-circle bg-body-secondary d-flex align-items-center justify-content-center"
                                        style="width:42px;height:42px;"
                                    >
                                        <i class="bi bi-person"></i>
                                    </div>

                                {% endif %}

                                <div>

                                    <strong>

                                        {% if customer.get_full_name %}

                                            {{ customer.get_full_name }}

                                        {% else %}

                                            {{ customer.username }}

                                        {% endif %}

                                    </strong>

                                    <small class="text-muted d-block">
                                        {{ customer.email|default:"No email" }}
                                    </small>

                                </div>

                            </div>

                        </td>


                        <td>
                            {{ customer.phone|default:"—" }}
                        </td>


                        <td>

                            {% if customer.is_active %}

                                <span class="badge text-bg-success">
                                    Active
                                </span>

                            {% else %}

                                <span class="badge text-bg-secondary">
                                    Inactive
                                </span>

                            {% endif %}

                            {% if customer.email_verified %}

                                <span class="badge text-bg-primary">
                                    Verified
                                </span>

                            {% endif %}

                        </td>


                        <td>
                            {{ customer.total_orders }}
                        </td>


                        <td>
                            {{ customer.paid_orders }}
                        </td>


                        <td>
                            KES {{ customer.lifetime_spend|floatformat:2 }}
                        </td>


                        <td>

                            {% if customer.last_order_at %}

                                {{ customer.last_order_at|date:"d M Y" }}

                            {% else %}

                                Never

                            {% endif %}

                        </td>


                        <td>

                            <a
                                href="{% url 'crm_customer_detail' customer.pk %}"
                                class="btn btn-sm btn-outline-primary"
                            >
                                View
                            </a>

                        </td>

                    </tr>

                {% empty %}

                    <tr>

                        <td
                            colspan="8"
                            class="text-center text-muted py-5"
                        >
                            No customers found.
                        </td>

                    </tr>

                {% endfor %}

            </tbody>

        </table>

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
    encoding="utf-8",
)

print(
    "Created customer list template"
)


# ============================================================
# 9. CUSTOMER DETAIL TEMPLATE
# ============================================================

detail_template.write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Customer | {{ customer.username }}
{% endblock %}

{% block page_heading %}
Customer Profile
{% endblock %}

{% block admin_content %}

<div class="d-flex justify-content-between align-items-center flex-wrap gap-3 mb-4">

    <div class="d-flex align-items-center gap-3">

        {% if customer.avatar %}

            <img
                src="{{ customer.avatar.url }}"
                width="70"
                height="70"
                class="rounded-circle"
                style="object-fit:cover;"
                alt=""
            >

        {% else %}

            <div
                class="rounded-circle bg-body-secondary d-flex align-items-center justify-content-center"
                style="width:70px;height:70px;"
            >
                <i class="bi bi-person fs-2"></i>
            </div>

        {% endif %}


        <div>

            <h1 class="h3 mb-1">

                {% if customer.get_full_name %}

                    {{ customer.get_full_name }}

                {% else %}

                    {{ customer.username }}

                {% endif %}

            </h1>

            <p class="text-muted mb-0">
                Customer since
                {{ customer.date_joined|date:"d M Y" }}
            </p>

        </div>

    </div>


    <div class="d-flex gap-2 flex-wrap">

        <a
            href="{% url 'crm_customer_list' %}"
            class="btn btn-outline-secondary"
        >
            <i class="bi bi-arrow-left"></i>
            Customers
        </a>

        {% if customer.email %}

            <a
                href="mailto:{{ customer.email }}"
                class="btn btn-outline-primary"
            >
                <i class="bi bi-envelope"></i>
                Email
            </a>

        {% endif %}

        {% if customer.phone %}

            <a
                href="tel:{{ customer.phone }}"
                class="btn btn-outline-success"
            >
                <i class="bi bi-telephone"></i>
                Call
            </a>

        {% endif %}

    </div>

</div>


<div class="row g-3 mb-4">

    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card mini-stat">

            <span>Total Orders</span>

            <strong>
                {{ total_orders }}
            </strong>

        </div>

    </div>


    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card mini-stat">

            <span>Paid Orders</span>

            <strong>
                {{ paid_order_count }}
            </strong>

        </div>

    </div>


    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card mini-stat">

            <span>Lifetime Spend</span>

            <strong>
                KES {{ lifetime_spend|floatformat:2 }}
            </strong>

        </div>

    </div>


    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card mini-stat">

            <span>Last Order</span>

            <strong class="fs-6">

                {% if last_order %}

                    {{ last_order.created_at|date:"d M Y" }}

                {% else %}

                    Never

                {% endif %}

            </strong>

        </div>

    </div>

</div>


<div class="row g-4 mb-4">

    <div class="col-xl-6">

        <div class="dashboard-card h-100">

            <div class="d-flex justify-content-between align-items-center mb-3">

                <h2 class="h5 mb-0">
                    Customer Information
                </h2>

                {% if customer.is_active %}

                    <span class="badge text-bg-success">
                        Active
                    </span>

                {% else %}

                    <span class="badge text-bg-secondary">
                        Inactive
                    </span>

                {% endif %}

            </div>


            <dl class="row mb-0">

                <dt class="col-sm-4">
                    Username
                </dt>

                <dd class="col-sm-8">
                    {{ customer.username }}
                </dd>


                <dt class="col-sm-4">
                    Email
                </dt>

                <dd class="col-sm-8">
                    {{ customer.email|default:"—" }}
                </dd>


                <dt class="col-sm-4">
                    Phone
                </dt>

                <dd class="col-sm-8">
                    {{ customer.phone|default:"—" }}
                </dd>


                <dt class="col-sm-4">
                    Email Verified
                </dt>

                <dd class="col-sm-8">

                    {% if customer.email_verified %}

                        <span class="badge text-bg-success">
                            Yes
                        </span>

                    {% else %}

                        <span class="badge text-bg-warning">
                            No
                        </span>

                    {% endif %}

                </dd>


                <dt class="col-sm-4">
                    Email Alerts
                </dt>

                <dd class="col-sm-8">

                    {% if customer.email_notifications %}
                        Enabled
                    {% else %}
                        Disabled
                    {% endif %}

                </dd>


                <dt class="col-sm-4">
                    SMS Alerts
                </dt>

                <dd class="col-sm-8">

                    {% if customer.sms_notifications %}
                        Enabled
                    {% else %}
                        Disabled
                    {% endif %}

                </dd>

            </dl>


            <hr>


            <form
                method="POST"
                action="{% url 'crm_customer_toggle_status' customer.pk %}"
            >

                {% csrf_token %}

                {% if customer.is_active %}

                    <button
                        type="submit"
                        class="btn btn-outline-danger"
                    >
                        <i class="bi bi-person-x"></i>
                        Deactivate Account
                    </button>

                {% else %}

                    <button
                        type="submit"
                        class="btn btn-success"
                    >
                        <i class="bi bi-person-check"></i>
                        Activate Account
                    </button>

                {% endif %}

            </form>

        </div>

    </div>


    <div class="col-xl-6">

        <div class="dashboard-card h-100">

            <h2 class="h5 mb-3">
                Saved Addresses
            </h2>

            {% for address in addresses %}

                <div class="border rounded p-3 mb-3">

                    <div class="d-flex justify-content-between">

                        <strong>
                            {{ address.full_name }}
                        </strong>

                        {% if address.is_default %}

                            <span class="badge text-bg-primary">
                                Default
                            </span>

                        {% endif %}

                    </div>

                    <div class="text-muted mt-2">

                        {{ address.phone }}<br>

                        {{ address.house_number }},
                        {{ address.estate }}<br>

                        {{ address.city }},
                        {{ address.county }}

                        {% if address.landmark %}

                            <br>
                            Landmark:
                            {{ address.landmark }}

                        {% endif %}

                    </div>

                </div>

            {% empty %}

                <p class="text-muted mb-0">
                    No saved addresses.
                </p>

            {% endfor %}

        </div>

    </div>

</div>


<div class="dashboard-card mb-4">

    <div class="d-flex justify-content-between align-items-center mb-3">

        <h2 class="h5 mb-0">
            Internal CRM Notes
        </h2>

        <span class="text-muted small">
            Staff only
        </span>

    </div>


    <form
        method="POST"
        action="{% url 'crm_customer_note_add' customer.pk %}"
        class="mb-4"
    >

        {% csrf_token %}

        <div class="mb-3">

            {{ note_form.note }}

        </div>

        <div class="form-check mb-3">

            {{ note_form.is_pinned }}

            <label
                class="form-check-label"
                for="{{ note_form.is_pinned.id_for_label }}"
            >
                Pin this note
            </label>

        </div>

        <button
            class="btn btn-primary"
            type="submit"
        >
            <i class="bi bi-plus-lg"></i>
            Add Note
        </button>

    </form>


    {% for note in notes %}

        <div
            class="
                border rounded p-3 mb-3
                {% if note.is_pinned %}
                    border-warning
                {% endif %}
            "
        >

            <div class="d-flex justify-content-between gap-3">

                <div>

                    {% if note.is_pinned %}

                        <span class="badge text-bg-warning mb-2">
                            <i class="bi bi-pin-angle"></i>
                            Pinned
                        </span>

                    {% endif %}

                    <div style="white-space:pre-wrap;">{{ note.note }}</div>

                    <small class="text-muted d-block mt-2">

                        {{ note.created_at|date:"d M Y H:i" }}

                        {% if note.created_by %}

                            • {{ note.created_by }}

                        {% endif %}

                    </small>

                </div>


                <div class="d-flex gap-2 align-items-start">

                    <form
                        method="POST"
                        action="{% url 'crm_customer_note_toggle_pin' customer.pk note.pk %}"
                    >

                        {% csrf_token %}

                        <button
                            type="submit"
                            class="btn btn-sm btn-outline-secondary"
                            title="Pin or unpin"
                        >
                            <i class="bi bi-pin-angle"></i>
                        </button>

                    </form>


                    <form
                        method="POST"
                        action="{% url 'crm_customer_note_delete' customer.pk note.pk %}"
                        onsubmit="return confirm('Delete this customer note?');"
                    >

                        {% csrf_token %}

                        <button
                            type="submit"
                            class="btn btn-sm btn-outline-danger"
                        >
                            <i class="bi bi-trash"></i>
                        </button>

                    </form>

                </div>

            </div>

        </div>

    {% empty %}

        <p class="text-muted">
            No internal customer notes yet.
        </p>

    {% endfor %}

</div>


<div class="dashboard-card">

    <h2 class="h5 mb-3">
        Order History
    </h2>


    <div class="table-responsive">

        <table class="table align-middle">

            <thead>

                <tr>
                    <th>Order</th>
                    <th>Date</th>
                    <th>Items</th>
                    <th>Total</th>
                    <th>Payment</th>
                    <th>Status</th>
                    <th></th>
                </tr>

            </thead>

            <tbody>

                {% for order in orders %}

                    <tr>

                        <td>
                            <strong>
                                {{ order.order_number }}
                            </strong>
                        </td>


                        <td>
                            {{ order.created_at|date:"d M Y H:i" }}
                        </td>


                        <td>
                            {{ order.items.count }}
                        </td>


                        <td>
                            KES {{ order.total_amount|floatformat:2 }}
                        </td>


                        <td>

                            {% if order.payment_status == "paid" %}

                                <span class="badge text-bg-success">
                                    Paid
                                </span>

                            {% elif order.payment_status == "failed" %}

                                <span class="badge text-bg-danger">
                                    Failed
                                </span>

                            {% elif order.payment_status == "refunded" %}

                                <span class="badge text-bg-info">
                                    Refunded
                                </span>

                            {% else %}

                                <span class="badge text-bg-warning">
                                    Pending
                                </span>

                            {% endif %}

                        </td>


                        <td>
                            {{ order.get_status_display }}
                        </td>


                        <td>

                            <a
                                href="{% url 'admin_order_detail' order.order_number %}"
                                class="btn btn-sm btn-outline-primary"
                            >
                                View
                            </a>

                        </td>

                    </tr>

                {% empty %}

                    <tr>

                        <td
                            colspan="7"
                            class="text-center text-muted py-5"
                        >
                            This customer has not placed any orders.
                        </td>

                    </tr>

                {% endfor %}

            </tbody>

        </table>

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
    encoding="utf-8",
)

print(
    "Created customer detail template"
)


# ============================================================
# 10. REPLACE CUSTOMER SIDEBAR PLACEHOLDER
# ============================================================

text = base_template.read_text(
    encoding="utf-8-sig"
)

if (
    "crm_customer_list"
    not in text
):

    pattern = re.compile(
        r'''
        <a
        \s+
        href="\#"
        \s+
        class="sidebar-link"
        \s*
        >
        (?:
            (?!</a>).*
        )?
        <span>
        Customers
        </span>
        (?:
            (?!</a>).*
        )?
        </a>
        ''',
        re.S | re.X,
    )

    replacement = r'''
<a
    href="{% url 'crm_customer_list' %}"
    class="
        sidebar-link
        {% if 'crm_customer' in request.resolver_match.url_name %}
            active
        {% endif %}
    "
>
    <i class="bi bi-people"></i>
    <span>Customers</span>
</a>'''

    text, count = pattern.subn(
        replacement,
        text,
        count=1,
    )

    if count == 0:

        # More tolerant fallback.
        customer_pos = text.find(
            "<span>Customers</span>"
        )

        if customer_pos == -1:

            raise RuntimeError(
                (
                    "Could not find "
                    "Customers sidebar item."
                )
            )

        start = text.rfind(
            "<a",
            0,
            customer_pos,
        )

        end = text.find(
            "</a>",
            customer_pos,
        )

        if (
            start == -1
            or end == -1
        ):

            raise RuntimeError(
                (
                    "Could not determine "
                    "Customers link boundaries."
                )
            )

        end += len("</a>")

        text = (
            text[:start]
            + replacement
            + text[end:]
        )

    base_template.write_text(
        text,
        encoding="utf-8",
    )

    print(
        "Activated Customers sidebar link"
    )

else:

    print(
        "Customers sidebar already active"
    )


# ============================================================
# 11. TESTS
# ============================================================

tests_path.write_text(
r'''
from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase

from orders.models import Order

from .models import CustomerNote


User = get_user_model()


class CRMTests(TestCase):

    def setUp(self):

        self.staff = (
            User.objects.create_user(
                username="crmadmin",
                password="testpass123",
                role=User.ADMIN,
                is_staff=True,
            )
        )

        self.customer = (
            User.objects.create_user(
                username="buyer",
                email="buyer@example.com",
                password="testpass123",
                role=User.CUSTOMER,
                phone="0712345678",
            )
        )

    def create_order(
        self,
        number,
        payment_status="paid",
        amount="1000.00",
    ):

        return Order.objects.create(
            user=self.customer,
            order_number=number,
            full_name="Test Buyer",
            phone="0712345678",
            email="buyer@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal(amount),
            shipping_cost=Decimal("0.00"),
            discount=Decimal("0.00"),
            total_amount=Decimal(amount),
            status="delivered",
            payment_status=payment_status,
            inventory_status="consumed",
        )

    def test_customer_note(self):

        note = CustomerNote.objects.create(
            customer=self.customer,
            created_by=self.staff,
            note="Important customer note.",
        )

        self.assertEqual(
            note.customer,
            self.customer,
        )

    def test_customer_list_requires_staff(self):

        response = self.client.get(
            "/dashboard/admin/customers/"
        )

        self.assertNotEqual(
            response.status_code,
            200,
        )

        self.client.login(
            username="crmadmin",
            password="testpass123",
        )

        response = self.client.get(
            "/dashboard/admin/customers/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_customer_detail(self):

        self.create_order(
            "CRM-ORDER-001",
            amount="2500.00",
        )

        self.client.login(
            username="crmadmin",
            password="testpass123",
        )

        response = self.client.get(
            (
                "/dashboard/admin/customers/"
                f"{self.customer.pk}/"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "2,500",
        )
'''.strip() + "\n",
    encoding="utf-8",
)

print(
    "Created crm/tests.py"
)


print()
print("=" * 65)
print("PHASE 5 CUSTOMER CRM PATCH COMPLETE")
print("=" * 65)
print()
print("Next commands:")
print("python manage.py makemigrations crm")
print("python manage.py migrate")
print("python manage.py check")
