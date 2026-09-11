from pathlib import Path
import shutil


ROOT = Path.cwd()

products_models = ROOT / "products" / "models.py"
dashboard_views = ROOT / "dashboard" / "views.py"
dashboard_urls = ROOT / "dashboard" / "urls.py"

catalog_forms = ROOT / "dashboard" / "catalog_forms.py"
catalog_views = ROOT / "dashboard" / "catalog_views.py"

template_dir = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "catalog"
)

category_list = template_dir / "categories.html"
brand_list = template_dir / "brands.html"
catalog_form = template_dir / "form.html"


def backup(path):

    if path.exists():

        target = Path(
            str(path) + ".phase35backup"
        )

        shutil.copy2(
            path,
            target,
        )

        print(
            f"Backup created: {target}"
        )


# ============================================================
# BACKUPS
# ============================================================

for path in [
    products_models,
    dashboard_views,
    dashboard_urls,
]:

    backup(path)


# ============================================================
# 1. ADD is_active TO BRAND
# ============================================================

text = products_models.read_text(
    encoding="utf-8-sig"
)

if (
    "class Brand(models.Model):"
    in text
    and "class Brand(models.Model):\n"
    in text
):

    brand_start = text.index(
        "class Brand(models.Model):"
    )

    product_start = text.index(
        "class Product(models.Model):"
    )

    brand_block = text[
        brand_start:product_start
    ]

    if "is_active =" not in brand_block:

        old = (
            '    logo = models.ImageField('
            'upload_to="brands/", '
            'blank=True, null=True)\n'
        )

        new = (
            '    logo = models.ImageField('
            'upload_to="brands/", '
            'blank=True, null=True)\n'
            '\n'
            '    is_active = '
            'models.BooleanField(default=True)\n'
        )

        if old not in text:

            raise RuntimeError(
                "Could not locate Brand.logo "
                "in products/models.py"
            )

        text = text.replace(
            old,
            new,
            1,
        )

        products_models.write_text(
            text,
            encoding="utf-8",
        )

        print(
            "Added Brand.is_active"
        )

    else:

        print(
            "Brand.is_active already exists"
        )


# ============================================================
# 2. CATALOG FORMS
# ============================================================

catalog_forms.write_text(
r'''
from django import forms
from django.core.exceptions import ValidationError

from categories.models import Category
from products.models import Brand


class AdminCategoryForm(forms.ModelForm):

    class Meta:

        model = Category

        fields = [
            "name",
            "description",
            "image",
            "is_active",
        ]

        widgets = {

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "e.g. Laptops"
                    ),
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": (
                        "Category description..."
                    ),
                }
            ),

            "image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def clean_name(self):

        name = (
            self.cleaned_data["name"]
            .strip()
        )

        queryset = (
            Category.objects
            .filter(
                name__iexact=name
            )
        )

        if self.instance.pk:

            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():

            raise ValidationError(
                (
                    "A category with this "
                    "name already exists."
                )
            )

        return name


class AdminBrandForm(forms.ModelForm):

    class Meta:

        model = Brand

        fields = [
            "name",
            "logo",
            "is_active",
        ]

        widgets = {

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "e.g. HP"
                    ),
                }
            ),

            "logo": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def clean_name(self):

        name = (
            self.cleaned_data["name"]
            .strip()
        )

        queryset = (
            Brand.objects
            .filter(
                name__iexact=name
            )
        )

        if self.instance.pk:

            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():

            raise ValidationError(
                (
                    "A brand with this "
                    "name already exists."
                )
            )

        return name
'''.strip() + "\n",
    encoding="utf-8",
)

print(
    "Created dashboard/catalog_forms.py"
)


# ============================================================
# 3. CATALOG VIEWS
# ============================================================

catalog_views.write_text(
r'''
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
'''.strip() + "\n",
    encoding="utf-8",
)

print(
    "Created dashboard/catalog_views.py"
)


# ============================================================
# 4. EXPOSE CATALOG VIEWS THROUGH dashboard.views
# ============================================================

views_text = dashboard_views.read_text(
    encoding="utf-8-sig"
)

import_marker = (
    "from .catalog_views import ("
)

if import_marker not in views_text:

    views_text += r'''


# ============================================================
# CATALOG MANAGEMENT
# ============================================================

from .catalog_views import (
    admin_category_list,
    admin_category_create,
    admin_category_edit,
    admin_category_toggle,
    admin_brand_list,
    admin_brand_create,
    admin_brand_edit,
    admin_brand_toggle,
)
'''

    dashboard_views.write_text(
        views_text,
        encoding="utf-8",
    )

    print(
        "Connected catalog views "
        "to dashboard/views.py"
    )

else:

    print(
        "Catalog views already connected"
    )


# ============================================================
# 5. INSERT URLS INSIDE urlpatterns
# ============================================================

urls_text = dashboard_urls.read_text(
    encoding="utf-8-sig"
)

if (
    'name="admin_category_list"'
    not in urls_text
):

    catalog_urls = r'''

    # =========================================================
    # CATEGORY MANAGEMENT
    # =========================================================

    path(
        "admin/categories/",
        views.admin_category_list,
        name="admin_category_list",
    ),

    path(
        "admin/categories/add/",
        views.admin_category_create,
        name="admin_category_create",
    ),

    path(
        "admin/categories/<int:pk>/edit/",
        views.admin_category_edit,
        name="admin_category_edit",
    ),

    path(
        "admin/categories/<int:pk>/toggle/",
        views.admin_category_toggle,
        name="admin_category_toggle",
    ),


    # =========================================================
    # BRAND MANAGEMENT
    # =========================================================

    path(
        "admin/brands/",
        views.admin_brand_list,
        name="admin_brand_list",
    ),

    path(
        "admin/brands/add/",
        views.admin_brand_create,
        name="admin_brand_create",
    ),

    path(
        "admin/brands/<int:pk>/edit/",
        views.admin_brand_edit,
        name="admin_brand_edit",
    ),

    path(
        "admin/brands/<int:pk>/toggle/",
        views.admin_brand_toggle,
        name="admin_brand_toggle",
    ),
'''

    # Insert immediately before the final closing
    # bracket of urlpatterns.
    closing = urls_text.rfind(
        "\n]"
    )

    if closing == -1:

        raise RuntimeError(
            (
                "Could not locate final ] "
                "in dashboard/urls.py"
            )
        )

    urls_text = (
        urls_text[:closing]
        + catalog_urls
        + urls_text[closing:]
    )

    dashboard_urls.write_text(
        urls_text,
        encoding="utf-8",
    )

    print(
        "Added category and brand URLs"
    )

else:

    print(
        "Catalog URLs already exist"
    )


# ============================================================
# 6. TEMPLATES
# ============================================================

template_dir.mkdir(
    parents=True,
    exist_ok=True,
)


category_list.write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Categories | Store Management
{% endblock %}

{% block page_heading %}
Categories
{% endblock %}

{% block admin_content %}

<div class="d-flex justify-content-between align-items-center flex-wrap gap-3 mb-4">

    <div>
        <h1 class="h3 mb-1">
            Category Management
        </h1>

        <p class="text-muted mb-0">
            Organize products into customer-friendly groups.
        </p>
    </div>

    <a
        href="{% url 'admin_category_create' %}"
        class="btn btn-primary"
    >
        <i class="bi bi-plus-lg"></i>
        Add Category
    </a>

</div>


<div class="row g-3 mb-4">

    <div class="col-md-4">

        <div class="dashboard-card mini-stat">
            <span>All Categories</span>
            <strong>{{ counts.all }}</strong>
        </div>

    </div>

    <div class="col-md-4">

        <div class="dashboard-card mini-stat">
            <span>Active</span>
            <strong>{{ counts.active }}</strong>
        </div>

    </div>

    <div class="col-md-4">

        <div class="dashboard-card mini-stat">
            <span>Hidden</span>
            <strong>{{ counts.inactive }}</strong>
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
                    placeholder="Search category..."
                >

            </div>

            <div class="col-md-4">

                <label class="form-label">
                    Status
                </label>

                <select
                    name="status"
                    class="form-select"
                >
                    <option value="">
                        All
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
                        Hidden
                    </option>
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
                href="{% url 'admin_category_list' %}"
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
                    <th>Category</th>
                    <th>Products</th>
                    <th>Active Products</th>
                    <th>Status</th>
                    <th></th>
                </tr>

            </thead>

            <tbody>

                {% for category in categories %}

                    <tr>

                        <td>

                            <div class="d-flex align-items-center gap-3">

                                {% if category.image %}

                                    <img
                                        src="{{ category.image.url }}"
                                        alt="{{ category.name }}"
                                        width="50"
                                        height="50"
                                        class="rounded"
                                        style="object-fit:cover;"
                                    >

                                {% endif %}

                                <div>

                                    <strong>
                                        {{ category.name }}
                                    </strong>

                                    {% if category.description %}

                                        <small class="text-muted d-block">
                                            {{ category.description|truncatechars:80 }}
                                        </small>

                                    {% endif %}

                                </div>

                            </div>

                        </td>

                        <td>
                            {{ category.product_count }}
                        </td>

                        <td>
                            {{ category.active_product_count }}
                        </td>

                        <td>

                            {% if category.is_active %}

                                <span class="badge text-bg-success">
                                    Active
                                </span>

                            {% else %}

                                <span class="badge text-bg-secondary">
                                    Hidden
                                </span>

                            {% endif %}

                        </td>

                        <td>

                            <div class="d-flex gap-2 justify-content-end">

                                <a
                                    href="{% url 'admin_category_edit' category.pk %}"
                                    class="btn btn-sm btn-outline-primary"
                                >
                                    Edit
                                </a>

                                <form
                                    method="POST"
                                    action="{% url 'admin_category_toggle' category.pk %}"
                                >

                                    {% csrf_token %}

                                    {% if category.is_active %}

                                        <button
                                            type="submit"
                                            class="btn btn-sm btn-outline-danger"
                                        >
                                            Hide
                                        </button>

                                    {% else %}

                                        <button
                                            type="submit"
                                            class="btn btn-sm btn-success"
                                        >
                                            Activate
                                        </button>

                                    {% endif %}

                                </form>

                            </div>

                        </td>

                    </tr>

                {% empty %}

                    <tr>

                        <td
                            colspan="5"
                            class="text-center text-muted py-5"
                        >
                            No categories found.
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


brand_list.write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Brands | Store Management
{% endblock %}

{% block page_heading %}
Brands
{% endblock %}

{% block admin_content %}

<div class="d-flex justify-content-between align-items-center flex-wrap gap-3 mb-4">

    <div>

        <h1 class="h3 mb-1">
            Brand Management
        </h1>

        <p class="text-muted mb-0">
            Manage brands used across your product catalogue.
        </p>

    </div>

    <a
        href="{% url 'admin_brand_create' %}"
        class="btn btn-primary"
    >
        <i class="bi bi-plus-lg"></i>
        Add Brand
    </a>

</div>


<div class="row g-3 mb-4">

    <div class="col-md-4">
        <div class="dashboard-card mini-stat">
            <span>All Brands</span>
            <strong>{{ counts.all }}</strong>
        </div>
    </div>

    <div class="col-md-4">
        <div class="dashboard-card mini-stat">
            <span>Active</span>
            <strong>{{ counts.active }}</strong>
        </div>
    </div>

    <div class="col-md-4">
        <div class="dashboard-card mini-stat">
            <span>Hidden</span>
            <strong>{{ counts.inactive }}</strong>
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
                    placeholder="Search brand..."
                >

            </div>

            <div class="col-md-4">

                <label class="form-label">
                    Status
                </label>

                <select
                    name="status"
                    class="form-select"
                >

                    <option value="">
                        All
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
                        Hidden
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
                href="{% url 'admin_brand_list' %}"
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
                    <th>Brand</th>
                    <th>Products</th>
                    <th>Active Products</th>
                    <th>Status</th>
                    <th></th>
                </tr>

            </thead>

            <tbody>

                {% for brand in brands %}

                    <tr>

                        <td>

                            <div class="d-flex align-items-center gap-3">

                                {% if brand.logo %}

                                    <img
                                        src="{{ brand.logo.url }}"
                                        alt="{{ brand.name }}"
                                        width="50"
                                        height="50"
                                        class="rounded"
                                        style="object-fit:contain;"
                                    >

                                {% endif %}

                                <strong>
                                    {{ brand.name }}
                                </strong>

                            </div>

                        </td>

                        <td>
                            {{ brand.product_count }}
                        </td>

                        <td>
                            {{ brand.active_product_count }}
                        </td>

                        <td>

                            {% if brand.is_active %}

                                <span class="badge text-bg-success">
                                    Active
                                </span>

                            {% else %}

                                <span class="badge text-bg-secondary">
                                    Hidden
                                </span>

                            {% endif %}

                        </td>

                        <td>

                            <div class="d-flex gap-2 justify-content-end">

                                <a
                                    href="{% url 'admin_brand_edit' brand.pk %}"
                                    class="btn btn-sm btn-outline-primary"
                                >
                                    Edit
                                </a>

                                <form
                                    method="POST"
                                    action="{% url 'admin_brand_toggle' brand.pk %}"
                                >

                                    {% csrf_token %}

                                    {% if brand.is_active %}

                                        <button
                                            type="submit"
                                            class="btn btn-sm btn-outline-danger"
                                        >
                                            Hide
                                        </button>

                                    {% else %}

                                        <button
                                            type="submit"
                                            class="btn btn-sm btn-success"
                                        >
                                            Activate
                                        </button>

                                    {% endif %}

                                </form>

                            </div>

                        </td>

                    </tr>

                {% empty %}

                    <tr>

                        <td
                            colspan="5"
                            class="text-center text-muted py-5"
                        >
                            No brands found.
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


catalog_form.write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
{{ page_title }} | Store Management
{% endblock %}

{% block page_heading %}
{{ page_title }}
{% endblock %}

{% block admin_content %}

<div class="d-flex justify-content-between align-items-center mb-4">

    <div>

        <h1 class="h3 mb-1">
            {{ page_title }}
        </h1>

    </div>

    {% if return_url_name == "admin_category_list" %}

        <a
            href="{% url 'admin_category_list' %}"
            class="btn btn-outline-secondary"
        >
            <i class="bi bi-arrow-left"></i>
            Categories
        </a>

    {% else %}

        <a
            href="{% url 'admin_brand_list' %}"
            class="btn btn-outline-secondary"
        >
            <i class="bi bi-arrow-left"></i>
            Brands
        </a>

    {% endif %}

</div>


<div class="row">

    <div class="col-xl-8">

        <form
            method="POST"
            enctype="multipart/form-data"
        >

            {% csrf_token %}

            {% if form.non_field_errors %}

                <div class="alert alert-danger">
                    {{ form.non_field_errors }}
                </div>

            {% endif %}


            <div class="dashboard-card">

                {% for field in form %}

                    {% if field.field.widget.input_type == "checkbox" %}

                        <div class="form-check mb-4">

                            {{ field }}

                            <label
                                class="form-check-label"
                                for="{{ field.id_for_label }}"
                            >
                                {{ field.label }}
                            </label>

                            {% for error in field.errors %}
                                <div class="text-danger small">
                                    {{ error }}
                                </div>
                            {% endfor %}

                        </div>

                    {% else %}

                        <div class="mb-4">

                            <label
                                class="form-label"
                                for="{{ field.id_for_label }}"
                            >
                                {{ field.label }}
                            </label>

                            {{ field }}

                            {% if field.help_text %}
                                <div class="form-text">
                                    {{ field.help_text }}
                                </div>
                            {% endif %}

                            {% for error in field.errors %}
                                <div class="text-danger small mt-1">
                                    {{ error }}
                                </div>
                            {% endfor %}

                        </div>

                    {% endif %}

                {% endfor %}


                <button
                    type="submit"
                    class="btn btn-primary"
                >
                    <i class="bi bi-check-lg"></i>
                    {{ submit_text }}
                </button>

            </div>

        </form>

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
    encoding="utf-8",
)


print(
    "Created catalog templates"
)

print()
print("=" * 65)
print("PHASE 3.4 + 3.5 PATCH COMPLETE")
print("=" * 65)
print()
print("Next:")
print("python manage.py makemigrations products")
print("python manage.py migrate")
print("python manage.py check")
