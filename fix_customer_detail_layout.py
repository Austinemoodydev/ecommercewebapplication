from pathlib import Path
import shutil

path = Path(
    "templates/dashboard/admin/customers/detail.html"
)

backup = Path(
    "templates/dashboard/admin/customers/"
    "detail.html.before_layout_fix"
)

shutil.copy2(
    path,
    backup,
)

path.write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
{{ customer.username }} | Customer
{% endblock %}

{% block page_heading %}
Customer Profile
{% endblock %}

{% block admin_content %}


<!-- ======================================================
     HEADING
====================================================== -->

<div class="dashboard-heading">

    <div
        class="
            d-flex
            justify-content-between
            align-items-start
            flex-wrap
            gap-3
        "
    >

        <div>

            <h1>

                {% if customer.get_full_name %}

                    {{ customer.get_full_name }}

                {% else %}

                    {{ customer.username }}

                {% endif %}

            </h1>

            <p>

                Customer since
                {{ customer.date_joined|date:"d M Y" }}

                ·

                @{{ customer.username }}

            </p>

        </div>


        <div
            class="
                d-flex
                gap-2
                flex-wrap
            "
        >

            <a
                href="{% url 'crm_customer_list' %}"
                class="btn btn-outline-secondary"
            >
                <i class="bi bi-arrow-left"></i>
                Customers
            </a>


            {% if customer.email %}

                <a
                    href="mailto:{{ customer.email }}"
                    class="btn btn-outline-primary"
                >
                    <i class="bi bi-envelope"></i>
                    Email
                </a>

            {% endif %}


            {% if customer.phone %}

                <a
                    href="tel:{{ customer.phone }}"
                    class="btn btn-outline-success"
                >
                    <i class="bi bi-telephone"></i>
                    Call
                </a>

            {% endif %}

        </div>

    </div>

</div>


<!-- ======================================================
     METRICS
====================================================== -->

<div class="row g-3 mb-4">

    <div class="col-xl-3 col-md-6">

        <div class="dashboard-card mini-stat">

            <span>
                Total Orders
            </span>

            <strong>
                {{ total_orders }}
            </strong>

        </div>

    </div>


    <div class="col-xl-3 col-md-6">

        <div class="dashboard-card mini-stat">

            <span>
                Paid Orders
            </span>

            <strong>
                {{ paid_order_count }}
            </strong>

        </div>

    </div>


    <div class="col-xl-3 col-md-6">

        <div class="dashboard-card mini-stat">

            <span>
                Lifetime Spend
            </span>

            <strong>
                KES {{ lifetime_spend|floatformat:2 }}
            </strong>

        </div>

    </div>


    <div class="col-xl-3 col-md-6">

        <div class="dashboard-card mini-stat">

            <span>
                Last Order
            </span>

            <strong class="fs-6">

                {% if last_order %}

                    {{ last_order.created_at|date:"d M Y" }}

                {% else %}

                    Never

                {% endif %}

            </strong>

        </div>

    </div>

</div>


<!-- ======================================================
     PROFILE + ADDRESS
====================================================== -->

<div class="row g-3 mb-4">

    <div class="col-xl-5">

        <div class="dashboard-card">

            <div class="card-header-custom">

                <div>

                    <h2>
                        Account Information
                    </h2>

                    <p>
                        Customer contact and account status.
                    </p>

                </div>


                {% if customer.is_active %}

                    <span class="badge text-bg-success">
                        Active
                    </span>

                {% else %}

                    <span class="badge text-bg-secondary">
                        Inactive
                    </span>

                {% endif %}

            </div>


            <div class="table-responsive">

                <table
                    class="
                        table
                        dashboard-table
                        mb-0
                    "
                >

                    <tbody>

                        <tr>

                            <th style="width:38%;">
                                Username
                            </th>

                            <td>
                                {{ customer.username }}
                            </td>

                        </tr>


                        <tr>

                            <th>
                                Full Name
                            </th>

                            <td>

                                {% if customer.get_full_name %}

                                    {{ customer.get_full_name }}

                                {% else %}

                                    —
                                {% endif %}

                            </td>

                        </tr>


                        <tr>

                            <th>
                                Email
                            </th>

                            <td>
                                {{ customer.email|default:"—" }}
                            </td>

                        </tr>


                        <tr>

                            <th>
                                Phone
                            </th>

                            <td>
                                {{ customer.phone|default:"—" }}
                            </td>

                        </tr>


                        <tr>

                            <th>
                                Email Verification
                            </th>

                            <td>

                                {% if customer.email_verified %}

                                    <span class="badge text-bg-success">
                                        Verified
                                    </span>

                                {% else %}

                                    <span class="badge text-bg-warning">
                                        Unverified
                                    </span>

                                {% endif %}

                            </td>

                        </tr>


                        <tr>

                            <th>
                                Email Notifications
                            </th>

                            <td>

                                {% if customer.email_notifications %}

                                    <span class="text-success">
                                        Enabled
                                    </span>

                                {% else %}

                                    <span class="text-muted">
                                        Disabled
                                    </span>

                                {% endif %}

                            </td>

                        </tr>


                        <tr>

                            <th>
                                SMS Notifications
                            </th>

                            <td>

                                {% if customer.sms_notifications %}

                                    <span class="text-success">
                                        Enabled
                                    </span>

                                {% else %}

                                    <span class="text-muted">
                                        Disabled
                                    </span>

                                {% endif %}

                            </td>

                        </tr>

                    </tbody>

                </table>

            </div>


            <hr>


            <form
                method="POST"
                action="{% url 'crm_customer_toggle_status' customer.pk %}"
            >

                {% csrf_token %}

                {% if customer.is_active %}

                    <button
                        type="submit"
                        class="btn btn-outline-danger"
                        onclick="return confirm('Deactivate this customer account?');"
                    >
                        <i class="bi bi-person-x"></i>
                        Deactivate Account
                    </button>

                {% else %}

                    <button
                        type="submit"
                        class="btn btn-success"
                    >
                        <i class="bi bi-person-check"></i>
                        Activate Account
                    </button>

                {% endif %}

            </form>

        </div>

    </div>


    <!-- ADDRESS -->

    <div class="col-xl-7">

        <div class="dashboard-card">

            <div class="card-header-custom">

                <div>

                    <h2>
                        Saved Addresses
                    </h2>

                    <p>
                        Customer delivery addresses.
                    </p>

                </div>

                <span class="badge text-bg-light border">
                    {{ addresses|length }}
                </span>

            </div>


            <div class="row g-3">

                {% for address in addresses %}

                    <div class="col-md-6">

                        <div
                            class="
                                border
                                rounded
                                p-3
                                h-100
                            "
                        >

                            <div
                                class="
                                    d-flex
                                    justify-content-between
                                    align-items-start
                                    gap-2
                                    mb-2
                                "
                            >

                                <strong>
                                    {{ address.full_name }}
                                </strong>

                                {% if address.is_default %}

                                    <span
                                        class="
                                            badge
                                            text-bg-primary
                                        "
                                    >
                                        Default
                                    </span>

                                {% endif %}

                            </div>


                            <div class="small">

                                <div class="mb-1">

                                    <i
                                        class="
                                            bi
                                            bi-telephone
                                            me-1
                                        "
                                    ></i>

                                    {{ address.phone }}

                                </div>


                                <div class="text-muted">

                                    {{ address.house_number }}

                                    {% if address.estate %}
                                        ,
                                        {{ address.estate }}
                                    {% endif %}

                                    <br>

                                    {{ address.city }}

                                    {% if address.county %}
                                        ,
                                        {{ address.county }}
                                    {% endif %}


                                    {% if address.landmark %}

                                        <br>

                                        <span>
                                            Landmark:
                                            {{ address.landmark }}
                                        </span>

                                    {% endif %}

                                </div>

                            </div>

                        </div>

                    </div>

                {% empty %}

                    <div class="col-12">

                        <div
                            class="
                                text-center
                                py-5
                                text-muted
                            "
                        >

                            <i
                                class="
                                    bi
                                    bi-geo-alt
                                    fs-1
                                "
                            ></i>

                            <p class="mt-2 mb-0">
                                No saved addresses.
                            </p>

                        </div>

                    </div>

                {% endfor %}

            </div>

        </div>

    </div>

</div>


<!-- ======================================================
     CRM NOTES
====================================================== -->

<div class="dashboard-card mb-4">

    <div class="card-header-custom">

        <div>

            <h2>
                Internal CRM Notes
            </h2>

            <p>
                Private notes visible only to staff.
            </p>

        </div>

        <i
            class="
                bi
                bi-journal-text
                fs-4
                text-muted
            "
        ></i>

    </div>


    <form
        method="POST"
        action="{% url 'crm_customer_note_add' customer.pk %}"
        class="
            border
            rounded
            p-3
            mb-4
            bg-body-tertiary
        "
    >

        {% csrf_token %}


        <label class="form-label fw-semibold">
            Add Note
        </label>

        {{ note_form.note }}


        {% if note_form.note.errors %}

            <div class="text-danger small mt-1">
                {{ note_form.note.errors }}
            </div>

        {% endif %}


        <div
            class="
                d-flex
                justify-content-between
                align-items-center
                flex-wrap
                gap-3
                mt-3
            "
        >

            <div class="form-check">

                {{ note_form.is_pinned }}

                <label
                    class="form-check-label"
                    for="{{ note_form.is_pinned.id_for_label }}"
                >
                    Pin this note
                </label>

            </div>


            <button
                type="submit"
                class="btn btn-primary"
            >
                <i class="bi bi-plus-lg"></i>
                Add Note
            </button>

        </div>

    </form>


    {% for note in notes %}

        <div
            class="
                border
                rounded
                p-3
                mb-3
            "
        >

            <div
                class="
                    d-flex
                    justify-content-between
                    align-items-start
                    gap-3
                "
            >

                <div class="flex-grow-1">

                    {% if note.is_pinned %}

                        <span
                            class="
                                badge
                                text-bg-warning
                                mb-2
                            "
                        >
                            <i class="bi bi-pin-angle-fill"></i>
                            Pinned
                        </span>

                    {% endif %}


                    <div
                        style="
                            white-space:pre-wrap;
                        "
                    >{{ note.note }}</div>


                    <small
                        class="
                            text-muted
                            d-block
                            mt-2
                        "
                    >

                        <i class="bi bi-clock"></i>

                        {{ note.created_at|date:"d M Y H:i" }}

                        {% if note.created_by %}

                            ·

                            {{ note.created_by.get_full_name|default:note.created_by.username }}

                        {% endif %}

                    </small>

                </div>


                <div class="d-flex gap-2">

                    <form
                        method="POST"
                        action="{% url 'crm_customer_note_toggle_pin' customer.pk note.pk %}"
                    >

                        {% csrf_token %}

                        <button
                            type="submit"
                            class="
                                btn
                                btn-sm
                                btn-outline-secondary
                            "
                            title="Pin or unpin note"
                        >
                            <i class="bi bi-pin-angle"></i>
                        </button>

                    </form>


                    <form
                        method="POST"
                        action="{% url 'crm_customer_note_delete' customer.pk note.pk %}"
                        onsubmit="return confirm('Delete this customer note?');"
                    >

                        {% csrf_token %}

                        <button
                            type="submit"
                            class="
                                btn
                                btn-sm
                                btn-outline-danger
                            "
                            title="Delete note"
                        >
                            <i class="bi bi-trash"></i>
                        </button>

                    </form>

                </div>

            </div>

        </div>

    {% empty %}

        <div
            class="
                text-center
                text-muted
                py-4
            "
        >

            <i
                class="
                    bi
                    bi-journal
                    fs-2
                "
            ></i>

            <p class="mt-2 mb-0">
                No CRM notes for this customer.
            </p>

        </div>

    {% endfor %}

</div>


<!-- ======================================================
     ORDER HISTORY
====================================================== -->

<div class="dashboard-card">

    <div class="card-header-custom">

        <div>

            <h2>
                Order History
            </h2>

            <p>
                Orders placed by this customer.
            </p>

        </div>

    </div>


    <div class="table-responsive">

        <table
            class="
                table
                dashboard-table
                align-middle
            "
        >

            <thead>

                <tr>

                    <th>
                        Order
                    </th>

                    <th>
                        Date
                    </th>

                    <th>
                        Items
                    </th>

                    <th>
                        Total
                    </th>

                    <th>
                        Payment
                    </th>

                    <th>
                        Status
                    </th>

                    <th class="text-end">
                        Action
                    </th>

                </tr>

            </thead>


            <tbody>

                {% for order in orders %}

                    <tr>

                        <td>

                            <strong>
                                {{ order.order_number }}
                            </strong>

                        </td>


                        <td>

                            {{ order.created_at|date:"d M Y" }}

                            <small
                                class="
                                    d-block
                                    text-muted
                                "
                            >
                                {{ order.created_at|date:"H:i" }}
                            </small>

                        </td>


                        <td>
                            {{ order.items.count }}
                        </td>


                        <td>

                            <strong>
                                KES
                                {{ order.total_amount|floatformat:2 }}
                            </strong>

                        </td>


                        <td>

                            {% if order.payment_status == "paid" %}

                                <span class="badge text-bg-success">
                                    Paid
                                </span>

                            {% elif order.payment_status == "failed" %}

                                <span class="badge text-bg-danger">
                                    Failed
                                </span>

                            {% elif order.payment_status == "refunded" %}

                                <span class="badge text-bg-info">
                                    Refunded
                                </span>

                            {% else %}

                                <span class="badge text-bg-warning">
                                    Pending
                                </span>

                            {% endif %}

                        </td>


                        <td>

                            {% if order.status == "delivered" %}

                                <span class="badge text-bg-success">
                                    {{ order.get_status_display }}
                                </span>

                            {% elif order.status == "cancelled" %}

                                <span class="badge text-bg-danger">
                                    {{ order.get_status_display }}
                                </span>

                            {% elif order.status == "shipped" %}

                                <span class="badge text-bg-primary">
                                    {{ order.get_status_display }}
                                </span>

                            {% else %}

                                <span class="badge text-bg-secondary">
                                    {{ order.get_status_display }}
                                </span>

                            {% endif %}

                        </td>


                        <td class="text-end">

                            <a
                                href="{% url 'admin_order_detail' order.order_number %}"
                                class="
                                    btn
                                    btn-sm
                                    btn-outline-primary
                                "
                            >
                                <i class="bi bi-eye"></i>
                                View
                            </a>

                        </td>

                    </tr>

                {% empty %}

                    <tr>

                        <td
                            colspan="7"
                            class="
                                text-center
                                text-muted
                                py-5
                            "
                        >

                            <i
                                class="
                                    bi
                                    bi-bag
                                    fs-1
                                "
                            ></i>

                            <p class="mt-2 mb-0">
                                This customer has no orders yet.
                            </p>

                        </td>

                    </tr>

                {% endfor %}

            </tbody>

        </table>

    </div>


    {% if page_obj.paginator.num_pages > 1 %}

        <div
            class="
                d-flex
                justify-content-between
                align-items-center
                pt-3
                border-top
            "
        >

            <small class="text-muted">

                Page
                {{ page_obj.number }}
                of
                {{ page_obj.paginator.num_pages }}

            </small>


            <div>

                {% if page_obj.has_previous %}

                    <a
                        href="?page={{ page_obj.previous_page_number }}"
                        class="btn btn-sm btn-outline-secondary"
                    >
                        Previous
                    </a>

                {% endif %}


                {% if page_obj.has_next %}

                    <a
                        href="?page={{ page_obj.next_page_number }}"
                        class="btn btn-sm btn-outline-secondary"
                    >
                        Next
                    </a>

                {% endif %}

            </div>

        </div>

    {% endif %}

</div>


{% endblock %}
'''.strip() + "\n",
    encoding="utf-8",
)

print(
    "Customer detail layout fixed."
)
print(
    "Backup:",
    backup,
)
