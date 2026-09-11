from pathlib import Path
import shutil


ROOT = Path.cwd()

forms_path = ROOT / "dashboard" / "forms.py"
views_path = ROOT / "dashboard" / "views.py"
urls_path = ROOT / "dashboard" / "urls.py"

detail_path = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "products"
    / "detail.html"
)

gallery_path = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "products"
    / "gallery.html"
)

variant_form_path = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "products"
    / "variant_form.html"
)


# ============================================================
# HELPERS
# ============================================================

def backup(path):
    if path.exists():
        backup_path = path.with_suffix(
            path.suffix + ".phase3backup"
        )
        shutil.copy2(path, backup_path)
        print(f"Backup: {backup_path}")


def append_once(path, marker, content):
    text = path.read_text(encoding="utf-8")

    if marker in text:
        print(f"Already exists: {marker}")
        return

    with path.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write("\n\n")
        file.write(content.strip())
        file.write("\n")

    print(f"Updated: {path}")


# ============================================================
# BACKUPS
# ============================================================

for file_path in [
    forms_path,
    views_path,
    urls_path,
    detail_path,
]:
    backup(file_path)


# ============================================================
# FORMS
# ============================================================

forms_text = forms_path.read_text(
    encoding="utf-8"
)

forms_text = forms_text.replace(
    "from products.models import Product",
    (
        "from products.models import "
        "Product, ProductImage, ProductVariant"
    ),
)

forms_path.write_text(
    forms_text,
    encoding="utf-8",
)


forms_code = r'''
class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):

    def __init__(self, *args, **kwargs):

        kwargs.setdefault(
            "widget",
            MultipleImageInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),
        )

        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):

        single_image_clean = super().clean

        if isinstance(
            data,
            (list, tuple),
        ):
            result = [
                single_image_clean(
                    image,
                    initial,
                )
                for image in data
            ]
        else:
            result = [
                single_image_clean(
                    data,
                    initial,
                )
            ]

        return result


class AdminProductGalleryForm(forms.Form):

    images = MultipleImageField(
        required=True,
        help_text=(
            "You can select multiple images. "
            "Maximum 10 images per upload."
        ),
    )

    def clean_images(self):

        images = self.cleaned_data["images"]

        if len(images) > 10:
            raise ValidationError(
                "Upload a maximum of 10 images at once."
            )

        max_size = 5 * 1024 * 1024

        for image in images:

            if image.size > max_size:
                raise ValidationError(
                    (
                        f"{image.name} is larger than "
                        "5 MB."
                    )
                )

        return images


class AdminProductVariantForm(forms.ModelForm):

    class Meta:

        model = ProductVariant

        fields = [
            "name",
            "sku",
            "price",
            "stock",
            "is_active",
        ]

        widgets = {

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "e.g. 16GB RAM / 512GB SSD"
                    ),
                }
            ),

            "sku": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "e.g. HP840-16-512"
                    ),
                }
            ),

            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "placeholder": (
                        "Leave blank to use "
                        "product price"
                    ),
                }
            ),

            "stock": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def clean_name(self):

        name = self.cleaned_data["name"].strip()

        if not name:
            raise ValidationError(
                "Variant name is required."
            )

        return name

    def clean_sku(self):

        sku = (
            self.cleaned_data["sku"]
            .strip()
            .upper()
        )

        queryset = (
            ProductVariant.objects
            .filter(
                sku__iexact=sku
            )
        )

        if self.instance.pk:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise ValidationError(
                (
                    "Another product variant "
                    "already uses this SKU."
                )
            )

        return sku

    def clean_price(self):

        price = self.cleaned_data.get(
            "price"
        )

        if (
            price is not None
            and price < 0
        ):
            raise ValidationError(
                "Price cannot be negative."
            )

        return price

    def clean_stock(self):

        stock = self.cleaned_data.get(
            "stock"
        )

        if stock is None:
            return stock

        if (
            self.instance.pk
            and stock
            < self.instance.reserved_stock
        ):
            raise ValidationError(
                (
                    "Stock cannot be lower than "
                    f"the reserved quantity "
                    f"({self.instance.reserved_stock})."
                )
            )

        return stock
'''

append_once(
    forms_path,
    "class AdminProductGalleryForm",
    forms_code,
)


# ============================================================
# UPDATE VIEWS IMPORTS
# ============================================================

views_text = views_path.read_text(
    encoding="utf-8"
)

old_import = (
    "from .forms import "
    "AdminOrderShippingForm, AdminProductForm"
)

new_import = '''from .forms import (
    AdminOrderShippingForm,
    AdminProductForm,
    AdminProductGalleryForm,
    AdminProductVariantForm,
)'''

if old_import in views_text:

    views_text = views_text.replace(
        old_import,
        new_import,
    )

elif "AdminProductGalleryForm" not in views_text:

    raise RuntimeError(
        (
            "Could not find the dashboard forms "
            "import in dashboard/views.py."
        )
    )

views_path.write_text(
    views_text,
    encoding="utf-8",
)


# ============================================================
# GALLERY + VARIANT VIEWS
# ============================================================

views_code = r'''
@staff_member_required
def admin_product_gallery(
    request,
    pk,
):

    product = get_object_or_404(
        Product.objects.prefetch_related(
            "images"
        ),
        pk=pk,
    )

    if request.method == "POST":

        form = AdminProductGalleryForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            uploaded_images = (
                form.cleaned_data["images"]
            )

            for image in uploaded_images:

                ProductImage.objects.create(
                    product=product,
                    image=image,
                    alt_text=product.name,
                )

            messages.success(
                request,
                (
                    f"{len(uploaded_images)} "
                    "gallery image(s) uploaded."
                ),
            )

            return redirect(
                "admin_product_gallery",
                pk=product.pk,
            )

    else:

        form = AdminProductGalleryForm()

    return render(
        request,
        (
            "dashboard/admin/products/"
            "gallery.html"
        ),
        {
            "product": product,
            "form": form,
            "gallery_images": (
                product.images.all()
            ),
        },
    )


@staff_member_required
def admin_product_gallery_delete(
    request,
    pk,
    image_id,
):

    if request.method != "POST":

        return redirect(
            "admin_product_gallery",
            pk=pk,
        )

    product = get_object_or_404(
        Product,
        pk=pk,
    )

    image = get_object_or_404(
        ProductImage,
        pk=image_id,
        product=product,
    )

    image_file = image.image

    image.delete()

    # Delete physical file only after
    # database row has been removed.
    if image_file:
        try:
            image_file.delete(
                save=False
            )
        except Exception:
            pass

    messages.success(
        request,
        "Gallery image removed.",
    )

    return redirect(
        "admin_product_gallery",
        pk=product.pk,
    )


@staff_member_required
def admin_product_variant_create(
    request,
    pk,
):

    product = get_object_or_404(
        Product,
        pk=pk,
    )

    if request.method == "POST":

        form = AdminProductVariantForm(
            request.POST
        )

        if form.is_valid():

            variant = form.save(
                commit=False
            )

            variant.product = product

            variant.save()

            messages.success(
                request,
                (
                    f"Variant "
                    f"{variant.name} created."
                ),
            )

            return redirect(
                "admin_product_detail",
                pk=product.pk,
            )

    else:

        form = AdminProductVariantForm()

    return render(
        request,
        (
            "dashboard/admin/products/"
            "variant_form.html"
        ),
        {
            "product": product,
            "form": form,
            "page_title": (
                "Add Product Variant"
            ),
            "submit_text": (
                "Create Variant"
            ),
        },
    )


@staff_member_required
def admin_product_variant_edit(
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

        form = AdminProductVariantForm(
            request.POST,
            instance=variant,
        )

        if form.is_valid():

            variant = form.save()

            messages.success(
                request,
                (
                    f"Variant "
                    f"{variant.name} updated."
                ),
            )

            return redirect(
                "admin_product_detail",
                pk=product.pk,
            )

    else:

        form = AdminProductVariantForm(
            instance=variant
        )

    return render(
        request,
        (
            "dashboard/admin/products/"
            "variant_form.html"
        ),
        {
            "product": product,
            "variant": variant,
            "form": form,
            "page_title": (
                "Edit Product Variant"
            ),
            "submit_text": (
                "Save Variant"
            ),
        },
    )


@staff_member_required
def admin_product_variant_toggle(
    request,
    pk,
    variant_id,
):

    if request.method != "POST":

        return redirect(
            "admin_product_detail",
            pk=pk,
        )

    product = get_object_or_404(
        Product,
        pk=pk,
    )

    variant = get_object_or_404(
        ProductVariant,
        pk=variant_id,
        product=product,
    )

    if (
        variant.is_active
        and variant.reserved_stock > 0
    ):

        messages.error(
            request,
            (
                "This variant currently has "
                "reserved stock and cannot "
                "be hidden yet."
            ),
        )

        return redirect(
            "admin_product_detail",
            pk=product.pk,
        )

    variant.is_active = (
        not variant.is_active
    )

    variant.save(
        update_fields=[
            "is_active",
        ]
    )

    messages.success(
        request,
        (
            f"{variant.name} is now "
            f"{'active' if variant.is_active else 'hidden'}."
        ),
    )

    return redirect(
        "admin_product_detail",
        pk=product.pk,
    )


@staff_member_required
def admin_product_variant_archive(
    request,
    pk,
    variant_id,
):

    if request.method != "POST":

        return redirect(
            "admin_product_detail",
            pk=pk,
        )

    product = get_object_or_404(
        Product,
        pk=pk,
    )

    variant = get_object_or_404(
        ProductVariant,
        pk=variant_id,
        product=product,
    )

    if variant.reserved_stock > 0:

        messages.error(
            request,
            (
                "This variant cannot be "
                "archived because some units "
                "are reserved by pending orders."
            ),
        )

        return redirect(
            "admin_product_detail",
            pk=product.pk,
        )

    # We intentionally DO NOT delete the row.
    # OrderItem.variant uses PROTECT and old
    # order history must remain valid.
    variant.is_active = False

    variant.save(
        update_fields=[
            "is_active",
        ]
    )

    messages.warning(
        request,
        (
            f"{variant.name} was archived "
            "and hidden from customers."
        ),
    )

    return redirect(
        "admin_product_detail",
        pk=product.pk,
    )
'''

append_once(
    views_path,
    "def admin_product_gallery(",
    views_code,
)


# ============================================================
# URLS
# ============================================================

urls_text = urls_path.read_text(
    encoding="utf-8"
)

if "admin_product_gallery" not in urls_text:

    marker = '''    # =========================================================
    # REPORTS / ANALYTICS
    # ========================================================='''

    new_urls = r'''    # =========================================================
    # PRODUCT GALLERY
    # =========================================================

    path(
        "admin/products/<int:pk>/gallery/",
        views.admin_product_gallery,
        name="admin_product_gallery",
    ),

    path(
        "admin/products/<int:pk>/gallery/<int:image_id>/delete/",
        views.admin_product_gallery_delete,
        name="admin_product_gallery_delete",
    ),


    # =========================================================
    # PRODUCT VARIANTS
    # =========================================================

    path(
        "admin/products/<int:pk>/variants/add/",
        views.admin_product_variant_create,
        name="admin_product_variant_create",
    ),

    path(
        "admin/products/<int:pk>/variants/<int:variant_id>/edit/",
        views.admin_product_variant_edit,
        name="admin_product_variant_edit",
    ),

    path(
        "admin/products/<int:pk>/variants/<int:variant_id>/toggle/",
        views.admin_product_variant_toggle,
        name="admin_product_variant_toggle",
    ),

    path(
        "admin/products/<int:pk>/variants/<int:variant_id>/archive/",
        views.admin_product_variant_archive,
        name="admin_product_variant_archive",
    ),


'''

    if marker not in urls_text:
        raise RuntimeError(
            (
                "REPORTS / ANALYTICS marker "
                "not found in dashboard/urls.py."
            )
        )

    urls_text = urls_text.replace(
        marker,
        new_urls + marker,
    )

    urls_path.write_text(
        urls_text,
        encoding="utf-8",
    )

    print(
        "Updated dashboard/urls.py"
    )

else:

    print(
        "Gallery/variant URLs already exist."
    )


# ============================================================
# CREATE TEMPLATE FOLDER
# ============================================================

detail_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# PRODUCT DETAIL TEMPLATE
# ============================================================

detail_html = r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
{{ product.name }} | Product
{% endblock %}

{% block page_heading %}
Product
{% endblock %}

{% block admin_content %}

<div class="d-flex justify-content-between align-items-center flex-wrap gap-3 mb-4">

    <div>
        <h1 class="h3 mb-1">
            {{ product.name }}
        </h1>

        <span class="text-muted">
            SKU: {{ product.sku }}
        </span>
    </div>

    <div class="d-flex gap-2 flex-wrap">

        <a
            href="{% url 'product_detail' product.slug %}"
            target="_blank"
            class="btn btn-outline-secondary"
        >
            <i class="bi bi-box-arrow-up-right"></i>
            Preview
        </a>

        <a
            href="{% url 'admin_product_edit' product.pk %}"
            class="btn btn-primary"
        >
            <i class="bi bi-pencil"></i>
            Edit Product
        </a>

    </div>

</div>


<div class="row g-4">

    <div class="col-lg-4">

        <div class="dashboard-card">

            {% if product.image %}

                <img
                    src="{{ product.image.url }}"
                    alt="{{ product.name }}"
                    class="img-fluid rounded"
                    style="
                        width: 100%;
                        max-height: 400px;
                        object-fit: contain;
                    "
                >

            {% else %}

                <div class="text-center text-muted py-5">
                    <i class="bi bi-image fs-1"></i>
                    <p class="mt-2 mb-0">
                        No primary image
                    </p>
                </div>

            {% endif %}

        </div>

    </div>


    <div class="col-lg-8">

        <div class="dashboard-card">

            <div class="d-flex justify-content-between align-items-start gap-3">

                <div>

                    <h2 class="h4">
                        {{ product.name }}
                    </h2>

                    <p class="text-muted">
                        {{ product.category.name }}

                        {% if product.brand %}
                            · {{ product.brand.name }}
                        {% endif %}
                    </p>

                </div>

                <div>

                    {% if product.is_active %}

                        <span class="badge text-bg-success">
                            Active
                        </span>

                    {% else %}

                        <span class="badge text-bg-secondary">
                            Hidden
                        </span>

                    {% endif %}

                    {% if product.featured %}

                        <span class="badge text-bg-warning">
                            Featured
                        </span>

                    {% endif %}

                </div>

            </div>

            <hr>

            <div class="row g-4">

                <div class="col-md-4">

                    <span class="text-muted">
                        Regular Price
                    </span>

                    <h5 class="mt-1">
                        KES {{ product.price|floatformat:2 }}
                    </h5>

                </div>

                <div class="col-md-4">

                    <span class="text-muted">
                        Selling Price
                    </span>

                    <h5 class="mt-1">
                        KES {{ product.current_price|floatformat:2 }}
                    </h5>

                </div>

                <div class="col-md-4">

                    <span class="text-muted">
                        SKU
                    </span>

                    <h5 class="mt-1">
                        {{ product.sku }}
                    </h5>

                </div>

            </div>

            <hr>

            <h3 class="h6">
                Description
            </h3>

            <div class="text-muted">
                {{ product.description|linebreaksbr }}
            </div>

        </div>

    </div>


    <div class="col-lg-4">

        <div class="dashboard-card">

            <h2 class="h5 mb-4">
                Inventory
            </h2>

            <div class="list-row">
                <span>Physical Stock</span>
                <strong>{{ product.stock }}</strong>
            </div>

            <div class="list-row">
                <span>Reserved</span>
                <strong>{{ product.reserved_stock }}</strong>
            </div>

            <div class="list-row">
                <span>Available</span>
                <strong>{{ product.available_stock }}</strong>
            </div>

            <div class="list-row">
                <span>Variants</span>
                <strong>{{ variants|length }}</strong>
            </div>

        </div>

    </div>


    <div class="col-lg-4">

        <div class="dashboard-card">

            <h2 class="h5 mb-4">
                Storefront
            </h2>

            <form
                method="POST"
                action="{% url 'admin_product_toggle_active' product.pk %}"
                class="mb-3"
            >

                {% csrf_token %}

                {% if product.is_active %}

                    <button
                        type="submit"
                        class="btn btn-outline-danger w-100"
                    >
                        <i class="bi bi-eye-slash"></i>
                        Hide Product
                    </button>

                {% else %}

                    <button
                        type="submit"
                        class="btn btn-success w-100"
                    >
                        <i class="bi bi-eye"></i>
                        Activate Product
                    </button>

                {% endif %}

            </form>


            <form
                method="POST"
                action="{% url 'admin_product_toggle_featured' product.pk %}"
            >

                {% csrf_token %}

                {% if product.featured %}

                    <button
                        type="submit"
                        class="btn btn-outline-secondary w-100"
                    >
                        <i class="bi bi-star"></i>
                        Remove Featured
                    </button>

                {% else %}

                    <button
                        type="submit"
                        class="btn btn-outline-warning w-100"
                    >
                        <i class="bi bi-star-fill"></i>
                        Make Featured
                    </button>

                {% endif %}

            </form>

        </div>

    </div>


    <div class="col-lg-4">

        <div class="dashboard-card">

            <h2 class="h5 mb-4">
                Product Media
            </h2>

            <div class="list-row">

                <span>
                    Gallery Images
                </span>

                <strong>
                    {{ gallery_images|length }}
                </strong>

            </div>

            <div class="list-row">

                <span>
                    Primary Image
                </span>

                <strong>
                    {% if product.image %}
                        Yes
                    {% else %}
                        No
                    {% endif %}
                </strong>

            </div>

            <div class="mt-3">

                <a
                    href="{% url 'admin_product_gallery' product.pk %}"
                    class="btn btn-outline-primary w-100"
                >
                    <i class="bi bi-images"></i>
                    Manage Gallery
                </a>

            </div>

        </div>

    </div>


    <div class="col-12">

        <div class="dashboard-card">

            <div class="card-header-custom">

                <div>

                    <h2>
                        Variants
                    </h2>

                    <p>
                        Options such as size, colour,
                        storage or configuration.
                    </p>

                </div>

                <a
                    href="{% url 'admin_product_variant_create' product.pk %}"
                    class="btn btn-sm btn-primary"
                >
                    <i class="bi bi-plus-lg"></i>
                    Add Variant
                </a>

            </div>


            <div class="table-responsive">

                <table class="table align-middle">

                    <thead>

                        <tr>
                            <th>Variant</th>
                            <th>SKU</th>
                            <th>Price</th>
                            <th>Stock</th>
                            <th>Reserved</th>
                            <th>Available</th>
                            <th>Status</th>
                            <th></th>
                        </tr>

                    </thead>

                    <tbody>

                        {% for variant in variants %}

                            <tr>

                                <td>
                                    <strong>
                                        {{ variant.name }}
                                    </strong>
                                </td>

                                <td>
                                    {{ variant.sku }}
                                </td>

                                <td>
                                    KES {{ variant.current_price|floatformat:2 }}
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

                                    {% elif variant.available_stock <= 5 %}

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

                                    {% if variant.is_active %}

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

                                    <div class="dropdown">

                                        <button
                                            class="btn btn-sm btn-outline-secondary dropdown-toggle"
                                            data-bs-toggle="dropdown"
                                        >
                                            Actions
                                        </button>

                                        <ul class="dropdown-menu dropdown-menu-end">

                                            <li>

                                                <a
                                                    href="{% url 'admin_product_variant_edit' product.pk variant.pk %}"
                                                    class="dropdown-item"
                                                >
                                                    <i class="bi bi-pencil"></i>
                                                    Edit
                                                </a>

                                            </li>

                                            <li>

                                                <form
                                                    method="POST"
                                                    action="{% url 'admin_product_variant_toggle' product.pk variant.pk %}"
                                                >
                                                    {% csrf_token %}

                                                    <button
                                                        type="submit"
                                                        class="dropdown-item"
                                                    >
                                                        {% if variant.is_active %}
                                                            <i class="bi bi-eye-slash"></i>
                                                            Hide
                                                        {% else %}
                                                            <i class="bi bi-eye"></i>
                                                            Activate
                                                        {% endif %}
                                                    </button>

                                                </form>

                                            </li>

                                            <li>
                                                <hr class="dropdown-divider">
                                            </li>

                                            <li>

                                                <form
                                                    method="POST"
                                                    action="{% url 'admin_product_variant_archive' product.pk variant.pk %}"
                                                    onsubmit="return confirm('Archive this variant? Historical order records will be preserved.');"
                                                >

                                                    {% csrf_token %}

                                                    <button
                                                        type="submit"
                                                        class="dropdown-item text-danger"
                                                    >
                                                        <i class="bi bi-archive"></i>
                                                        Archive
                                                    </button>

                                                </form>

                                            </li>

                                        </ul>

                                    </div>

                                </td>

                            </tr>

                        {% empty %}

                            <tr>

                                <td
                                    colspan="8"
                                    class="text-center text-muted py-5"
                                >

                                    <i class="bi bi-diagram-3 fs-1 d-block mb-2"></i>

                                    No variants yet.

                                    <div class="mt-3">

                                        <a
                                            href="{% url 'admin_product_variant_create' product.pk %}"
                                            class="btn btn-sm btn-primary"
                                        >
                                            Add First Variant
                                        </a>

                                    </div>

                                </td>

                            </tr>

                        {% endfor %}

                    </tbody>

                </table>

            </div>

        </div>

    </div>

</div>

{% endblock %}
'''

detail_path.write_text(
    detail_html.strip() + "\n",
    encoding="utf-8",
)

print(
    f"Created/updated: {detail_path}"
)


# ============================================================
# GALLERY TEMPLATE
# ============================================================

gallery_html = r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Gallery | {{ product.name }}
{% endblock %}

{% block page_heading %}
Product Gallery
{% endblock %}

{% block admin_content %}

<div class="d-flex justify-content-between align-items-center flex-wrap gap-3 mb-4">

    <div>

        <h1 class="h3 mb-1">
            Product Gallery
        </h1>

        <p class="text-muted mb-0">
            {{ product.name }}
        </p>

    </div>

    <a
        href="{% url 'admin_product_detail' product.pk %}"
        class="btn btn-outline-secondary"
    >
        <i class="bi bi-arrow-left"></i>
        Back to Product
    </a>

</div>


<div class="row g-4">

    <div class="col-lg-4">

        <div class="dashboard-card">

            <h2 class="h5 mb-3">
                Upload Images
            </h2>

            <p class="text-muted small">
                Select up to 10 images at once.
                Each image can be up to 5 MB.
            </p>


            <form
                method="POST"
                enctype="multipart/form-data"
            >

                {% csrf_token %}

                <div class="mb-3">

                    {{ form.images }}

                    {% if form.images.help_text %}

                        <div class="form-text">
                            {{ form.images.help_text }}
                        </div>

                    {% endif %}

                    {% for error in form.images.errors %}

                        <div class="text-danger small mt-1">
                            {{ error }}
                        </div>

                    {% endfor %}

                </div>


                <button
                    type="submit"
                    class="btn btn-primary w-100"
                >
                    <i class="bi bi-cloud-upload"></i>
                    Upload Images
                </button>

            </form>

        </div>

    </div>


    <div class="col-lg-8">

        <div class="dashboard-card">

            <div class="d-flex justify-content-between align-items-center mb-4">

                <div>

                    <h2 class="h5 mb-1">
                        Gallery Images
                    </h2>

                    <span class="text-muted">
                        {{ gallery_images|length }}
                        image{{ gallery_images|length|pluralize }}
                    </span>

                </div>

            </div>


            <div class="row g-3">

                {% for image in gallery_images %}

                    <div class="col-md-6 col-xl-4">

                        <div class="border rounded p-2 h-100">

                            <img
                                src="{{ image.image.url }}"
                                alt="{{ image.alt_text|default:product.name }}"
                                class="img-fluid rounded"
                                style="
                                    width: 100%;
                                    height: 180px;
                                    object-fit: cover;
                                "
                            >

                            <div class="mt-2">

                                <small class="text-muted d-block text-truncate">
                                    {{ image.alt_text|default:product.name }}
                                </small>

                                <form
                                    method="POST"
                                    action="{% url 'admin_product_gallery_delete' product.pk image.pk %}"
                                    class="mt-2"
                                    onsubmit="return confirm('Remove this gallery image?');"
                                >

                                    {% csrf_token %}

                                    <button
                                        type="submit"
                                        class="btn btn-sm btn-outline-danger w-100"
                                    >
                                        <i class="bi bi-trash"></i>
                                        Remove
                                    </button>

                                </form>

                            </div>

                        </div>

                    </div>

                {% empty %}

                    <div class="col-12">

                        <div class="text-center text-muted py-5">

                            <i class="bi bi-images fs-1 d-block mb-2"></i>

                            No gallery images uploaded yet.

                        </div>

                    </div>

                {% endfor %}

            </div>

        </div>

    </div>

</div>

{% endblock %}
'''

gallery_path.write_text(
    gallery_html.strip() + "\n",
    encoding="utf-8",
)

print(
    f"Created: {gallery_path}"
)


# ============================================================
# VARIANT FORM TEMPLATE
# ============================================================

variant_html = r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
{{ page_title }} | {{ product.name }}
{% endblock %}

{% block page_heading %}
{{ page_title }}
{% endblock %}

{% block admin_content %}

<div class="d-flex justify-content-between align-items-center flex-wrap gap-3 mb-4">

    <div>

        <h1 class="h3 mb-1">
            {{ page_title }}
        </h1>

        <p class="text-muted mb-0">
            {{ product.name }}
        </p>

    </div>

    <a
        href="{% url 'admin_product_detail' product.pk %}"
        class="btn btn-outline-secondary"
    >
        <i class="bi bi-arrow-left"></i>
        Back to Product
    </a>

</div>


<div class="row">

    <div class="col-xl-8">

        <form method="POST">

            {% csrf_token %}


            {% if form.non_field_errors %}

                <div class="alert alert-danger">
                    {{ form.non_field_errors }}
                </div>

            {% endif %}


            <div class="dashboard-card mb-4">

                <h2 class="h5 mb-4">
                    Variant Information
                </h2>


                <div class="row g-3">

                    <div class="col-md-6">

                        <label class="form-label">
                            Variant Name *
                        </label>

                        {{ form.name }}

                        {% for error in form.name.errors %}
                            <div class="text-danger small">
                                {{ error }}
                            </div>
                        {% endfor %}

                    </div>


                    <div class="col-md-6">

                        <label class="form-label">
                            SKU *
                        </label>

                        {{ form.sku }}

                        {% for error in form.sku.errors %}
                            <div class="text-danger small">
                                {{ error }}
                            </div>
                        {% endfor %}

                    </div>


                    <div class="col-md-6">

                        <label class="form-label">
                            Variant Price
                        </label>

                        {{ form.price }}

                        <div class="form-text">
                            Leave blank to inherit the
                            main product selling price.
                        </div>

                        {% for error in form.price.errors %}
                            <div class="text-danger small">
                                {{ error }}
                            </div>
                        {% endfor %}

                    </div>


                    <div class="col-md-6">

                        <label class="form-label">
                            Physical Stock *
                        </label>

                        {{ form.stock }}

                        {% if variant %}

                            <div class="form-text">
                                Reserved:
                                {{ variant.reserved_stock }}
                                |
                                Available:
                                {{ variant.available_stock }}
                            </div>

                        {% endif %}

                        {% for error in form.stock.errors %}
                            <div class="text-danger small">
                                {{ error }}
                            </div>
                        {% endfor %}

                    </div>

                </div>


                <div class="form-check mt-4">

                    {{ form.is_active }}

                    <label
                        class="form-check-label"
                        for="{{ form.is_active.id_for_label }}"
                    >
                        Active variant
                    </label>

                </div>

            </div>


            <div class="d-flex gap-2">

                <button
                    type="submit"
                    class="btn btn-primary"
                >
                    <i class="bi bi-check-lg"></i>
                    {{ submit_text }}
                </button>

                <a
                    href="{% url 'admin_product_detail' product.pk %}"
                    class="btn btn-outline-secondary"
                >
                    Cancel
                </a>

            </div>

        </form>

    </div>


    <div class="col-xl-4 mt-4 mt-xl-0">

        <div class="dashboard-card">

            <h2 class="h6">
                How variant pricing works
            </h2>

            <p class="text-muted small mb-0">

                If you leave Variant Price blank,
                this variant automatically uses the
                main product's current selling price.

            </p>

        </div>

    </div>

</div>

{% endblock %}
'''

variant_form_path.write_text(
    variant_html.strip() + "\n",
    encoding="utf-8",
)

print(
    f"Created: {variant_form_path}"
)


print()
print("=" * 60)
print("PHASE 3.2 + 3.3 PATCH COMPLETE")
print("=" * 60)
print()
print("Next commands:")
print("  python manage.py check")
print("  python manage.py test")
print()
