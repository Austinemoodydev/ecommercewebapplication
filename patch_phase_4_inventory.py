from pathlib import Path
import shutil

ROOT = Path.cwd()

settings_path = ROOT / "config" / "settings.py"
models_path = ROOT / "inventory" / "models.py"
forms_path = ROOT / "inventory" / "forms.py"
services_path = ROOT / "inventory" / "services.py"
views_path = ROOT / "inventory" / "views.py"
urls_path = ROOT / "inventory" / "urls.py"
tests_path = ROOT / "inventory" / "tests.py"

config_urls = ROOT / "config" / "urls.py"
order_inventory = ROOT / "orders" / "inventory.py"
base_template = (
    ROOT / "templates" / "dashboard" / "admin" / "base.html"
)

template_dir = (
    ROOT / "templates" / "dashboard" / "admin" / "inventory"
)

list_template = template_dir / "list.html"
detail_template = template_dir / "detail.html"
adjust_template = template_dir / "adjust.html"


def backup(path):
    if path.exists():
        target = Path(str(path) + ".phase4backup")
        shutil.copy2(path, target)
        print(f"Backup: {target}")


for path in [
    settings_path,
    config_urls,
    order_inventory,
    base_template,
]:
    backup(path)


# ============================================================
# INSTALLED APPS
# ============================================================

text = settings_path.read_text(
    encoding="utf-8-sig"
)

if '"inventory"' not in text and "'inventory'" not in text:

    marker = "'products',"

    if marker in text:
        text = text.replace(
            marker,
            marker + "\n    'inventory',",
            1,
        )
    else:
        marker = '"products",'

        if marker not in text:
            raise RuntimeError(
                "Could not find products app in INSTALLED_APPS."
            )

        text = text.replace(
            marker,
            marker + '\n    "inventory",',
            1,
        )

    settings_path.write_text(
        text,
        encoding="utf-8",
    )

    print("Added inventory to INSTALLED_APPS")

else:
    print("inventory already in INSTALLED_APPS")


# ============================================================
# INVENTORY MODEL
# ============================================================

models_path.write_text(
r'''
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from products.models import Product, ProductVariant


class InventoryMovement(models.Model):

    MOVEMENT_TYPES = [
        ("restock", "Restock"),
        ("sale", "Sale"),
        ("adjustment_in", "Adjustment In"),
        ("adjustment_out", "Adjustment Out"),
        ("damaged", "Damaged / Lost"),
        ("return", "Customer Return"),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="inventory_movements",
        null=True,
        blank=True,
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        related_name="inventory_movements",
        null=True,
        blank=True,
    )

    movement_type = models.CharField(
        max_length=30,
        choices=MOVEMENT_TYPES,
        db_index=True,
    )

    quantity = models.PositiveIntegerField()

    stock_before = models.PositiveIntegerField()

    stock_after = models.PositiveIntegerField()

    reference = models.CharField(
        max_length=150,
        blank=True,
        db_index=True,
    )

    notes = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_movements",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at", "-id"]

        indexes = [
            models.Index(
                fields=[
                    "movement_type",
                    "created_at",
                ]
            ),
        ]

    def clean(self):

        if self.product_id and self.variant_id:
            raise ValidationError(
                "A movement cannot target both "
                "a product and a variant."
            )

        if not self.product_id and not self.variant_id:
            raise ValidationError(
                "A movement must target either "
                "a product or a variant."
            )

        if self.quantity <= 0:
            raise ValidationError(
                "Movement quantity must be greater than zero."
            )

    @property
    def item_name(self):

        if self.variant_id:
            return (
                f"{self.variant.product.name} "
                f"— {self.variant.name}"
            )

        return self.product.name

    @property
    def direction(self):

        if self.movement_type in {
            "restock",
            "adjustment_in",
            "return",
        }:
            return "in"

        return "out"

    def __str__(self):
        return (
            f"{self.get_movement_type_display()} "
            f"{self.item_name} "
            f"({self.quantity})"
        )
'''.strip() + "\n",
    encoding="utf-8",
)

print("Created inventory/models.py")


# ============================================================
# INVENTORY SERVICES
# ============================================================

services_path.write_text(
r'''
from django.db import transaction

from products.models import Product, ProductVariant

from .models import InventoryMovement


class InventoryAdjustmentError(Exception):
    pass


INBOUND_TYPES = {
    "restock",
    "adjustment_in",
    "return",
}

OUTBOUND_TYPES = {
    "adjustment_out",
    "damaged",
}


def record_inventory_movement(
    *,
    product=None,
    variant=None,
    movement_type,
    quantity,
    stock_before,
    stock_after,
    reference="",
    notes="",
    user=None,
):

    movement = InventoryMovement(
        product=product,
        variant=variant,
        movement_type=movement_type,
        quantity=quantity,
        stock_before=stock_before,
        stock_after=stock_after,
        reference=reference,
        notes=notes,
        created_by=user,
    )

    movement.full_clean()
    movement.save()

    return movement


@transaction.atomic
def adjust_product_stock(
    *,
    product_id,
    movement_type,
    quantity,
    reference="",
    notes="",
    user=None,
):

    if quantity <= 0:
        raise InventoryAdjustmentError(
            "Quantity must be greater than zero."
        )

    product = (
        Product.objects
        .select_for_update()
        .get(pk=product_id)
    )

    stock_before = product.stock

    if movement_type in INBOUND_TYPES:

        stock_after = (
            stock_before + quantity
        )

    elif movement_type in OUTBOUND_TYPES:

        stock_after = (
            stock_before - quantity
        )

        if stock_after < 0:
            raise InventoryAdjustmentError(
                "There is not enough physical stock "
                "for this adjustment."
            )

        if stock_after < product.reserved_stock:
            raise InventoryAdjustmentError(
                (
                    "This adjustment would reduce "
                    "physical stock below stock already "
                    "reserved by customer orders."
                )
            )

    else:
        raise InventoryAdjustmentError(
            "Unsupported inventory movement type."
        )

    product.stock = stock_after

    product.save(
        update_fields=[
            "stock",
            "updated_at",
        ]
    )

    return record_inventory_movement(
        product=product,
        movement_type=movement_type,
        quantity=quantity,
        stock_before=stock_before,
        stock_after=stock_after,
        reference=reference,
        notes=notes,
        user=user,
    )


@transaction.atomic
def adjust_variant_stock(
    *,
    variant_id,
    movement_type,
    quantity,
    reference="",
    notes="",
    user=None,
):

    if quantity <= 0:
        raise InventoryAdjustmentError(
            "Quantity must be greater than zero."
        )

    variant = (
        ProductVariant.objects
        .select_for_update()
        .select_related("product")
        .get(pk=variant_id)
    )

    stock_before = variant.stock

    if movement_type in INBOUND_TYPES:

        stock_after = (
            stock_before + quantity
        )

    elif movement_type in OUTBOUND_TYPES:

        stock_after = (
            stock_before - quantity
        )

        if stock_after < 0:
            raise InventoryAdjustmentError(
                "There is not enough physical stock "
                "for this adjustment."
            )

        if stock_after < variant.reserved_stock:
            raise InventoryAdjustmentError(
                (
                    "This adjustment would reduce "
                    "physical stock below stock already "
                    "reserved by customer orders."
                )
            )

    else:
        raise InventoryAdjustmentError(
            "Unsupported inventory movement type."
        )

    variant.stock = stock_after

    variant.save(
        update_fields=[
            "stock",
        ]
    )

    return record_inventory_movement(
        variant=variant,
        movement_type=movement_type,
        quantity=quantity,
        stock_before=stock_before,
        stock_after=stock_after,
        reference=reference,
        notes=notes,
        user=user,
    )
'''.strip() + "\n",
    encoding="utf-8",
)

print("Created inventory/services.py")


# ============================================================
# INVENTORY FORMS
# ============================================================

forms_path.write_text(
r'''
from django import forms


class InventoryAdjustmentForm(forms.Form):

    MOVEMENT_CHOICES = [
        ("restock", "Restock / Supplier Delivery"),
        ("adjustment_in", "Manual Stock Increase"),
        ("adjustment_out", "Manual Stock Reduction"),
        ("damaged", "Damaged / Lost Stock"),
        ("return", "Customer Return"),
    ]

    movement_type = forms.ChoiceField(
        choices=MOVEMENT_CHOICES,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "1",
            }
        ),
    )

    reference = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": (
                    "Supplier invoice, GRN, "
                    "reference number..."
                ),
            }
        ),
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": (
                    "Reason or additional details..."
                ),
            }
        ),
    )
'''.strip() + "\n",
    encoding="utf-8",
)

print("Created inventory/forms.py")


# ============================================================
# INVENTORY VIEWS
# ============================================================

views_path.write_text(
r'''
from django.contrib import messages

from django.contrib.admin.views.decorators import (
    staff_member_required,
)

from django.core.paginator import Paginator

from django.db.models import Q

from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from products.models import (
    Product,
    ProductVariant,
)

from .forms import InventoryAdjustmentForm

from .models import InventoryMovement

from .services import (
    InventoryAdjustmentError,
    adjust_product_stock,
    adjust_variant_stock,
)


@staff_member_required
def inventory_dashboard(request):

    query = request.GET.get(
        "q",
        "",
    ).strip()

    stock_filter = request.GET.get(
        "stock",
        "",
    )

    products = (
        Product.objects
        .select_related(
            "category",
            "brand",
        )
        .prefetch_related(
            "variants"
        )
        .order_by("name")
    )

    if query:

        products = products.filter(
            Q(name__icontains=query)
            | Q(sku__icontains=query)
            | Q(category__name__icontains=query)
            | Q(brand__name__icontains=query)
        )

    product_rows = []

    low_stock_count = 0
    out_stock_count = 0

    for product in products:

        available = product.available_stock

        if available == 0:
            out_stock_count += 1

        elif available <= 5:
            low_stock_count += 1

        if (
            stock_filter == "low"
            and not (
                0 < available <= 5
            )
        ):
            continue

        if (
            stock_filter == "out"
            and available != 0
        ):
            continue

        if (
            stock_filter == "available"
            and available <= 0
        ):
            continue

        product_rows.append(
            product
        )

    paginator = Paginator(
        product_rows,
        20,
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    recent_movements = (
        InventoryMovement.objects
        .select_related(
            "product",
            "variant",
            "variant__product",
            "created_by",
        )
        .all()[:10]
    )

    return render(
        request,
        (
            "dashboard/admin/inventory/"
            "list.html"
        ),
        {
            "products": (
                page_obj.object_list
            ),
            "page_obj": page_obj,
            "query": query,
            "selected_stock": stock_filter,
            "total_products": (
                Product.objects.count()
            ),
            "low_stock_count": (
                low_stock_count
            ),
            "out_stock_count": (
                out_stock_count
            ),
            "recent_movements": (
                recent_movements
            ),
        },
    )


@staff_member_required
def inventory_product_detail(
    request,
    pk,
):

    product = get_object_or_404(
        Product.objects.prefetch_related(
            "variants"
        ),
        pk=pk,
    )

    movements = (
        InventoryMovement.objects
        .select_related(
            "product",
            "variant",
            "created_by",
        )
        .filter(
            Q(product=product)
            | Q(
                variant__product=product
            )
        )
        .order_by(
            "-created_at"
        )
    )

    paginator = Paginator(
        movements,
        30,
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        (
            "dashboard/admin/inventory/"
            "detail.html"
        ),
        {
            "product": product,
            "variants": (
                product.variants.all()
            ),
            "movements": (
                page_obj.object_list
            ),
            "page_obj": page_obj,
        },
    )


@staff_member_required
def inventory_product_adjust(
    request,
    pk,
):

    product = get_object_or_404(
        Product,
        pk=pk,
    )

    if request.method == "POST":

        form = InventoryAdjustmentForm(
            request.POST
        )

        if form.is_valid():

            try:

                adjust_product_stock(
                    product_id=product.pk,
                    movement_type=(
                        form.cleaned_data[
                            "movement_type"
                        ]
                    ),
                    quantity=(
                        form.cleaned_data[
                            "quantity"
                        ]
                    ),
                    reference=(
                        form.cleaned_data[
                            "reference"
                        ]
                    ),
                    notes=(
                        form.cleaned_data[
                            "notes"
                        ]
                    ),
                    user=request.user,
                )

            except InventoryAdjustmentError as exc:

                messages.error(
                    request,
                    str(exc),
                )

            else:

                messages.success(
                    request,
                    (
                        "Product inventory "
                        "updated successfully."
                    ),
                )

                return redirect(
                    "inventory_product_detail",
                    pk=product.pk,
                )

    else:

        form = InventoryAdjustmentForm()

    return render(
        request,
        (
            "dashboard/admin/inventory/"
            "adjust.html"
        ),
        {
            "product": product,
            "variant": None,
            "form": form,
            "page_title": (
                "Adjust Product Stock"
            ),
        },
    )


@staff_member_required
def inventory_variant_adjust(
    request,
    pk,
    variant_id,
):

    product = get_object_or_404(
        Product,
        pk=pk,
    )

    variant = get_object_or_404(
        ProductVariant,
        pk=variant_id,
        product=product,
    )

    if request.method == "POST":

        form = InventoryAdjustmentForm(
            request.POST
        )

        if form.is_valid():

            try:

                adjust_variant_stock(
                    variant_id=variant.pk,
                    movement_type=(
                        form.cleaned_data[
                            "movement_type"
                        ]
                    ),
                    quantity=(
                        form.cleaned_data[
                            "quantity"
                        ]
                    ),
                    reference=(
                        form.cleaned_data[
                            "reference"
                        ]
                    ),
                    notes=(
                        form.cleaned_data[
                            "notes"
                        ]
                    ),
                    user=request.user,
                )

            except InventoryAdjustmentError as exc:

                messages.error(
                    request,
                    str(exc),
                )

            else:

                messages.success(
                    request,
                    (
                        "Variant inventory "
                        "updated successfully."
                    ),
                )

                return redirect(
                    "inventory_product_detail",
                    pk=product.pk,
                )

    else:

        form = InventoryAdjustmentForm()

    return render(
        request,
        (
            "dashboard/admin/inventory/"
            "adjust.html"
        ),
        {
            "product": product,
            "variant": variant,
            "form": form,
            "page_title": (
                "Adjust Variant Stock"
            ),
        },
    )


@staff_member_required
def inventory_movement_list(
    request,
):

    movements = (
        InventoryMovement.objects
        .select_related(
            "product",
            "variant",
            "variant__product",
            "created_by",
        )
        .all()
    )

    query = request.GET.get(
        "q",
        "",
    ).strip()

    movement_type = request.GET.get(
        "type",
        "",
    )

    if query:

        movements = movements.filter(
            Q(product__name__icontains=query)
            | Q(
                variant__product__name__icontains=query
            )
            | Q(
                variant__name__icontains=query
            )
            | Q(reference__icontains=query)
        )

    if movement_type:

        movements = movements.filter(
            movement_type=movement_type
        )

    paginator = Paginator(
        movements,
        50,
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        (
            "dashboard/admin/inventory/"
            "movements.html"
        ),
        {
            "movements": (
                page_obj.object_list
            ),
            "page_obj": page_obj,
            "query": query,
            "selected_type": movement_type,
            "movement_types": (
                InventoryMovement.MOVEMENT_TYPES
            ),
        },
    )
'''.strip() + "\n",
    encoding="utf-8",
)

print("Created inventory/views.py")


# ============================================================
# INVENTORY URLS
# ============================================================

urls_path.write_text(
r'''
from django.urls import path

from . import views


urlpatterns = [

    path(
        "",
        views.inventory_dashboard,
        name="inventory_dashboard",
    ),

    path(
        "movements/",
        views.inventory_movement_list,
        name="inventory_movement_list",
    ),

    path(
        "products/<int:pk>/",
        views.inventory_product_detail,
        name="inventory_product_detail",
    ),

    path(
        "products/<int:pk>/adjust/",
        views.inventory_product_adjust,
        name="inventory_product_adjust",
    ),

    path(
        "products/<int:pk>/variants/<int:variant_id>/adjust/",
        views.inventory_variant_adjust,
        name="inventory_variant_adjust",
    ),
]
'''.strip() + "\n",
    encoding="utf-8",
)

print("Created inventory/urls.py")


# ============================================================
# ADD INVENTORY URL INCLUDE
# ============================================================

text = config_urls.read_text(
    encoding="utf-8-sig"
)

if 'include("inventory.urls")' not in text:

    if "from django.urls import" in text:

        if "include" not in text.splitlines()[0:15].__str__():

            text = text.replace(
                "from django.urls import path",
                "from django.urls import include, path",
            )

    marker = "urlpatterns = ["

    if marker not in text:
        raise RuntimeError(
            "Could not find urlpatterns in config/urls.py."
        )

    text = text.replace(
        marker,
        marker
        + '''
    path(
        "dashboard/admin/inventory/",
        include("inventory.urls"),
    ),
''',
        1,
    )

    config_urls.write_text(
        text,
        encoding="utf-8",
    )

    print("Connected inventory URLs")

else:
    print("Inventory URLs already connected")


# ============================================================
# CONNECT SALES TO INVENTORY LEDGER
# ============================================================

text = order_inventory.read_text(
    encoding="utf-8-sig"
)

if (
    "record_inventory_movement"
    not in text
):

    text = (
        "from inventory.services import "
        "record_inventory_movement\n"
        + text
    )

    # Insert recording after physical stock save.
    old = '''        inventory.stock -= item.quantity
        inventory.reserved_stock = max(
            inventory.reserved_stock - item.quantity,
            0,
        )
'''

    new = '''        stock_before = inventory.stock

        inventory.stock -= item.quantity
        inventory.reserved_stock = max(
            inventory.reserved_stock - item.quantity,
            0,
        )
'''

    if old in text:
        text = text.replace(
            old,
            new,
            1,
        )
    else:
        print(
            "WARNING: Could not automatically "
            "insert stock_before in orders/inventory.py"
        )

    save_marker = '''        inventory.save(update_fields=fields)
'''

    replacement = '''        inventory.save(update_fields=fields)

        record_inventory_movement(
            product=(
                None
                if item.variant_id
                else inventory
            ),
            variant=(
                inventory
                if item.variant_id
                else None
            ),
            movement_type="sale",
            quantity=item.quantity,
            stock_before=stock_before,
            stock_after=inventory.stock,
            reference=order.order_number,
            notes=(
                "Stock consumed after "
                "successful payment."
            ),
        )
'''

    # Replace last relevant save in consume function.
    consume_pos = text.find(
        "def consume_order_inventory"
    )

    if consume_pos != -1:

        before = text[:consume_pos]
        after = text[consume_pos:]

        if save_marker in after:

            after = after.replace(
                save_marker,
                replacement,
                1,
            )

            text = before + after

        else:
            print(
                "WARNING: Could not insert "
                "sale ledger recording."
            )

    order_inventory.write_text(
        text,
        encoding="utf-8",
    )

    print(
        "Connected successful sales "
        "to inventory ledger"
    )

else:
    print(
        "Sale ledger integration already exists"
    )


# ============================================================
# TEMPLATES
# ============================================================

template_dir.mkdir(
    parents=True,
    exist_ok=True,
)


list_template.write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Inventory | Store Management
{% endblock %}

{% block page_heading %}
Inventory
{% endblock %}

{% block admin_content %}

<div class="d-flex justify-content-between align-items-center flex-wrap gap-3 mb-4">

    <div>
        <h1 class="h3 mb-1">
            Inventory Management
        </h1>

        <p class="text-muted mb-0">
            Monitor stock, reservations and movements.
        </p>
    </div>

    <a
        href="{% url 'inventory_movement_list' %}"
        class="btn btn-outline-primary"
    >
        <i class="bi bi-clock-history"></i>
        Stock History
    </a>

</div>


<div class="row g-3 mb-4">

    <div class="col-md-4">
        <div class="dashboard-card mini-stat">
            <span>Products</span>
            <strong>{{ total_products }}</strong>
        </div>
    </div>

    <div class="col-md-4">
        <div class="dashboard-card mini-stat">
            <span>Low Stock</span>
            <strong>{{ low_stock_count }}</strong>
        </div>
    </div>

    <div class="col-md-4">
        <div class="dashboard-card mini-stat">
            <span>Out of Stock</span>
            <strong>{{ out_stock_count }}</strong>
        </div>
    </div>

</div>


<div class="dashboard-card mb-4">

    <form method="GET">

        <div class="row g-3">

            <div class="col-md-8">

                <label class="form-label">
                    Search
                </label>

                <input
                    type="text"
                    name="q"
                    value="{{ query }}"
                    class="form-control"
                    placeholder="Product, SKU, brand..."
                >

            </div>

            <div class="col-md-4">

                <label class="form-label">
                    Stock Status
                </label>

                <select
                    name="stock"
                    class="form-select"
                >

                    <option value="">
                        All
                    </option>

                    <option
                        value="available"
                        {% if selected_stock == "available" %}
                            selected
                        {% endif %}
                    >
                        Available
                    </option>

                    <option
                        value="low"
                        {% if selected_stock == "low" %}
                            selected
                        {% endif %}
                    >
                        Low Stock
                    </option>

                    <option
                        value="out"
                        {% if selected_stock == "out" %}
                            selected
                        {% endif %}
                    >
                        Out of Stock
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
                href="{% url 'inventory_dashboard' %}"
                class="btn btn-outline-secondary"
            >
                Reset
            </a>

        </div>

    </form>

</div>


<div class="dashboard-card mb-4">

    <div class="table-responsive">

        <table class="table align-middle">

            <thead>
                <tr>
                    <th>Product</th>
                    <th>Physical</th>
                    <th>Reserved</th>
                    <th>Available</th>
                    <th>Variants</th>
                    <th></th>
                </tr>
            </thead>

            <tbody>

                {% for product in products %}

                    <tr>

                        <td>

                            <strong>
                                {{ product.name }}
                            </strong>

                            <small class="text-muted d-block">
                                {{ product.sku }}
                            </small>

                        </td>

                        <td>
                            {{ product.stock }}
                        </td>

                        <td>
                            {{ product.reserved_stock }}
                        </td>

                        <td>

                            {% if product.available_stock == 0 %}

                                <span class="badge text-bg-danger">
                                    0
                                </span>

                            {% elif product.available_stock <= 5 %}

                                <span class="badge text-bg-warning">
                                    {{ product.available_stock }}
                                </span>

                            {% else %}

                                <span class="badge text-bg-success">
                                    {{ product.available_stock }}
                                </span>

                            {% endif %}

                        </td>

                        <td>
                            {{ product.variants.count }}
                        </td>

                        <td>

                            <a
                                href="{% url 'inventory_product_detail' product.pk %}"
                                class="btn btn-sm btn-outline-primary"
                            >
                                Manage
                            </a>

                        </td>

                    </tr>

                {% empty %}

                    <tr>
                        <td
                            colspan="6"
                            class="text-center text-muted py-5"
                        >
                            No products found.
                        </td>
                    </tr>

                {% endfor %}

            </tbody>

        </table>

    </div>

</div>


<div class="dashboard-card">

    <div class="d-flex justify-content-between align-items-center mb-3">

        <h2 class="h5 mb-0">
            Recent Stock Movements
        </h2>

        <a
            href="{% url 'inventory_movement_list' %}"
        >
            View All
        </a>

    </div>

    <div class="table-responsive">

        <table class="table align-middle">

            <thead>
                <tr>
                    <th>Item</th>
                    <th>Type</th>
                    <th>Qty</th>
                    <th>Before</th>
                    <th>After</th>
                    <th>Reference</th>
                    <th>Date</th>
                </tr>
            </thead>

            <tbody>

                {% for movement in recent_movements %}

                    <tr>

                        <td>
                            {{ movement.item_name }}
                        </td>

                        <td>
                            {{ movement.get_movement_type_display }}
                        </td>

                        <td>
                            {{ movement.quantity }}
                        </td>

                        <td>
                            {{ movement.stock_before }}
                        </td>

                        <td>
                            {{ movement.stock_after }}
                        </td>

                        <td>
                            {{ movement.reference|default:"—" }}
                        </td>

                        <td>
                            {{ movement.created_at|date:"d M Y H:i" }}
                        </td>

                    </tr>

                {% empty %}

                    <tr>
                        <td
                            colspan="7"
                            class="text-center text-muted py-4"
                        >
                            No inventory movements yet.
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


detail_template.write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Inventory | {{ product.name }}
{% endblock %}

{% block page_heading %}
Inventory
{% endblock %}

{% block admin_content %}

<div class="d-flex justify-content-between align-items-center flex-wrap gap-3 mb-4">

    <div>

        <h1 class="h3 mb-1">
            {{ product.name }}
        </h1>

        <p class="text-muted mb-0">
            SKU: {{ product.sku }}
        </p>

    </div>

    <div class="d-flex gap-2">

        <a
            href="{% url 'inventory_dashboard' %}"
            class="btn btn-outline-secondary"
        >
            <i class="bi bi-arrow-left"></i>
            Inventory
        </a>

        <a
            href="{% url 'inventory_product_adjust' product.pk %}"
            class="btn btn-primary"
        >
            <i class="bi bi-plus-slash-minus"></i>
            Adjust Stock
        </a>

    </div>

</div>


<div class="row g-3 mb-4">

    <div class="col-md-4">
        <div class="dashboard-card mini-stat">
            <span>Physical Stock</span>
            <strong>{{ product.stock }}</strong>
        </div>
    </div>

    <div class="col-md-4">
        <div class="dashboard-card mini-stat">
            <span>Reserved</span>
            <strong>{{ product.reserved_stock }}</strong>
        </div>
    </div>

    <div class="col-md-4">
        <div class="dashboard-card mini-stat">
            <span>Available</span>
            <strong>{{ product.available_stock }}</strong>
        </div>
    </div>

</div>


{% if variants %}

<div class="dashboard-card mb-4">

    <h2 class="h5 mb-3">
        Variant Inventory
    </h2>

    <div class="table-responsive">

        <table class="table align-middle">

            <thead>
                <tr>
                    <th>Variant</th>
                    <th>SKU</th>
                    <th>Physical</th>
                    <th>Reserved</th>
                    <th>Available</th>
                    <th></th>
                </tr>
            </thead>

            <tbody>

                {% for variant in variants %}

                    <tr>

                        <td>
                            {{ variant.name }}
                        </td>

                        <td>
                            {{ variant.sku }}
                        </td>

                        <td>
                            {{ variant.stock }}
                        </td>

                        <td>
                            {{ variant.reserved_stock }}
                        </td>

                        <td>
                            {{ variant.available_stock }}
                        </td>

                        <td>

                            <a
                                href="{% url 'inventory_variant_adjust' product.pk variant.pk %}"
                                class="btn btn-sm btn-outline-primary"
                            >
                                Adjust
                            </a>

                        </td>

                    </tr>

                {% endfor %}

            </tbody>

        </table>

    </div>

</div>

{% endif %}


<div class="dashboard-card">

    <h2 class="h5 mb-3">
        Stock History
    </h2>

    <div class="table-responsive">

        <table class="table align-middle">

            <thead>
                <tr>
                    <th>Date</th>
                    <th>Item</th>
                    <th>Movement</th>
                    <th>Qty</th>
                    <th>Before</th>
                    <th>After</th>
                    <th>Reference</th>
                    <th>Staff</th>
                </tr>
            </thead>

            <tbody>

                {% for movement in movements %}

                    <tr>

                        <td>
                            {{ movement.created_at|date:"d M Y H:i" }}
                        </td>

                        <td>
                            {{ movement.item_name }}
                        </td>

                        <td>
                            {{ movement.get_movement_type_display }}
                        </td>

                        <td>
                            {{ movement.quantity }}
                        </td>

                        <td>
                            {{ movement.stock_before }}
                        </td>

                        <td>
                            {{ movement.stock_after }}
                        </td>

                        <td>
                            {{ movement.reference|default:"—" }}
                        </td>

                        <td>

                            {% if movement.created_by %}
                                {{ movement.created_by }}
                            {% else %}
                                System
                            {% endif %}

                        </td>

                    </tr>

                {% empty %}

                    <tr>
                        <td
                            colspan="8"
                            class="text-center text-muted py-5"
                        >
                            No stock history yet.
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


adjust_template.write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
{{ page_title }}
{% endblock %}

{% block page_heading %}
Inventory Adjustment
{% endblock %}

{% block admin_content %}

<div class="d-flex justify-content-between align-items-center mb-4">

    <div>

        <h1 class="h3 mb-1">
            {{ page_title }}
        </h1>

        <p class="text-muted mb-0">

            {{ product.name }}

            {% if variant %}
                — {{ variant.name }}
            {% endif %}

        </p>

    </div>

    <a
        href="{% url 'inventory_product_detail' product.pk %}"
        class="btn btn-outline-secondary"
    >
        <i class="bi bi-arrow-left"></i>
        Back
    </a>

</div>


<div class="row">

    <div class="col-xl-7">

        <form method="POST">

            {% csrf_token %}

            <div class="dashboard-card">

                {% if variant %}

                    <div class="alert alert-light border">

                        Physical:
                        <strong>
                            {{ variant.stock }}
                        </strong>

                        &nbsp; | &nbsp;

                        Reserved:
                        <strong>
                            {{ variant.reserved_stock }}
                        </strong>

                        &nbsp; | &nbsp;

                        Available:
                        <strong>
                            {{ variant.available_stock }}
                        </strong>

                    </div>

                {% else %}

                    <div class="alert alert-light border">

                        Physical:
                        <strong>
                            {{ product.stock }}
                        </strong>

                        &nbsp; | &nbsp;

                        Reserved:
                        <strong>
                            {{ product.reserved_stock }}
                        </strong>

                        &nbsp; | &nbsp;

                        Available:
                        <strong>
                            {{ product.available_stock }}
                        </strong>

                    </div>

                {% endif %}


                <div class="mb-3">

                    <label class="form-label">
                        Movement Type
                    </label>

                    {{ form.movement_type }}

                </div>


                <div class="mb-3">

                    <label class="form-label">
                        Quantity
                    </label>

                    {{ form.quantity }}

                </div>


                <div class="mb-3">

                    <label class="form-label">
                        Reference
                    </label>

                    {{ form.reference }}

                    <div class="form-text">
                        Example: supplier invoice,
                        GRN, adjustment reference.
                    </div>

                </div>


                <div class="mb-4">

                    <label class="form-label">
                        Notes
                    </label>

                    {{ form.notes }}

                </div>


                <button
                    type="submit"
                    class="btn btn-primary"
                >
                    <i class="bi bi-check-lg"></i>
                    Save Stock Movement
                </button>

            </div>

        </form>

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
    encoding="utf-8",
)


movement_template = (
    template_dir / "movements.html"
)

movement_template.write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Stock History
{% endblock %}

{% block page_heading %}
Stock History
{% endblock %}

{% block admin_content %}

<div class="d-flex justify-content-between align-items-center mb-4">

    <div>

        <h1 class="h3 mb-1">
            Inventory Movement Ledger
        </h1>

        <p class="text-muted mb-0">
            Complete history of physical stock changes.
        </p>

    </div>

    <a
        href="{% url 'inventory_dashboard' %}"
        class="btn btn-outline-secondary"
    >
        Inventory
    </a>

</div>


<div class="dashboard-card mb-4">

    <form method="GET">

        <div class="row g-3">

            <div class="col-md-8">

                <input
                    type="text"
                    name="q"
                    value="{{ query }}"
                    class="form-control"
                    placeholder="Product, variant, reference..."
                >

            </div>

            <div class="col-md-4">

                <select
                    name="type"
                    class="form-select"
                >

                    <option value="">
                        All Movement Types
                    </option>

                    {% for value, label in movement_types %}

                        <option
                            value="{{ value }}"
                            {% if selected_type == value %}
                                selected
                            {% endif %}
                        >
                            {{ label }}
                        </option>

                    {% endfor %}

                </select>

            </div>

        </div>

        <div class="mt-3">

            <button
                class="btn btn-primary"
                type="submit"
            >
                Filter
            </button>

            <a
                href="{% url 'inventory_movement_list' %}"
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
                    <th>Date</th>
                    <th>Item</th>
                    <th>Type</th>
                    <th>Quantity</th>
                    <th>Before</th>
                    <th>After</th>
                    <th>Reference</th>
                    <th>Staff</th>
                </tr>
            </thead>

            <tbody>

                {% for movement in movements %}

                    <tr>

                        <td>
                            {{ movement.created_at|date:"d M Y H:i" }}
                        </td>

                        <td>
                            {{ movement.item_name }}
                        </td>

                        <td>
                            {{ movement.get_movement_type_display }}
                        </td>

                        <td>
                            {{ movement.quantity }}
                        </td>

                        <td>
                            {{ movement.stock_before }}
                        </td>

                        <td>
                            {{ movement.stock_after }}
                        </td>

                        <td>
                            {{ movement.reference|default:"—" }}
                        </td>

                        <td>

                            {% if movement.created_by %}
                                {{ movement.created_by }}
                            {% else %}
                                System
                            {% endif %}

                        </td>

                    </tr>

                {% empty %}

                    <tr>
                        <td
                            colspan="8"
                            class="text-center text-muted py-5"
                        >
                            No inventory movements found.
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

print("Created inventory templates")


# ============================================================
# SIDEBAR LINK
# ============================================================

text = base_template.read_text(
    encoding="utf-8-sig"
)

if "inventory_dashboard" not in text:

    pos = text.find(
        "{% url 'admin_category_list' %}"
    )

    if pos == -1:

        pos = text.find(
            "{% url 'admin_analytics' %}"
        )

    if pos == -1:

        raise RuntimeError(
            "Could not locate sidebar insertion point."
        )

    start = text.rfind(
        "<a",
        0,
        pos,
    )

    inventory_link = r'''
<a
    href="{% url 'inventory_dashboard' %}"
    class="
        sidebar-link
        {% if 'inventory' in request.resolver_match.url_name %}
            active
        {% endif %}
    "
>
    <i class="bi bi-boxes"></i>
    <span>Inventory</span>
</a>

'''

    text = (
        text[:start]
        + inventory_link
        + text[start:]
    )

    base_template.write_text(
        text,
        encoding="utf-8",
    )

    print("Added Inventory to sidebar")

else:
    print("Inventory sidebar link already exists")


# ============================================================
# TESTS
# ============================================================

tests_path.write_text(
r'''
from django.contrib.auth import get_user_model
from django.test import TestCase

from categories.models import Category
from products.models import Product

from .models import InventoryMovement

from .services import (
    InventoryAdjustmentError,
    adjust_product_stock,
)


class InventoryServiceTests(TestCase):

    def setUp(self):

        User = get_user_model()

        self.user = User.objects.create_user(
            username="inventorytester",
            password="testpass123",
        )

        self.category = Category.objects.create(
            name="Inventory Test",
            slug="inventory-test",
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Inventory Product",
            slug="inventory-product",
            sku="INV-001",
            price="1000.00",
            stock=10,
            reserved_stock=2,
            is_active=True,
        )

    def test_restock_creates_movement(self):

        adjust_product_stock(
            product_id=self.product.pk,
            movement_type="restock",
            quantity=5,
            reference="INV-100",
            user=self.user,
        )

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.stock,
            15,
        )

        movement = (
            InventoryMovement.objects.get()
        )

        self.assertEqual(
            movement.stock_before,
            10,
        )

        self.assertEqual(
            movement.stock_after,
            15,
        )

    def test_cannot_reduce_below_reserved(self):

        with self.assertRaises(
            InventoryAdjustmentError
        ):

            adjust_product_stock(
                product_id=self.product.pk,
                movement_type="damaged",
                quantity=9,
                user=self.user,
            )

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.stock,
            10,
        )
'''.strip() + "\n",
    encoding="utf-8",
)

print("Created inventory/tests.py")

print()
print("=" * 65)
print("PHASE 4 INVENTORY PATCH CREATED")
print("=" * 65)
print()
print("Run:")
print("python manage.py makemigrations inventory")
print("python manage.py migrate")
print("python manage.py check")
