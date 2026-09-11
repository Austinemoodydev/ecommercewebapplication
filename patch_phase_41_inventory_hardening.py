from pathlib import Path
import re
import shutil


ROOT = Path.cwd()

models_path = ROOT / "products" / "models.py"
forms_path = ROOT / "dashboard" / "forms.py"

inventory_views = ROOT / "inventory" / "views.py"
inventory_urls = ROOT / "inventory" / "urls.py"

variant_template = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "products"
    / "variant_form.html"
)

inventory_list = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "inventory"
    / "list.html"
)

inventory_detail = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "inventory"
    / "detail.html"
)


# ============================================================
# HELPERS
# ============================================================

def backup(path):

    if path.exists():

        target = Path(
            str(path) + ".phase41backup"
        )

        shutil.copy2(
            path,
            target,
        )

        print(
            f"Backup: {target}"
        )


def get_class_block(
    text,
    class_name,
):

    marker = (
        f"class {class_name}"
    )

    start = text.find(marker)

    if start == -1:
        raise RuntimeError(
            f"{class_name} not found."
        )

    end = text.find(
        "\nclass ",
        start + len(marker),
    )

    if end == -1:
        end = len(text)

    return (
        start,
        end,
        text[start:end],
    )


def replace_class_block(
    text,
    class_name,
    new_block,
):

    start, end, old = get_class_block(
        text,
        class_name,
    )

    return (
        text[:start]
        + new_block
        + text[end:]
    )


for path in [
    models_path,
    forms_path,
    inventory_views,
    inventory_urls,
    variant_template,
    inventory_list,
    inventory_detail,
]:

    backup(path)


# ============================================================
# 1. PRODUCT MODEL HARDENING
# ============================================================

text = models_path.read_text(
    encoding="utf-8-sig"
)


# ------------------------------------------------------------
# PRODUCT
# ------------------------------------------------------------

start, end, block = get_class_block(
    text,
    "Product",
)


if "cost_price =" not in block:

    lines = block.splitlines()

    inserted = False
    result = []

    for line in lines:

        result.append(line)

        stripped = line.strip()

        if (
            not inserted
            and stripped.startswith(
                "price = models.DecimalField"
            )
        ):

            indent = (
                line[:len(line) - len(line.lstrip())]
            )

            result.extend([
                "",
                (
                    indent
                    + "cost_price = models.DecimalField("
                ),
                (
                    indent
                    + "    max_digits=10,"
                ),
                (
                    indent
                    + "    decimal_places=2,"
                ),
                (
                    indent
                    + "    null=True,"
                ),
                (
                    indent
                    + "    blank=True,"
                ),
                (
                    indent
                    + ")"
                ),
            ])

            inserted = True

    if not inserted:

        raise RuntimeError(
            "Could not locate Product.price."
        )

    block = "\n".join(result)

    print(
        "Added Product.cost_price"
    )


if "low_stock_threshold =" not in block:

    lines = block.splitlines()

    inserted = False
    result = []

    for line in lines:

        result.append(line)

        if (
            not inserted
            and line.strip().startswith(
                "reserved_stock ="
            )
        ):

            indent = (
                line[:len(line) - len(line.lstrip())]
            )

            result.extend([
                "",
                (
                    indent
                    + "low_stock_threshold = "
                    + "models.PositiveIntegerField("
                    + "default=5)"
                ),
            ])

            inserted = True

    if not inserted:

        raise RuntimeError(
            (
                "Could not locate "
                "Product.reserved_stock."
            )
        )

    block = "\n".join(result)

    print(
        "Added Product.low_stock_threshold"
    )


text = (
    text[:start]
    + block
    + text[end:]
)


# ------------------------------------------------------------
# PRODUCT VARIANT
# ------------------------------------------------------------

start, end, block = get_class_block(
    text,
    "ProductVariant",
)


if "cost_price =" not in block:

    lines = block.splitlines()

    inserted = False
    result = []

    for line in lines:

        result.append(line)

        if (
            not inserted
            and line.strip().startswith(
                "price = models.DecimalField"
            )
        ):

            indent = (
                line[:len(line) - len(line.lstrip())]
            )

            result.extend([
                "",
                (
                    indent
                    + "cost_price = models.DecimalField("
                ),
                (
                    indent
                    + "    max_digits=10,"
                ),
                (
                    indent
                    + "    decimal_places=2,"
                ),
                (
                    indent
                    + "    null=True,"
                ),
                (
                    indent
                    + "    blank=True,"
                ),
                (
                    indent
                    + ")"
                ),
            ])

            inserted = True

    if not inserted:

        raise RuntimeError(
            (
                "Could not locate "
                "ProductVariant.price."
            )
        )

    block = "\n".join(result)

    print(
        "Added ProductVariant.cost_price"
    )


if "low_stock_threshold =" not in block:

    lines = block.splitlines()

    inserted = False
    result = []

    for line in lines:

        result.append(line)

        if (
            not inserted
            and line.strip().startswith(
                "reserved_stock ="
            )
        ):

            indent = (
                line[:len(line) - len(line.lstrip())]
            )

            result.extend([
                "",
                (
                    indent
                    + "low_stock_threshold = "
                    + "models.PositiveIntegerField("
                    + "default=5)"
                ),
            ])

            inserted = True

    if not inserted:

        raise RuntimeError(
            (
                "Could not locate "
                "ProductVariant.reserved_stock."
            )
        )

    block = "\n".join(result)

    print(
        "Added ProductVariant.low_stock_threshold"
    )


text = (
    text[:start]
    + block
    + text[end:]
)


models_path.write_text(
    text,
    encoding="utf-8",
)

print(
    "Updated products/models.py"
)


# ============================================================
# 2. REMOVE STOCK FROM NORMAL PRODUCT FORMS
# ============================================================

text = forms_path.read_text(
    encoding="utf-8-sig"
)


# ------------------------------------------------------------
# ADMIN PRODUCT FORM
# ------------------------------------------------------------

start, end, block = get_class_block(
    text,
    "AdminProductForm",
)


# Remove stock from fields list.
block = re.sub(
    r'(?m)^[ \t]*"stock",[ \t]*\n',
    "",
    block,
    count=1,
)


if '"cost_price",' not in block:

    block = re.sub(
        r'(?m)^([ \t]*)"price",[ \t]*$',
        (
            r'\1"price",'
            '\n'
            r'\1"cost_price",'
            '\n'
            r'\1"low_stock_threshold",'
        ),
        block,
        count=1,
    )


if (
    'self.fields["cost_price"]'
    not in block
):

    init_code = r'''
    def __init__(
        self,
        *args,
        **kwargs,
    ):

        super().__init__(
            *args,
            **kwargs,
        )

        self.fields[
            "cost_price"
        ].required = False

        self.fields[
            "cost_price"
        ].widget.attrs.update(
            {
                "class": "form-control",
                "min": "0",
                "step": "0.01",
                "placeholder": (
                    "Business cost per unit"
                ),
            }
        )

        self.fields[
            "low_stock_threshold"
        ].widget.attrs.update(
            {
                "class": "form-control",
                "min": "0",
            }
        )

        self.fields[
            "low_stock_threshold"
        ].help_text = (
            "Inventory warning level. "
            "Stock is considered low when "
            "available quantity is at or "
            "below this number."
        )

'''

    position = block.find(
        "    def clean_sku"
    )

    if position == -1:

        raise RuntimeError(
            (
                "Could not locate "
                "AdminProductForm.clean_sku."
            )
        )

    block = (
        block[:position]
        + init_code
        + block[position:]
    )


text = (
    text[:start]
    + block
    + text[end:]
)


# ------------------------------------------------------------
# ADMIN PRODUCT VARIANT FORM
# ------------------------------------------------------------

start, end, block = get_class_block(
    text,
    "AdminProductVariantForm",
)


block = re.sub(
    r'(?m)^[ \t]*"stock",[ \t]*\n',
    "",
    block,
    count=1,
)


if '"cost_price",' not in block:

    block = re.sub(
        r'(?m)^([ \t]*)"price",[ \t]*$',
        (
            r'\1"price",'
            '\n'
            r'\1"cost_price",'
            '\n'
            r'\1"low_stock_threshold",'
        ),
        block,
        count=1,
    )


if (
    'self.fields["cost_price"]'
    not in block
):

    init_code = r'''
    def __init__(
        self,
        *args,
        **kwargs,
    ):

        super().__init__(
            *args,
            **kwargs,
        )

        self.fields[
            "cost_price"
        ].required = False

        self.fields[
            "cost_price"
        ].widget.attrs.update(
            {
                "class": "form-control",
                "min": "0",
                "step": "0.01",
                "placeholder": (
                    "Variant cost per unit"
                ),
            }
        )

        self.fields[
            "low_stock_threshold"
        ].widget.attrs.update(
            {
                "class": "form-control",
                "min": "0",
            }
        )

'''

    position = block.find(
        "    def clean_name"
    )

    if position == -1:

        raise RuntimeError(
            (
                "Could not locate "
                "AdminProductVariantForm.clean_name."
            )
        )

    block = (
        block[:position]
        + init_code
        + block[position:]
    )


text = (
    text[:start]
    + block
    + text[end:]
)


forms_path.write_text(
    text,
    encoding="utf-8",
)

print(
    "Removed direct stock editing "
    "from Product and Variant forms"
)


# ============================================================
# 3. INVENTORY VIEWS + VALUATION + CSV EXPORT
# ============================================================

inventory_views.write_text(
r'''
import csv

from decimal import Decimal

from django.contrib import messages

from django.contrib.admin.views.decorators import (
    staff_member_required,
)

from django.core.paginator import Paginator

from django.db.models import Q

from django.http import HttpResponse

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


def calculate_inventory_summary():

    products = Product.objects.all()

    variants = (
        ProductVariant.objects
        .select_related("product")
        .all()
    )

    low_stock_count = 0
    out_stock_count = 0

    missing_cost_count = 0

    inventory_value = Decimal(
        "0.00"
    )

    for product in products:

        available = (
            product.available_stock
        )

        threshold = (
            product.low_stock_threshold
        )

        if available == 0:

            out_stock_count += 1

        elif available <= threshold:

            low_stock_count += 1

        if product.stock > 0:

            if product.cost_price is None:

                missing_cost_count += 1

            else:

                inventory_value += (
                    Decimal(product.stock)
                    * product.cost_price
                )

    for variant in variants:

        available = (
            variant.available_stock
        )

        threshold = (
            variant.low_stock_threshold
        )

        if available == 0:

            out_stock_count += 1

        elif available <= threshold:

            low_stock_count += 1

        if variant.stock > 0:

            if variant.cost_price is None:

                missing_cost_count += 1

            else:

                inventory_value += (
                    Decimal(variant.stock)
                    * variant.cost_price
                )

    return {
        "low_stock_count": (
            low_stock_count
        ),
        "out_stock_count": (
            out_stock_count
        ),
        "missing_cost_count": (
            missing_cost_count
        ),
        "inventory_value": (
            inventory_value
        ),
    }


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

        products = (
            products.filter(
                Q(name__icontains=query)
                | Q(sku__icontains=query)
                | Q(
                    category__name__icontains=query
                )
                | Q(
                    brand__name__icontains=query
                )
                | Q(
                    variants__sku__icontains=query
                )
                | Q(
                    variants__name__icontains=query
                )
            )
            .distinct()
        )

    product_rows = []

    for product in products:

        available = (
            product.available_stock
        )

        threshold = (
            product.low_stock_threshold
        )

        if (
            stock_filter == "low"
            and not (
                0
                < available
                <= threshold
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

        if product.cost_price is not None:

            product.inventory_value = (
                Decimal(product.stock)
                * product.cost_price
            )

        else:

            product.inventory_value = None

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

    summary = (
        calculate_inventory_summary()
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
            "selected_stock": (
                stock_filter
            ),
            "total_products": (
                Product.objects.count()
            ),
            "low_stock_count": (
                summary[
                    "low_stock_count"
                ]
            ),
            "out_stock_count": (
                summary[
                    "out_stock_count"
                ]
            ),
            "missing_cost_count": (
                summary[
                    "missing_cost_count"
                ]
            ),
            "inventory_value": (
                summary[
                    "inventory_value"
                ]
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

    if product.cost_price is not None:

        product.inventory_value = (
            Decimal(product.stock)
            * product.cost_price
        )

    else:

        product.inventory_value = None

    variants = list(
        product.variants.all()
    )

    for variant in variants:

        if variant.cost_price is not None:

            variant.inventory_value = (
                Decimal(variant.stock)
                * variant.cost_price
            )

        else:

            variant.inventory_value = None

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
            "variants": variants,
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

        form = (
            InventoryAdjustmentForm()
        )

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

        form = (
            InventoryAdjustmentForm()
        )

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

    movement_type = (
        request.GET.get(
            "type",
            "",
        )
    )

    if query:

        movements = movements.filter(
            Q(
                product__name__icontains=query
            )
            | Q(
                variant__product__name__icontains=query
            )
            | Q(
                variant__name__icontains=query
            )
            | Q(
                reference__icontains=query
            )
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
            "selected_type": (
                movement_type
            ),
            "movement_types": (
                InventoryMovement
                .MOVEMENT_TYPES
            ),
        },
    )


@staff_member_required
def inventory_export_csv(
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
        'filename="inventory.csv"'
    )

    response.write(
        "\ufeff"
    )

    writer = csv.writer(
        response
    )

    writer.writerow([
        "Type",
        "Product",
        "Variant",
        "SKU",
        "Physical Stock",
        "Reserved Stock",
        "Available Stock",
        "Low Stock Threshold",
        "Cost Price",
        "Inventory Value",
        "Status",
    ])

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

    for product in products:

        cost = product.cost_price

        value = (
            Decimal(product.stock)
            * cost
            if cost is not None
            else ""
        )

        available = (
            product.available_stock
        )

        if available == 0:
            status = "OUT OF STOCK"

        elif (
            available
            <= product.low_stock_threshold
        ):
            status = "LOW STOCK"

        else:
            status = "OK"

        writer.writerow([
            "Product",
            product.name,
            "",
            product.sku,
            product.stock,
            product.reserved_stock,
            available,
            product.low_stock_threshold,
            (
                cost
                if cost is not None
                else ""
            ),
            value,
            status,
        ])

        for variant in (
            product.variants.all()
        ):

            variant_cost = (
                variant.cost_price
            )

            variant_value = (
                Decimal(variant.stock)
                * variant_cost
                if variant_cost
                is not None
                else ""
            )

            variant_available = (
                variant.available_stock
            )

            if variant_available == 0:

                variant_status = (
                    "OUT OF STOCK"
                )

            elif (
                variant_available
                <= variant.low_stock_threshold
            ):

                variant_status = (
                    "LOW STOCK"
                )

            else:

                variant_status = "OK"

            writer.writerow([
                "Variant",
                product.name,
                variant.name,
                variant.sku,
                variant.stock,
                variant.reserved_stock,
                variant_available,
                (
                    variant
                    .low_stock_threshold
                ),
                (
                    variant_cost
                    if variant_cost
                    is not None
                    else ""
                ),
                variant_value,
                variant_status,
            ])

    return response
'''.strip() + "\n",
    encoding="utf-8",
)

print(
    "Updated inventory/views.py"
)


# ============================================================
# 4. INVENTORY URLS
# ============================================================

inventory_urls.write_text(
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
        "export/",
        views.inventory_export_csv,
        name="inventory_export_csv",
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
        (
            "products/<int:pk>/variants/"
            "<int:variant_id>/adjust/"
        ),
        views.inventory_variant_adjust,
        name="inventory_variant_adjust",
    ),
]
'''.strip() + "\n",
    encoding="utf-8",
)

print(
    "Updated inventory/urls.py"
)


# ============================================================
# 5. INVENTORY DASHBOARD TEMPLATE
# ============================================================

inventory_list.write_text(
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
            Stock control, valuation and movement history.
        </p>

    </div>

    <div class="d-flex gap-2 flex-wrap">

        <a
            href="{% url 'inventory_export_csv' %}"
            class="btn btn-outline-success"
        >
            <i class="bi bi-file-earmark-spreadsheet"></i>
            Export CSV
        </a>

        <a
            href="{% url 'inventory_movement_list' %}"
            class="btn btn-outline-primary"
        >
            <i class="bi bi-clock-history"></i>
            Stock History
        </a>

    </div>

</div>


<div class="row g-3 mb-4">

    <div class="col-md-4 col-xl">

        <div class="dashboard-card mini-stat">

            <span>
                Products
            </span>

            <strong>
                {{ total_products }}
            </strong>

        </div>

    </div>


    <div class="col-md-4 col-xl">

        <div class="dashboard-card mini-stat">

            <span>
                Low Stock Items
            </span>

            <strong>
                {{ low_stock_count }}
            </strong>

        </div>

    </div>


    <div class="col-md-4 col-xl">

        <div class="dashboard-card mini-stat">

            <span>
                Out of Stock
            </span>

            <strong>
                {{ out_stock_count }}
            </strong>

        </div>

    </div>


    <div class="col-md-6 col-xl">

        <div class="dashboard-card mini-stat">

            <span>
                Inventory Cost Value
            </span>

            <strong>
                KES {{ inventory_value|floatformat:2 }}
            </strong>

        </div>

    </div>


    <div class="col-md-6 col-xl">

        <div class="dashboard-card mini-stat">

            <span>
                Missing Cost Prices
            </span>

            <strong>
                {{ missing_cost_count }}
            </strong>

        </div>

    </div>

</div>


{% if missing_cost_count %}

<div class="alert alert-warning">

    <i class="bi bi-exclamation-triangle"></i>

    {{ missing_cost_count }}
    stocked item{{ missing_cost_count|pluralize }}
    have no cost price.

    They are excluded from the inventory valuation.

</div>

{% endif %}


<div class="dashboard-card mb-4">

    <form method="GET">

        <div class="row g-3">

            <div class="col-lg-8">

                <label class="form-label">
                    Search
                </label>

                <input
                    type="text"
                    name="q"
                    value="{{ query }}"
                    class="form-control"
                    placeholder="Product, SKU, variant, brand..."
                >

            </div>

            <div class="col-lg-4">

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
                    <th>Alert At</th>
                    <th>Cost</th>
                    <th>Stock Value</th>
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

                            {% if product.variants.count %}

                                <small class="text-muted">
                                    {{ product.variants.count }}
                                    variant{{ product.variants.count|pluralize }}
                                </small>

                            {% endif %}

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

                            {% elif product.available_stock <= product.low_stock_threshold %}

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
                            {{ product.low_stock_threshold }}
                        </td>


                        <td>

                            {% if product.cost_price != None %}

                                KES {{ product.cost_price|floatformat:2 }}

                            {% else %}

                                <span class="badge text-bg-warning">
                                    Missing
                                </span>

                            {% endif %}

                        </td>


                        <td>

                            {% if product.inventory_value != None %}

                                KES {{ product.inventory_value|floatformat:2 }}

                            {% else %}

                                —
                            {% endif %}

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
                            colspan="8"
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

        <a href="{% url 'inventory_movement_list' %}">
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

print(
    "Updated inventory dashboard template"
)


# ============================================================
# 6. INVENTORY PRODUCT DETAIL TEMPLATE
# ============================================================

inventory_detail.write_text(
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
            href="{% url 'admin_product_edit' product.pk %}"
            class="btn btn-outline-secondary"
        >
            Product Settings
        </a>

        <a
            href="{% url 'inventory_dashboard' %}"
            class="btn btn-outline-secondary"
        >
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

    <div class="col-md-4 col-xl">

        <div class="dashboard-card mini-stat">

            <span>
                Physical
            </span>

            <strong>
                {{ product.stock }}
            </strong>

        </div>

    </div>


    <div class="col-md-4 col-xl">

        <div class="dashboard-card mini-stat">

            <span>
                Reserved
            </span>

            <strong>
                {{ product.reserved_stock }}
            </strong>

        </div>

    </div>


    <div class="col-md-4 col-xl">

        <div class="dashboard-card mini-stat">

            <span>
                Available
            </span>

            <strong>
                {{ product.available_stock }}
            </strong>

        </div>

    </div>


    <div class="col-md-6 col-xl">

        <div class="dashboard-card mini-stat">

            <span>
                Low Stock Alert
            </span>

            <strong>
                {{ product.low_stock_threshold }}
            </strong>

        </div>

    </div>


    <div class="col-md-6 col-xl">

        <div class="dashboard-card mini-stat">

            <span>
                Cost Value
            </span>

            <strong>

                {% if product.inventory_value != None %}

                    KES {{ product.inventory_value|floatformat:2 }}

                {% else %}

                    Not configured

                {% endif %}

            </strong>

        </div>

    </div>

</div>


<div class="alert alert-info">

    <i class="bi bi-info-circle"></i>

    Stock quantities cannot be changed from
    Product Settings.

    Use <strong>Adjust Stock</strong> so every
    change remains in the inventory audit trail.

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
                    <th>Alert At</th>
                    <th>Cost</th>
                    <th>Value</th>
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

                            {% if variant.available_stock == 0 %}

                                <span class="badge text-bg-danger">
                                    0
                                </span>

                            {% elif variant.available_stock <= variant.low_stock_threshold %}

                                <span class="badge text-bg-warning">
                                    {{ variant.available_stock }}
                                </span>

                            {% else %}

                                <span class="badge text-bg-success">
                                    {{ variant.available_stock }}
                                </span>

                            {% endif %}

                        </td>

                        <td>
                            {{ variant.low_stock_threshold }}
                        </td>

                        <td>

                            {% if variant.cost_price != None %}

                                KES {{ variant.cost_price|floatformat:2 }}

                            {% else %}
                                —
                            {% endif %}

                        </td>

                        <td>

                            {% if variant.inventory_value != None %}

                                KES {{ variant.inventory_value|floatformat:2 }}

                            {% else %}
                                —
                            {% endif %}

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

print(
    "Updated inventory detail template"
)


# ============================================================
# 7. VARIANT PRODUCT FORM TEMPLATE
# ============================================================

text = variant_template.read_text(
    encoding="utf-8-sig"
)

# Remove old stock-input section if present.
pattern = re.compile(
    r'''
    <div\s+class="col-md-6">\s*
    <label\s+class="form-label">\s*
    Physical\s+Stock\s+\*\s*
    </label>.*?
    </div>
    ''',
    re.S | re.X,
)

text, count = pattern.subn(
    r'''
                    <div class="col-md-6">

                        <label class="form-label">
                            Inventory
                        </label>

                        <div class="form-control bg-body-secondary">

                            {% if variant %}

                                Physical:
                                {{ variant.stock }}

                                |
                                Reserved:
                                {{ variant.reserved_stock }}

                            {% else %}

                                New variants start with
                                zero stock.

                            {% endif %}

                        </div>

                        <div class="form-text">

                            Use Inventory Management
                            to change stock quantity.

                        </div>

                    </div>
''',
    text,
    count=1,
)

variant_template.write_text(
    text,
    encoding="utf-8",
)

print(
    (
        "Updated variant form template "
        f"(stock blocks replaced: {count})"
    )
)


print()
print("=" * 65)
print("PHASE 4.1 PATCH COMPLETE")
print("=" * 65)
print()
print("Next:")
print("python manage.py makemigrations products")
print("python manage.py migrate")
print("python manage.py check")
