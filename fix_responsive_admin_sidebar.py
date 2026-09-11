from pathlib import Path
import shutil


ROOT = Path.cwd()

base_path = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "base.html"
)

css_path = (
    ROOT
    / "static"
    / "css"
    / "admin-dashboard.css"
)


# ============================================================
# BACKUPS
# ============================================================

for path in [base_path, css_path]:

    if path.exists():

        backup = Path(
            str(path) + ".responsivebackup"
        )

        shutil.copy2(
            path,
            backup,
        )

        print(
            f"Backup created: {backup}"
        )


# ============================================================
# CLEAN SHARED ADMIN BASE
# ============================================================

base_path.write_text(
r'''
{% load static %}

<!DOCTYPE html>

<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >

    <title>

        {% block title %}
            Store Management
        {% endblock %}

    </title>


    <!-- Bootstrap -->

    <link
        href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.7/dist/css/bootstrap.min.css"
        rel="stylesheet"
    >


    <!-- Bootstrap Icons -->

    <link
        rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/bootstrap-icons.min.css"
    >


    <!-- Admin Dashboard -->

    <link
        rel="stylesheet"
        href="{% static 'css/admin-dashboard.css' %}"
    >


    {% block extra_css %}
    {% endblock %}

</head>


<body>


<div class="admin-layout">


    <!-- ==================================================
         MOBILE SIDEBAR OVERLAY
    =================================================== -->

    <button
        type="button"
        class="sidebar-overlay"
        id="sidebarOverlay"
        aria-label="Close navigation"
    ></button>


    <!-- ==================================================
         SIDEBAR
    =================================================== -->

    <aside
        class="admin-sidebar"
        id="adminSidebar"
        aria-label="Management navigation"
    >


        <!-- BRAND -->

        <div class="sidebar-brand">

            <div
                class="
                    d-flex
                    align-items-center
                    gap-3
                    flex-grow-1
                "
            >

                <i class="bi bi-bag-check-fill"></i>


                <div>

                    <strong>
                        Online Shop
                    </strong>

                    <small>
                        Management
                    </small>

                </div>

            </div>


            <!-- Mobile close button -->

            <button
                type="button"
                class="sidebar-close"
                id="sidebarClose"
                aria-label="Close sidebar"
            >

                <i class="bi bi-x-lg"></i>

            </button>

        </div>


        <!-- NAVIGATION -->

        <nav class="sidebar-nav">


            <!-- DASHBOARD -->

            <a
                href="{% url 'admin_dashboard' %}"
                class="
                    sidebar-link
                    {% if request.resolver_match.url_name == 'admin_dashboard' %}
                        active
                    {% endif %}
                "
            >

                <i class="bi bi-grid-1x2-fill"></i>

                <span>
                    Dashboard
                </span>

            </a>


            <!-- ORDERS -->

            <a
                href="{% url 'admin_order_list' %}"
                class="
                    sidebar-link
                    {% if 'admin_order' in request.resolver_match.url_name %}
                        active
                    {% endif %}
                "
            >

                <i class="bi bi-bag-check"></i>

                <span>
                    Orders
                </span>

            </a>


            <!-- PRODUCTS -->

            <a
                href="{% url 'admin_product_list' %}"
                class="
                    sidebar-link
                    {% if 'admin_product' in request.resolver_match.url_name %}
                        active
                    {% endif %}
                "
            >

                <i class="bi bi-box-seam"></i>

                <span>
                    Products
                </span>

            </a>


            <!-- INVENTORY -->

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

                <span>
                    Inventory
                </span>

            </a>


            <!-- CATEGORIES -->

            <a
                href="{% url 'admin_category_list' %}"
                class="
                    sidebar-link
                    {% if 'admin_category' in request.resolver_match.url_name %}
                        active
                    {% endif %}
                "
            >

                <i class="bi bi-tags"></i>

                <span>
                    Categories
                </span>

            </a>


            <!-- BRANDS -->

            <a
                href="{% url 'admin_brand_list' %}"
                class="
                    sidebar-link
                    {% if 'admin_brand' in request.resolver_match.url_name %}
                        active
                    {% endif %}
                "
            >

                <i class="bi bi-award"></i>

                <span>
                    Brands
                </span>

            </a>


            <!-- CUSTOMERS -->

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

                <span>
                    Customers
                </span>

            </a>


            <!-- PAYMENTS -->

            <a
                href="#"
                class="sidebar-link"
            >

                <i class="bi bi-phone"></i>

                <span>
                    Payments
                </span>

            </a>


            <!-- DELIVERY -->

            <a
                href="#"
                class="sidebar-link"
            >

                <i class="bi bi-truck"></i>

                <span>
                    Delivery
                </span>

            </a>


            <!-- RETURNS -->

            <a
                href="#"
                class="sidebar-link"
            >

                <i class="bi bi-arrow-counterclockwise"></i>

                <span>
                    Returns & Refunds
                </span>

            </a>


            <!-- PROMOTIONS -->

            <a
                href="#"
                class="sidebar-link"
            >

                <i class="bi bi-tag"></i>

                <span>
                    Promotions
                </span>

            </a>


            <!-- REVIEWS -->

            <a
                href="#"
                class="sidebar-link"
            >

                <i class="bi bi-star"></i>

                <span>
                    Reviews
                </span>

            </a>


            <!-- REPORTS -->

            <a
                href="{% url 'admin_analytics' %}"
                class="
                    sidebar-link
                    {% if 'admin_analytics' in request.resolver_match.url_name %}
                        active
                    {% endif %}
                "
            >

                <i class="bi bi-bar-chart"></i>

                <span>
                    Reports
                </span>

            </a>


            <!-- NOTIFICATIONS -->

            <a
                href="#"
                class="sidebar-link"
            >

                <i class="bi bi-bell"></i>

                <span>
                    Notifications
                </span>

            </a>


            <!-- SETTINGS -->

            <a
                href="#"
                class="sidebar-link"
            >

                <i class="bi bi-gear"></i>

                <span>
                    Settings
                </span>

            </a>


        </nav>

    </aside>


    <!-- ==================================================
         MAIN AREA
    =================================================== -->

    <div class="admin-main">


        <!-- TOP NAVBAR -->

        <header class="admin-topbar">


            <!-- MOBILE HAMBURGER -->

            <button
                type="button"
                class="sidebar-toggle"
                id="sidebarToggle"
                aria-label="Open navigation"
                aria-controls="adminSidebar"
                aria-expanded="false"
            >

                <i class="bi bi-list"></i>

            </button>


            <!-- PAGE TITLE -->

            <div class="topbar-title">

                {% block page_heading %}
                    Dashboard
                {% endblock %}

            </div>


            <!-- TOPBAR ACTIONS -->

            <div class="topbar-actions">


                <a
                    href="/"
                    target="_blank"
                    class="
                        btn
                        btn-outline-secondary
                        btn-sm
                        view-store-button
                    "
                >

                    <i class="bi bi-box-arrow-up-right"></i>

                    <span>
                        View Store
                    </span>

                </a>


                <!-- USER MENU -->

                <div class="dropdown">

                    <button
                        class="
                            btn
                            dropdown-toggle
                            user-menu-button
                        "
                        type="button"
                        data-bs-toggle="dropdown"
                        aria-expanded="false"
                    >

                        <i class="bi bi-person-circle"></i>


                        <span class="topbar-username">

                            {{ request.user.get_full_name|default:request.user.username }}

                        </span>

                    </button>


                    <ul
                        class="
                            dropdown-menu
                            dropdown-menu-end
                        "
                    >

                        <li>

                            <a
                                class="dropdown-item"
                                href="{% url 'admin:index' %}"
                            >

                                <i class="bi bi-tools me-2"></i>

                                Django Admin

                            </a>

                        </li>


                        <li>

                            <hr class="dropdown-divider">

                        </li>


                        <li>

                            <a
                                class="dropdown-item"
                                href="/accounts/logout/"
                            >

                                <i class="bi bi-box-arrow-right me-2"></i>

                                Logout

                            </a>

                        </li>

                    </ul>

                </div>

            </div>

        </header>


        <!-- ==================================================
             PAGE CONTENT
        =================================================== -->

        <main class="admin-content">

            {% include "includes/messages.html" %}


            {% block admin_content %}
            {% endblock %}

        </main>


    </div>

</div>


<!-- Bootstrap JavaScript -->

<script
    src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.7/dist/js/bootstrap.bundle.min.js"
></script>


<!-- ======================================================
     RESPONSIVE SIDEBAR
====================================================== -->

<script>

(function () {

    const body = document.body;

    const sidebar = document.getElementById(
        "adminSidebar"
    );

    const toggle = document.getElementById(
        "sidebarToggle"
    );

    const closeButton = document.getElementById(
        "sidebarClose"
    );

    const overlay = document.getElementById(
        "sidebarOverlay"
    );


    if (
        !sidebar
        || !toggle
        || !overlay
    ) {
        return;
    }


    function isMobile() {

        return window.matchMedia(
            "(max-width: 991.98px)"
        ).matches;

    }


    function openSidebar() {

        if (!isMobile()) {
            return;
        }

        body.classList.add(
            "sidebar-open"
        );

        toggle.setAttribute(
            "aria-expanded",
            "true"
        );

    }


    function closeSidebar() {

        body.classList.remove(
            "sidebar-open"
        );

        toggle.setAttribute(
            "aria-expanded",
            "false"
        );

    }


    function toggleSidebar() {

        if (
            body.classList.contains(
                "sidebar-open"
            )
        ) {

            closeSidebar();

        } else {

            openSidebar();

        }

    }


    toggle.addEventListener(
        "click",
        toggleSidebar
    );


    overlay.addEventListener(
        "click",
        closeSidebar
    );


    if (closeButton) {

        closeButton.addEventListener(
            "click",
            closeSidebar
        );

    }


    sidebar.querySelectorAll(
        ".sidebar-link"
    ).forEach(function (link) {

        link.addEventListener(
            "click",
            function () {

                if (isMobile()) {

                    closeSidebar();

                }

            }
        );

    });


    document.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key === "Escape"
                && body.classList.contains(
                    "sidebar-open"
                )
            ) {

                closeSidebar();

            }

        }
    );


    window.addEventListener(
        "resize",
        function () {

            if (!isMobile()) {

                closeSidebar();

            }

        }
    );

})();

</script>


{% block extra_js %}
{% endblock %}


</body>

</html>
'''.strip() + "\n",
    encoding="utf-8",
)

print(
    "Clean responsive base.html created."
)


# ============================================================
# RESPONSIVE CSS
# ============================================================

css = css_path.read_text(
    encoding="utf-8-sig"
)


RESPONSIVE_MARKER = (
    "/* === PROFESSIONAL RESPONSIVE ADMIN V2 === */"
)


if RESPONSIVE_MARKER in css:

    css = css.split(
        RESPONSIVE_MARKER
    )[0].rstrip()


responsive_css = r'''

/* === PROFESSIONAL RESPONSIVE ADMIN V2 === */


/* =========================================================
   GLOBAL LAYOUT SAFETY
========================================================= */

html,
body {
    max-width: 100%;
    overflow-x: hidden;
}


.admin-layout {
    width: 100%;
}


.admin-main {
    width: calc(
        100% - var(--sidebar-width)
    );

    max-width: calc(
        100% - var(--sidebar-width)
    );

    transition:
        margin-left 0.25s ease,
        width 0.25s ease,
        max-width 0.25s ease;
}


.admin-content {
    width: 100%;
    min-width: 0;
}


.admin-content img {
    max-width: 100%;
}


.admin-content .row {
    min-width: 0;
}


.table-responsive {
    width: 100%;
    max-width: 100%;
}


/* =========================================================
   SIDEBAR ENHANCEMENTS
========================================================= */

.admin-sidebar {
    transition:
        transform 0.25s ease,
        box-shadow 0.25s ease;
}


.sidebar-brand {
    position: sticky;
    top: 0;

    z-index: 2;

    background: var(--sidebar-bg);
}


.sidebar-close {
    display: none;

    width: 38px;
    height: 38px;

    flex-shrink: 0;

    align-items: center;
    justify-content: center;

    padding: 0;

    border: 0;

    border-radius: 8px;

    background:
        rgba(255, 255, 255, 0.08);

    color: #ffffff;

    font-size: 18px;

    cursor: pointer;
}


.sidebar-close:hover {
    background:
        rgba(255, 255, 255, 0.14);
}


.sidebar-overlay {
    display: none;
}


/* =========================================================
   TOPBAR SAFETY
========================================================= */

.admin-topbar {
    min-width: 0;
}


.topbar-title {
    overflow: hidden;

    text-overflow: ellipsis;

    white-space: nowrap;
}


.topbar-actions {
    min-width: 0;
}


.user-menu-button {
    display: flex;

    align-items: center;

    gap: 7px;

    max-width: 240px;
}


.topbar-username {
    display: inline-block;

    max-width: 170px;

    overflow: hidden;

    text-overflow: ellipsis;

    white-space: nowrap;
}


/* =========================================================
   TABLE / CARD RESPONSIVENESS
========================================================= */

.dashboard-card {
    max-width: 100%;
    min-width: 0;
}


.dashboard-table {
    min-width: 720px;
}


.dashboard-table td,
.dashboard-table th {
    vertical-align: middle;
}


/* =========================================================
   TABLET + MOBILE
========================================================= */

@media (max-width: 991.98px) {

    body.sidebar-open {
        overflow: hidden;
    }


    .admin-main {
        margin-left: 0;

        width: 100%;

        max-width: 100%;
    }


    .admin-sidebar {
        width: min(
            300px,
            86vw
        );

        transform: translateX(-105%);

        z-index: 1050;

        box-shadow: none;
    }


    body.sidebar-open .admin-sidebar {
        transform: translateX(0);

        box-shadow:
            14px 0 40px
            rgba(0, 0, 0, 0.28);
    }


    .sidebar-toggle {
        display: inline-flex;

        align-items: center;
        justify-content: center;

        width: 42px;
        height: 42px;

        padding: 0;

        margin-right: 12px;

        border-radius: 9px;

        color: var(--text-primary);
    }


    .sidebar-toggle:hover {
        background: #f3f4f6;
    }


    .sidebar-close {
        display: inline-flex;
    }


    .sidebar-overlay {
        display: block;

        position: fixed;

        inset: 0;

        z-index: 1040;

        padding: 0;

        border: 0;

        visibility: hidden;

        opacity: 0;

        pointer-events: none;

        background:
            rgba(15, 23, 42, 0.55);

        backdrop-filter: blur(1px);

        transition:
            opacity 0.25s ease,
            visibility 0.25s ease;
    }


    body.sidebar-open
    .sidebar-overlay {
        visibility: visible;

        opacity: 1;

        pointer-events: auto;
    }


    .admin-topbar {
        height: 68px;

        padding:
            0
            18px;
    }


    .admin-content {
        padding: 20px;
    }


    .dashboard-heading h1 {
        font-size: 25px;
    }


    .dashboard-card {
        padding: 18px;
    }


    .card-header-custom {
        gap: 12px;

        flex-wrap: wrap;
    }

}


/* =========================================================
   PHONE
========================================================= */

@media (max-width: 767.98px) {

    .admin-topbar {
        padding:
            0
            14px;
    }


    .admin-content {
        padding:
            16px
            14px
            24px;
    }


    .topbar-title {
        font-size: 16px;
    }


    .view-store-button {
        display: none !important;
    }


    .topbar-username {
        display: none;
    }


    .user-menu-button {
        width: 40px;
        height: 40px;

        display: inline-flex;

        justify-content: center;

        padding: 0;

        border-radius: 50%;
    }


    .user-menu-button::after {
        display: none;
    }


    .user-menu-button i {
        margin: 0;

        font-size: 21px;
    }


    .dashboard-heading {
        margin-bottom: 18px;
    }


    .dashboard-heading h1 {
        font-size: 22px;
    }


    .dashboard-heading p {
        font-size: 14px;
    }


    .dashboard-card {
        padding: 15px;

        border-radius: 10px;
    }


    .mini-stat {
        gap: 12px;
    }


    .mini-stat strong {
        font-size: 21px;
    }


    .card-header-custom {
        align-items: flex-start;
    }


    .card-header-custom h2 {
        font-size: 17px;
    }


    .btn {
        max-width: 100%;
    }


    .input-group {
        max-width: 100%;
    }


    .form-control,
    .form-select {
        max-width: 100%;
    }


    .pagination {
        flex-wrap: wrap;
    }

}


/* =========================================================
   VERY SMALL PHONE
========================================================= */

@media (max-width: 479.98px) {

    .admin-sidebar {
        width: min(
            290px,
            90vw
        );
    }


    .admin-content {
        padding:
            14px
            10px
            22px;
    }


    .admin-topbar {
        padding:
            0
            10px;
    }


    .sidebar-toggle {
        width: 38px;
        height: 38px;

        margin-right: 8px;
    }


    .topbar-actions {
        gap: 6px;
    }


    .dashboard-card {
        padding: 13px;
    }


    .dashboard-heading h1 {
        font-size: 20px;
    }

}


/* =========================================================
   DESKTOP
========================================================= */

@media (min-width: 992px) {

    .admin-sidebar {
        transform: none !important;
    }


    .sidebar-toggle,
    .sidebar-close,
    .sidebar-overlay {
        display: none !important;
    }


    body {
        overflow-y: auto !important;
    }

}
'''


css = (
    css.rstrip()
    + "\n\n"
    + RESPONSIVE_MARKER
    + "\n"
    + responsive_css.strip()
    + "\n"
)


css_path.write_text(
    css,
    encoding="utf-8",
)


print(
    "Responsive admin CSS installed."
)

print()
print("=" * 68)
print("RESPONSIVE ADMIN SIDEBAR PATCH COMPLETE")
print("=" * 68)
print()
print("No migrations are required.")
print("Run:")
print("python manage.py check")
print()
