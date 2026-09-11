from pathlib import Path
import shutil

path = Path(
    "templates/dashboard/admin/base.html"
)

backup = Path(
    "templates/dashboard/admin/"
    "base.html.before_sidebar_cleanup"
)

shutil.copy2(path, backup)

text = path.read_text(
    encoding="utf-8-sig"
)

start_marker = '<nav class="sidebar-nav">'
end_marker = '</nav>'

start = text.find(start_marker)

if start == -1:
    raise RuntimeError(
        "Could not find sidebar navigation."
    )

end = text.find(
    end_marker,
    start
)

if end == -1:
    raise RuntimeError(
        "Could not find sidebar closing tag."
    )

end += len(end_marker)


clean_sidebar = r'''<nav class="sidebar-nav">

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
                <span>Dashboard</span>
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
                <span>Orders</span>
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
                <span>Products</span>
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
                <span>Inventory</span>
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
                <span>Categories</span>
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
                <span>Brands</span>
            </a>


            <!-- FUTURE CUSTOMER MANAGEMENT -->
            <a
                href="#"
                class="sidebar-link"
            >
                <i class="bi bi-people"></i>
                <span>Customers</span>
            </a>


            <!-- FUTURE PAYMENT MANAGEMENT -->
            <a
                href="#"
                class="sidebar-link"
            >
                <i class="bi bi-phone"></i>
                <span>Payments</span>
            </a>


            <!-- FUTURE DELIVERY MANAGEMENT -->
            <a
                href="#"
                class="sidebar-link"
            >
                <i class="bi bi-truck"></i>
                <span>Delivery</span>
            </a>


            <!-- FUTURE RETURNS -->
            <a
                href="#"
                class="sidebar-link"
            >
                <i class="bi bi-arrow-counterclockwise"></i>
                <span>Returns & Refunds</span>
            </a>


            <!-- FUTURE PROMOTIONS -->
            <a
                href="#"
                class="sidebar-link"
            >
                <i class="bi bi-tag"></i>
                <span>Promotions</span>
            </a>


            <!-- FUTURE REVIEWS -->
            <a
                href="#"
                class="sidebar-link"
            >
                <i class="bi bi-star"></i>
                <span>Reviews</span>
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
                <span>Reports</span>
            </a>


            <!-- FUTURE NOTIFICATIONS -->
            <a
                href="#"
                class="sidebar-link"
            >
                <i class="bi bi-bell"></i>
                <span>Notifications</span>
            </a>


            <!-- FUTURE SETTINGS -->
            <a
                href="#"
                class="sidebar-link"
            >
                <i class="bi bi-gear"></i>
                <span>Settings</span>
            </a>

        </nav>'''


text = (
    text[:start]
    + clean_sidebar
    + text[end:]
)

path.write_text(
    text,
    encoding="utf-8",
)

print()
print("=" * 60)
print("SIDEBAR CLEANED SUCCESSFULLY")
print("=" * 60)
print()
print("Backup:")
print(backup)
