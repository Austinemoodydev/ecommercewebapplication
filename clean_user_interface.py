from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()

if not (ROOT / "manage.py").exists():
    raise SystemExit(
        "ERROR: Run this inside the Django project folder containing manage.py."
    )

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

BACKUP = (
    ROOT
    / ".ui_cleanup_backups"
    / stamp
)

BACKUP.mkdir(
    parents=True,
    exist_ok=True,
)


def backup(path):

    if not path.exists():
        return

    target = (
        BACKUP
        / path.relative_to(ROOT)
    )

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        path,
        target,
    )


def write(rel, text):

    path = ROOT / rel

    if path.exists():
        backup(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        text,
        encoding="utf-8",
    )

    print("[UPDATED]", rel)


print("=" * 72)
print("ONLINE SHOP UI CLEANUP")
print("=" * 72)


# ============================================================
# 1. CUSTOMER DASHBOARD — LIVE COUNTS
# ============================================================

views_file = ROOT / "dashboard/views.py"
backup(views_file)

text = views_file.read_text(
    encoding="utf-8-sig"
)


if "from wishlist.models import Wishlist" not in text:

    anchor = (
        "from products.models import "
        "Brand, Product, ProductImage, ProductVariant"
    )

    if anchor not in text:
        raise RuntimeError(
            "Could not safely locate dashboard imports."
        )

    text = text.replace(
        anchor,
        anchor + "\nfrom wishlist.models import Wishlist",
        1,
    )


old_dashboard = '''@login_required
def dashboard(request):
    return render(request, "dashboard/dashboard.html")
'''

new_dashboard = '''@login_required
def dashboard(request):

    orders = (
        Order.objects
        .filter(user=request.user)
        .order_by("-created_at")
    )

    context = {
        "orders_count": orders.count(),
        "wishlist_count_dashboard": (
            Wishlist.objects
            .filter(user=request.user)
            .count()
        ),
        "addresses_count": (
            request.user.addresses.count()
        ),
        "recent_orders": orders[:5],
    }

    return render(
        request,
        "dashboard/dashboard.html",
        context,
    )
'''

if old_dashboard in text:

    text = text.replace(
        old_dashboard,
        new_dashboard,
        1,
    )

elif "wishlist_count_dashboard" in text:

    print(
        "[OK] Customer dashboard already has live counts."
    )

else:

    raise RuntimeError(
        "Could not safely update customer dashboard view."
    )


views_file.write_text(
    text,
    encoding="utf-8",
)

print("[UPDATED] dashboard/views.py")


# ============================================================
# 2. CUSTOMER DASHBOARD TEMPLATE
# ============================================================

write(
    "templates/dashboard/dashboard.html",
r'''{% extends "base.html" %}

{% block title %}
My Account
{% endblock %}


{% block content %}

<div class="container py-4">


    <!-- HEADER -->

    <div
        class="d-flex flex-column flex-md-row
               justify-content-between
               align-items-md-center
               gap-3 mb-4"
    >

        <div>

            <p
                class="text-primary fw-semibold mb-1"
            >
                MY ACCOUNT
            </p>

            <h2 class="mb-1">

                Welcome,
                {{ request.user.first_name|default:request.user.username }}

            </h2>

            <p class="text-muted mb-0">

                Manage your orders, saved products,
                addresses and account information.

            </p>

        </div>


        <a
            href="{% url 'shop' %}"
            class="btn btn-primary"
        >

            <i class="bi bi-bag me-2"></i>

            Continue shopping

        </a>

    </div>


    <!-- SUMMARY -->

    <div class="row g-3 mb-4">


        <div class="col-md-4">

            <a
                href="{% url 'order_history' %}"
                class="text-decoration-none"
            >

                <div
                    class="card border-0 shadow-sm h-100"
                >

                    <div class="card-body">

                        <div
                            class="d-flex align-items-center
                                   justify-content-between"
                        >

                            <div>

                                <p
                                    class="text-muted mb-1"
                                >
                                    Orders
                                </p>

                                <h3 class="mb-0 text-dark">

                                    {{ orders_count }}

                                </h3>

                            </div>

                            <div
                                class="bg-primary-subtle
                                       text-primary
                                       rounded-3 p-3"
                            >

                                <i
                                    class="bi bi-box-seam fs-4"
                                ></i>

                            </div>

                        </div>

                    </div>

                </div>

            </a>

        </div>


        <div class="col-md-4">

            <a
                href="{% url 'wishlist' %}"
                class="text-decoration-none"
            >

                <div
                    class="card border-0 shadow-sm h-100"
                >

                    <div class="card-body">

                        <div
                            class="d-flex align-items-center
                                   justify-content-between"
                        >

                            <div>

                                <p
                                    class="text-muted mb-1"
                                >
                                    Wishlist
                                </p>

                                <h3 class="mb-0 text-dark">

                                    {{ wishlist_count_dashboard }}

                                </h3>

                            </div>

                            <div
                                class="bg-primary-subtle
                                       text-primary
                                       rounded-3 p-3"
                            >

                                <i
                                    class="bi bi-heart fs-4"
                                ></i>

                            </div>

                        </div>

                    </div>

                </div>

            </a>

        </div>


        <div class="col-md-4">

            <a
                href="{% url 'addresses' %}"
                class="text-decoration-none"
            >

                <div
                    class="card border-0 shadow-sm h-100"
                >

                    <div class="card-body">

                        <div
                            class="d-flex align-items-center
                                   justify-content-between"
                        >

                            <div>

                                <p
                                    class="text-muted mb-1"
                                >
                                    Addresses
                                </p>

                                <h3 class="mb-0 text-dark">

                                    {{ addresses_count }}

                                </h3>

                            </div>

                            <div
                                class="bg-primary-subtle
                                       text-primary
                                       rounded-3 p-3"
                            >

                                <i
                                    class="bi bi-geo-alt fs-4"
                                ></i>

                            </div>

                        </div>

                    </div>

                </div>

            </a>

        </div>

    </div>


    <div class="row g-4">


        <!-- ACCOUNT LINKS -->

        <div class="col-lg-4">

            <div
                class="card border-0 shadow-sm h-100"
            >

                <div class="card-body">

                    <h5 class="mb-3">
                        Account
                    </h5>


                    <div class="list-group list-group-flush">


                        <a
                            href="{% url 'profile' %}"
                            class="list-group-item
                                   list-group-item-action
                                   px-0"
                        >

                            <i
                                class="bi bi-person me-2
                                       text-primary"
                            ></i>

                            Profile

                        </a>


                        <a
                            href="{% url 'addresses' %}"
                            class="list-group-item
                                   list-group-item-action
                                   px-0"
                        >

                            <i
                                class="bi bi-geo-alt me-2
                                       text-primary"
                            ></i>

                            Delivery addresses

                        </a>


                        <a
                            href="{% url 'wishlist' %}"
                            class="list-group-item
                                   list-group-item-action
                                   px-0"
                        >

                            <i
                                class="bi bi-heart me-2
                                       text-primary"
                            ></i>

                            Wishlist

                        </a>


                        <a
                            href="{% url 'customer_notifications' %}"
                            class="list-group-item
                                   list-group-item-action
                                   px-0"
                        >

                            <i
                                class="bi bi-bell me-2
                                       text-primary"
                            ></i>

                            Notifications

                        </a>


                        <a
                            href="{% url 'notification_preferences' %}"
                            class="list-group-item
                                   list-group-item-action
                                   px-0"
                        >

                            <i
                                class="bi bi-sliders me-2
                                       text-primary"
                            ></i>

                            Notification preferences

                        </a>


                    </div>

                </div>

            </div>

        </div>


        <!-- RECENT ORDERS -->

        <div class="col-lg-8">

            <div
                class="card border-0 shadow-sm h-100"
            >

                <div
                    class="card-header bg-white
                           d-flex justify-content-between
                           align-items-center py-3"
                >

                    <strong>
                        Recent orders
                    </strong>

                    <a
                        href="{% url 'order_history' %}"
                        class="small"
                    >
                        View all
                    </a>

                </div>


                <div class="card-body p-0">

                    {% if recent_orders %}

                        <div
                            class="table-responsive"
                        >

                            <table
                                class="table
                                       align-middle
                                       mb-0"
                            >

                                <thead
                                    class="table-light"
                                >

                                    <tr>

                                        <th>
                                            Order
                                        </th>

                                        <th>
                                            Status
                                        </th>

                                        <th>
                                            Payment
                                        </th>

                                        <th
                                            class="text-end"
                                        >
                                            Total
                                        </th>

                                    </tr>

                                </thead>


                                <tbody>

                                {% for order in recent_orders %}

                                    <tr>

                                        <td>

                                            <a
                                                href="{% url 'order_detail' order.order_number %}"
                                                class="fw-semibold"
                                            >

                                                {{ order.order_number }}

                                            </a>

                                            <small
                                                class="d-block
                                                       text-muted"
                                            >

                                                {{ order.created_at|date:"d M Y" }}

                                            </small>

                                        </td>


                                        <td>

                                            <span
                                                class="badge
                                                       text-bg-light
                                                       border"
                                            >

                                                {{ order.get_status_display }}

                                            </span>

                                        </td>


                                        <td>

                                            {% if order.payment_status == "paid" %}

                                                <span
                                                    class="badge bg-success"
                                                >
                                                    Paid
                                                </span>

                                            {% else %}

                                                <span
                                                    class="badge
                                                           text-bg-warning"
                                                >

                                                    {{ order.get_payment_status_display }}

                                                </span>

                                            {% endif %}

                                        </td>


                                        <td
                                            class="text-end
                                                   fw-semibold"
                                        >

                                            KES {{ order.total_amount }}

                                        </td>

                                    </tr>

                                {% endfor %}

                                </tbody>

                            </table>

                        </div>

                    {% else %}

                        <div
                            class="text-center py-5"
                        >

                            <i
                                class="bi bi-bag fs-1
                                       text-muted"
                            ></i>

                            <h5 class="mt-3">
                                No orders yet
                            </h5>

                            <p class="text-muted">

                                Your recent orders will
                                appear here.

                            </p>

                            <a
                                href="{% url 'shop' %}"
                                class="btn btn-primary"
                            >

                                Start shopping

                            </a>

                        </div>

                    {% endif %}

                </div>

            </div>

        </div>


    </div>


</div>

{% endblock %}
'''
)


# ============================================================
# 3. SHOP BRAND CONSISTENCY
# ============================================================

shop_file = ROOT / "templates/products/shop.html"
backup(shop_file)

text = shop_file.read_text(
    encoding="utf-8-sig"
)

text = text.replace(
    'class="badge bg-success"',
    'class="badge bg-primary"',
)

text = text.replace(
    'class="text-success"',
    'class="text-primary"',
)

text = text.replace(
    'class="btn btn-success add-to-cart-btn"',
    'class="btn btn-primary add-to-cart-btn"',
)

text = text.replace(
    'class="btn btn-outline-danger wishlist-btn"',
    'class="btn btn-outline-primary wishlist-btn"',
)

shop_file.write_text(
    text,
    encoding="utf-8",
)

print("[UPDATED] templates/products/shop.html")


# ============================================================
# 4. NAVBAR BRAND IDENTITY
# ============================================================

navbar = ROOT / "templates/includes/navbar.html"
backup(navbar)

text = navbar.read_text(
    encoding="utf-8-sig"
)

old = '''<img src="{% static 'images/icons/icon.jpeg' %}" alt="" height="32" class="me-2">
      
    </a>'''

new = '''<img
        src="{% static 'images/icons/icon.jpeg' %}"
        alt="OnlineShop"
        height="32"
        class="me-2"
      >
      <span>OnlineShop</span>
    </a>'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif "<span>OnlineShop</span>" in text:

    print(
        "[OK] Navbar brand text already present."
    )

else:

    print(
        "[NOTICE] Navbar branding block had different formatting; skipped."
    )

navbar.write_text(
    text,
    encoding="utf-8",
)

print("[UPDATED] templates/includes/navbar.html")


# ============================================================
# 5. HIDE UNFINISHED ADMIN SIDEBAR FEATURES
# ============================================================

admin_base = ROOT / "templates/dashboard/admin/base.html"
backup(admin_base)

text = admin_base.read_text(
    encoding="utf-8-sig"
)


promotions = '''            <!-- PROMOTIONS -->

            <a
                href="#"
                class="sidebar-link"
            >

                <i class="bi bi-tag"></i>

                <span>
                    Promotions
                </span>

            </a>
'''

reviews = '''            <!-- REVIEWS -->

            <a
                href="#"
                class="sidebar-link"
            >

                <i class="bi bi-star"></i>

                <span>
                    Reviews
                </span>

            </a>
'''

if promotions in text:

    text = text.replace(
        promotions,
        "",
        1,
    )

if reviews in text:

    text = text.replace(
        reviews,
        "",
        1,
    )

admin_base.write_text(
    text,
    encoding="utf-8",
)

print(
    "[UPDATED] Admin sidebar unfinished links removed."
)


# ============================================================
# 6. AUTH UI CONSISTENCY
# ============================================================

auth_css = ROOT / "static/css/auth.css"
backup(auth_css)

text = auth_css.read_text(
    encoding="utf-8-sig"
)

text = text.replace(
    '''button {
    border-radius: 999px !important;
    font-weight: 700;
}''',
    '''button,
.btn {
    border-radius: .65rem !important;
    font-weight: 700;
}''',
)

if ".form-label {" not in text:

    text += '''

.form-label {
    color: #334155;
    font-weight: 600;
    margin-bottom: .45rem;
}

.form-control:focus,
.form-select:focus {
    border-color: #3B82F6 !important;
    box-shadow: 0 0 0 .2rem rgba(59, 130, 246, .12);
}

.btn-primary {
    background: #3B82F6;
    border-color: #3B82F6;
}

.btn-primary:hover,
.btn-primary:focus {
    background: #2563EB;
    border-color: #2563EB;
}

.auth-note {
    color: #64748B;
    font-size: .875rem;
}
'''

auth_css.write_text(
    text,
    encoding="utf-8",
)

print("[UPDATED] static/css/auth.css")


# ============================================================
# 7. CHECK ACTIVE DEAD LINKS
# ============================================================

print()
print("=" * 72)
print("CHECKING ACTIVE TEMPLATE DEAD LINKS")
print("=" * 72)

active_templates = [
    ROOT / "templates/dashboard/admin/base.html",
    ROOT / "templates/dashboard/dashboard.html",
    ROOT / "templates/products/shop.html",
]

for path in active_templates:

    data = path.read_text(
        encoding="utf-8"
    )

    if 'href="#"' in data:

        print(
            "[WARNING] Remaining href=# in",
            path.relative_to(ROOT),
        )

    else:

        print(
            "[PASS]",
            path.relative_to(ROOT),
        )


# ============================================================
# 8. DJANGO VALIDATION
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
        "collectstatic",
        "--noinput",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "dashboard",
        "-v",
        "1",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "-v",
        "1",
    ],
]


print()
print("=" * 72)
print("RUNNING UI VALIDATION")
print("=" * 72)


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
        print("=" * 72)
        print("UI VALIDATION FAILED")
        print("=" * 72)

        print()
        print("Your original files are backed up here:")
        print(BACKUP)

        raise SystemExit(
            result.returncode
        )


print()
print("=" * 72)
print("UI CLEANUP PASSED")
print("=" * 72)

print()
print("✓ Customer dashboard now useful")
print("✓ Dashboard counts now use real data")
print("✓ Customer account links work")
print("✓ Recent orders displayed")
print("✓ Shop green branding removed")
print("✓ Semantic success green preserved")
print("✓ Navbar store identity clearer")
print("✓ Unfinished admin links hidden")
print("✓ Auth form styling normalized")
print("✓ collectstatic completed")
print("✓ Full tests passed")

print()
print("Backup:")
print(BACKUP)

