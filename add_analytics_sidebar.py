from pathlib import Path
import re
import shutil

ROOT = Path.cwd()

BASE = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "base.html"
)

backup = Path(
    str(BASE) + ".analytics-sidebar-backup"
)

if not backup.exists():
    shutil.copy2(BASE, backup)

html = BASE.read_text(
    encoding="utf-8-sig"
)


# ============================================================
# DO NOT ADD DUPLICATE ANALYTICS LINK
# ============================================================

if "{% url 'admin_analytics' %}" in html:

    print(
        "Analytics sidebar link already exists."
    )

else:

    # Insert Analytics directly after Dashboard.
    dashboard_pattern = re.compile(
        r'''
        (
            <a\b
            (?:
                (?!</a>).
            )*?
            <span>
            \s*
            Dashboard
            \s*
            </span>
            (?:
                (?!</a>).
            )*?
            </a>
        )
        ''',
        re.S | re.X,
    )

    matches = list(
        dashboard_pattern.finditer(
            html
        )
    )

    if len(matches) != 1:

        raise RuntimeError(
            "Expected exactly one Dashboard "
            f"sidebar item, found {len(matches)}."
        )


    analytics_link = r'''

            <a
                href="{% url 'admin_analytics' %}"
                class="
                    sidebar-link
                    {% if request.resolver_match.url_name == 'admin_analytics' %}
                        active
                    {% endif %}
                "
            >

                <i class="bi bi-graph-up-arrow"></i>

                <span>
                    Analytics
                </span>

            </a>
'''

    match = matches[0]

    html = (
        html[:match.end()]
        + analytics_link
        + html[match.end():]
    )


BASE.write_text(
    html,
    encoding="utf-8",
)


# ============================================================
# VALIDATION
# ============================================================

final = BASE.read_text(
    encoding="utf-8-sig"
)

if final.count(
    "{% url 'admin_analytics' %}"
) != 1:

    raise RuntimeError(
        "Analytics sidebar validation failed."
    )


print()
print("=" * 70)
print("ANALYTICS SIDEBAR LINK ADDED")
print("=" * 70)
print()
print("Dashboard")
print("Analytics")
print("Orders")
print("Products")
print("...")
