from pathlib import Path
import shutil

path = Path(
    "templates/dashboard/admin/base.html"
)

backup = Path(
    "templates/dashboard/admin/"
    "base.html.catalogbackup"
)

shutil.copy2(
    path,
    backup,
)

text = path.read_text(
    encoding="utf-8-sig"
)

if "admin_category_list" not in text:

    marker = '''
<a
    href="{% url 'admin_analytics' %}
'''

    # Find Analytics navigation area.
    pos = text.find(
        "{% url 'admin_analytics' %}"
    )

    if pos == -1:

        raise RuntimeError(
            "Could not find Analytics sidebar link."
        )

    start = text.rfind(
        "<a",
        0,
        pos,
    )

    new_links = r'''
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

'''

    text = (
        text[:start]
        + new_links
        + text[start:]
    )

    path.write_text(
        text,
        encoding="utf-8",
    )

    print(
        "Categories and Brands added to sidebar."
    )

else:

    print(
        "Catalog sidebar links already exist."
    )
