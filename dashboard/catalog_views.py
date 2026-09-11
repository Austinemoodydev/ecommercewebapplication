from django.contrib import messages

from django.contrib.admin.views.decorators import (
    staff_member_required,
)

from django.core.paginator import Paginator

from django.db.models import (
    Count,
    Q,
)

from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from django.utils.text import slugify

from categories.models import Category

from products.models import (
    Brand,
    Product,
)

from .catalog_forms import (
    AdminBrandForm,
    AdminCategoryForm,
)


# ============================================================
# SLUG HELPERS
# ============================================================

def generate_unique_category_slug(
    name,
    category_id=None,
):

    base_slug = slugify(name)

    if not base_slug:
        base_slug = "category"

    candidate = base_slug

    counter = 2

    while True:

        queryset = Category.objects.filter(
            slug=candidate
        )

        if category_id:

            queryset = queryset.exclude(
                pk=category_id
            )

        if not queryset.exists():
            return candidate

        candidate = (
            f"{base_slug}-{counter}"
        )

        counter += 1


def generate_unique_brand_slug(
    name,
    brand_id=None,
):

    base_slug = slugify(name)

    if not base_slug:
        base_slug = "brand"

    candidate = base_slug

    counter = 2

    while True:

        queryset = Brand.objects.filter(
            slug=candidate
        )

        if brand_id:

            queryset = queryset.exclude(
                pk=brand_id
            )

        if not queryset.exists():
            return candidate

        candidate = (
            f"{base_slug}-{counter}"
        )

        counter += 1


# ============================================================
# CATEGORY LIST
# ============================================================

@staff_member_required
def admin_category_list(request):

    categories = (
        Category.objects
        .annotate(
            product_count=Count(
                "products"
            ),
            active_product_count=Count(
                "products",
                filter=Q(
                    products__is_active=True
                ),
            ),
        )
        .order_by("name")
    )

    query = request.GET.get(
        "q",
        "",
    ).strip()

    if query:

        categories = categories.filter(
            Q(name__icontains=query)
            | Q(
                description__icontains=query
            )
        )

    status = request.GET.get(
        "status",
        "",
    )

    if status == "active":

        categories = categories.filter(
            is_active=True
        )

    elif status == "inactive":

        categories = categories.filter(
            is_active=False
        )

    counts = {

        "all": Category.objects.count(),

        "active": Category.objects.filter(
            is_active=True
        ).count(),

        "inactive": Category.objects.filter(
            is_active=False
        ).count(),
    }

    paginator = Paginator(
        categories,
        20,
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        (
            "dashboard/admin/catalog/"
            "categories.html"
        ),
        {
            "categories": (
                page_obj.object_list
            ),
            "page_obj": page_obj,
            "query": query,
            "selected_status": status,
            "counts": counts,
        },
    )


# ============================================================
# CREATE CATEGORY
# ============================================================

@staff_member_required
def admin_category_create(request):

    if request.method == "POST":

        form = AdminCategoryForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            category = form.save(
                commit=False
            )

            category.slug = (
                generate_unique_category_slug(
                    category.name
                )
            )

            category.save()

            messages.success(
                request,
                (
                    f'Category "{category.name}" '
                    "created successfully."
                ),
            )

            return redirect(
                "admin_category_list"
            )

    else:

        form = AdminCategoryForm()

    return render(
        request,
        "dashboard/admin/catalog/form.html",
        {
            "form": form,
            "page_title": (
                "Add Category"
            ),
            "submit_text": (
                "Create Category"
            ),
            "return_url_name": (
                "admin_category_list"
            ),
        },
    )


# ============================================================
# EDIT CATEGORY
# ============================================================

@staff_member_required
def admin_category_edit(
    request,
    pk,
):

    category = get_object_or_404(
        Category,
        pk=pk,
    )

    old_name = category.name

    if request.method == "POST":

        form = AdminCategoryForm(
            request.POST,
            request.FILES,
            instance=category,
        )

        if form.is_valid():

            category = form.save(
                commit=False
            )

            if category.name != old_name:

                category.slug = (
                    generate_unique_category_slug(
                        category.name,
                        category.pk,
                    )
                )

            category.save()

            messages.success(
                request,
                (
                    f'Category "{category.name}" '
                    "updated successfully."
                ),
            )

            return redirect(
                "admin_category_list"
            )

    else:

        form = AdminCategoryForm(
            instance=category
        )

    return render(
        request,
        "dashboard/admin/catalog/form.html",
        {
            "form": form,
            "category": category,
            "page_title": (
                "Edit Category"
            ),
            "submit_text": (
                "Save Category"
            ),
            "return_url_name": (
                "admin_category_list"
            ),
        },
    )


# ============================================================
# CATEGORY ACTIVE / HIDDEN
# ============================================================

@staff_member_required
def admin_category_toggle(
    request,
    pk,
):

    if request.method != "POST":

        return redirect(
            "admin_category_list"
        )

    category = get_object_or_404(
        Category,
        pk=pk,
    )

    # Do not hide a category while it still
    # contains active products. This avoids
    # confusing storefront behaviour.
    if category.is_active:

        active_products = (
            category.products
            .filter(
                is_active=True
            )
            .count()
        )

        if active_products:

            messages.error(
                request,
                (
                    f'Cannot hide "{category.name}". '
                    f"It still contains "
                    f"{active_products} active "
                    "product(s). Move or hide "
                    "those products first."
                ),
            )

            return redirect(
                "admin_category_list"
            )

    category.is_active = (
        not category.is_active
    )

    category.save(
        update_fields=[
            "is_active"
        ]
    )

    messages.success(
        request,
        (
            f'Category "{category.name}" '
            f'is now '
            f'{"active" if category.is_active else "hidden"}.'
        ),
    )

    return redirect(
        "admin_category_list"
    )


# ============================================================
# BRAND LIST
# ============================================================

@staff_member_required
def admin_brand_list(request):

    brands = (
        Brand.objects
        .annotate(
            product_count=Count(
                "products"
            ),
            active_product_count=Count(
                "products",
                filter=Q(
                    products__is_active=True
                ),
            ),
        )
        .order_by("name")
    )

    query = request.GET.get(
        "q",
        "",
    ).strip()

    if query:

        brands = brands.filter(
            name__icontains=query
        )

    status = request.GET.get(
        "status",
        "",
    )

    if status == "active":

        brands = brands.filter(
            is_active=True
        )

    elif status == "inactive":

        brands = brands.filter(
            is_active=False
        )

    counts = {

        "all": Brand.objects.count(),

        "active": Brand.objects.filter(
            is_active=True
        ).count(),

        "inactive": Brand.objects.filter(
            is_active=False
        ).count(),
    }

    paginator = Paginator(
        brands,
        20,
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        (
            "dashboard/admin/catalog/"
            "brands.html"
        ),
        {
            "brands": (
                page_obj.object_list
            ),
            "page_obj": page_obj,
            "query": query,
            "selected_status": status,
            "counts": counts,
        },
    )


# ============================================================
# CREATE BRAND
# ============================================================

@staff_member_required
def admin_brand_create(request):

    if request.method == "POST":

        form = AdminBrandForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            brand = form.save(
                commit=False
            )

            brand.slug = (
                generate_unique_brand_slug(
                    brand.name
                )
            )

            brand.save()

            messages.success(
                request,
                (
                    f'Brand "{brand.name}" '
                    "created successfully."
                ),
            )

            return redirect(
                "admin_brand_list"
            )

    else:

        form = AdminBrandForm()

    return render(
        request,
        "dashboard/admin/catalog/form.html",
        {
            "form": form,
            "page_title": (
                "Add Brand"
            ),
            "submit_text": (
                "Create Brand"
            ),
            "return_url_name": (
                "admin_brand_list"
            ),
        },
    )


# ============================================================
# EDIT BRAND
# ============================================================

@staff_member_required
def admin_brand_edit(
    request,
    pk,
):

    brand = get_object_or_404(
        Brand,
        pk=pk,
    )

    old_name = brand.name

    if request.method == "POST":

        form = AdminBrandForm(
            request.POST,
            request.FILES,
            instance=brand,
        )

        if form.is_valid():

            brand = form.save(
                commit=False
            )

            if brand.name != old_name:

                brand.slug = (
                    generate_unique_brand_slug(
                        brand.name,
                        brand.pk,
                    )
                )

            brand.save()

            messages.success(
                request,
                (
                    f'Brand "{brand.name}" '
                    "updated successfully."
                ),
            )

            return redirect(
                "admin_brand_list"
            )

    else:

        form = AdminBrandForm(
            instance=brand
        )

    return render(
        request,
        "dashboard/admin/catalog/form.html",
        {
            "form": form,
            "brand": brand,
            "page_title": (
                "Edit Brand"
            ),
            "submit_text": (
                "Save Brand"
            ),
            "return_url_name": (
                "admin_brand_list"
            ),
        },
    )


# ============================================================
# BRAND ACTIVE / HIDDEN
# ============================================================

@staff_member_required
def admin_brand_toggle(
    request,
    pk,
):

    if request.method != "POST":

        return redirect(
            "admin_brand_list"
        )

    brand = get_object_or_404(
        Brand,
        pk=pk,
    )

    brand.is_active = (
        not brand.is_active
    )

    brand.save(
        update_fields=[
            "is_active"
        ]
    )

    messages.success(
        request,
        (
            f'Brand "{brand.name}" '
            f'is now '
            f'{"active" if brand.is_active else "hidden"}.'
        ),
    )

    return redirect(
        "admin_brand_list"
    )
