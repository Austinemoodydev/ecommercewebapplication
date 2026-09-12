from pathlib import Path
import shutil


ROOT = Path.cwd()

BASE = (
    ROOT
    / "templates"
    / "orders"
    / "documents"
    / "base.html"
)

VIEWS = (
    ROOT
    / "orders"
    / "credit_note_views.py"
)


for path in [
    BASE,
    VIEWS,
]:

    if not path.exists():

        raise RuntimeError(
            f"Missing required file: {path}"
        )

    backup = Path(
        str(path)
        + ".phase10c-render-fix-backup"
    )

    if not backup.exists():

        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# 1. FIX CREDIT NOTE VIEW CONTEXT
# ============================================================

text = VIEWS.read_text(
    encoding="utf-8-sig"
)


old = '''        {
            "document":
                document,

            "snapshot":
                document.snapshot,

            "order":
                document.order,
        },
'''


new = '''        {
            "document":
                document,

            "snapshot":
                document.snapshot,

            "order":
                document.order,

            "is_credit_note":
                True,

            "credit_note_email_url_name":
                (
                    "admin_credit_note_email"
                    if request.user.is_staff
                    else
                    "customer_credit_note_email"
                ),
        },
'''


if old not in text:

    if (
        '"is_credit_note":'
        in text
        and
        '"credit_note_email_url_name":'
        in text
    ):

        print(
            "Credit-note view context "
            "already repaired."
        )

    else:

        raise RuntimeError(
            "Could not locate "
            "_render_credit_note context."
        )

else:

    text = text.replace(
        old,
        new,
        1,
    )

    VIEWS.write_text(
        text,
        encoding="utf-8",
    )

    print(
        "Credit-note view context repaired."
    )


# ============================================================
# 2. FIX SHARED DOCUMENT TOOLBAR
# ============================================================

text = BASE.read_text(
    encoding="utf-8-sig"
)


old = '''        <form
            method="post"
            action="{% url email_url_name order.order_number document.document_type %}"
        >

            {% csrf_token %}

            <button type="submit">
                Email Customer
            </button>

        </form>
'''


new = '''        {% if is_credit_note %}

            <form
                method="post"
                action="{% url credit_note_email_url_name document.refund_request_id %}"
            >

                {% csrf_token %}

                <button type="submit">
                    Email Customer
                </button>

            </form>

        {% else %}

            <form
                method="post"
                action="{% url email_url_name order.order_number document.document_type %}"
            >

                {% csrf_token %}

                <button type="submit">
                    Email Customer
                </button>

            </form>

        {% endif %}
'''


if old not in text:

    if (
        "credit_note_email_url_name"
        in text
        and
        "document.refund_request_id"
        in text
    ):

        print(
            "Shared document toolbar "
            "already repaired."
        )

    else:

        raise RuntimeError(
            "Could not locate Phase 10B "
            "email form in base.html."
        )

else:

    text = text.replace(
        old,
        new,
        1,
    )

    BASE.write_text(
        text,
        encoding="utf-8",
    )

    print(
        "Shared document toolbar repaired."
    )


print()
print("=" * 72)
print("PHASE 10C RENDER REPAIR COMPLETE")
print("=" * 72)
print()
print(
    "Credit notes now use refund_id-based "
    "email routes."
)
print(
    "Invoices and receipts keep their "
    "existing order-number routes."
)
print()
print("No migration required.")
