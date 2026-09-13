import csv

from decimal import Decimal

from django.contrib import messages

from accounts.staff_auth import (
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
