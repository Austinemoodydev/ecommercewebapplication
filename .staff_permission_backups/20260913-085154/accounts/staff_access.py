from django.contrib import messages
from django.shortcuts import redirect
from django.urls import resolve

from .store_roles import (
    STORE_OWNER,
    STORE_MANAGER,
    ORDER_STAFF,
    INVENTORY_STAFF,
    FINANCE_STAFF,
    SUPPORT_STAFF,
)


ALL_MANAGEMENT_ROLES = {
    STORE_OWNER,
    STORE_MANAGER,
    ORDER_STAFF,
    INVENTORY_STAFF,
    FINANCE_STAFF,
    SUPPORT_STAFF,
}


def user_store_roles(user):
    if not user.is_authenticated:
        return set()

    return set(
        user.groups.values_list(
            "name",
            flat=True,
        )
    )


def is_store_owner(user):

    if not user.is_authenticated:
        return False

    return (
        user.is_superuser
        or STORE_OWNER in user_store_roles(user)
    )


def can_access_store_management(user):

    if not user.is_authenticated:
        return False

    if not user.is_active or not user.is_staff:
        return False

    if user.is_superuser:
        return True

    return bool(
        user_store_roles(user)
        & ALL_MANAGEMENT_ROLES
    )


ROLE_URL_ACCESS = {

    STORE_OWNER: "*",

    STORE_MANAGER: {
        "admin_dashboard",
        "admin_analytics",
        "admin_sales_export",
        "admin_sales_reports",
        "admin_sales_reports_csv",

        "admin_order_list",
        "admin_order_detail",
        "admin_order_invoice",
        "admin_order_receipt",
        "admin_order_document_email",
        "admin_order_update_status",
        "admin_order_update_shipping",

        "admin_product_list",
        "admin_product_create",
        "admin_product_detail",
        "admin_product_edit",
        "admin_product_toggle_active",
        "admin_product_toggle_featured",
        "admin_product_gallery",
        "admin_product_gallery_delete",
        "admin_product_variant_create",
        "admin_product_variant_edit",
        "admin_product_variant_toggle",
        "admin_product_variant_archive",

        "admin_category_list",
        "admin_category_create",
        "admin_category_edit",
        "admin_category_toggle",

        "admin_brand_list",
        "admin_brand_create",
        "admin_brand_edit",
        "admin_brand_toggle",

        "inventory_dashboard",
        "inventory_export_csv",
        "inventory_movement_list",
        "inventory_product_detail",
        "inventory_product_adjust",
        "inventory_variant_adjust",

        "crm_customer_list",
        "crm_customer_export_csv",
        "crm_customer_detail",
        "crm_customer_toggle_status",
        "crm_customer_note_add",
        "crm_customer_note_toggle_pin",
        "crm_customer_note_delete",

        "delivery_list",
        "delivery_detail",
        "delivery_assign",
        "delivery_update_status",
        "delivery_add_attempt",
        "delivery_set_quote",
        "delivery_zone_list",
        "delivery_provider_list",

        "admin_payment_list",
        "admin_payment_detail",

        "admin_returns_refunds",
        "admin_return_detail",
        "admin_refund_detail",

        "admin_notifications",
        "admin_notification_detail",

        "admin_abandoned_cart_list",
        "admin_abandoned_cart_detail",
    },


    ORDER_STAFF: {
        "admin_dashboard",

        "admin_order_list",
        "admin_order_detail",
        "admin_order_invoice",
        "admin_order_receipt",
        "admin_order_document_email",
        "admin_order_update_status",
        "admin_order_update_shipping",

        "delivery_list",
        "delivery_detail",
        "delivery_assign",
        "delivery_update_status",
        "delivery_add_attempt",
        "delivery_set_quote",
    },


    INVENTORY_STAFF: {
        "admin_dashboard",

        "admin_product_list",
        "admin_product_create",
        "admin_product_detail",
        "admin_product_edit",
        "admin_product_toggle_active",
        "admin_product_toggle_featured",
        "admin_product_gallery",
        "admin_product_gallery_delete",
        "admin_product_variant_create",
        "admin_product_variant_edit",
        "admin_product_variant_toggle",
        "admin_product_variant_archive",

        "admin_category_list",
        "admin_category_create",
        "admin_category_edit",
        "admin_category_toggle",

        "admin_brand_list",
        "admin_brand_create",
        "admin_brand_edit",
        "admin_brand_toggle",

        "inventory_dashboard",
        "inventory_export_csv",
        "inventory_movement_list",
        "inventory_product_detail",
        "inventory_product_adjust",
        "inventory_variant_adjust",
    },


    FINANCE_STAFF: {
        "admin_dashboard",
        "admin_analytics",
        "admin_sales_export",
        "admin_sales_reports",
        "admin_sales_reports_csv",

        "admin_order_list",
        "admin_order_detail",
        "admin_order_invoice",
        "admin_order_receipt",

        "admin_payment_list",
        "admin_payment_export_csv",
        "admin_payment_detail",
        "admin_payment_review_resolve",
        "admin_payment_review_reopen",

        "admin_returns_refunds",
        "admin_return_detail",
        "admin_return_review",
        "admin_return_complete",
        "admin_refund_detail",
        "admin_refund_review",
        "admin_refund_process",

        "admin_credit_note",
        "admin_credit_note_email",
    },


    SUPPORT_STAFF: {
        "admin_dashboard",

        "admin_order_list",
        "admin_order_detail",
        "admin_order_invoice",
        "admin_order_receipt",

        "crm_customer_list",
        "crm_customer_detail",
        "crm_customer_note_add",
        "crm_customer_note_toggle_pin",

        "admin_notifications",
        "admin_notification_detail",

        "admin_abandoned_cart_list",
        "admin_abandoned_cart_detail",
    },
}


class StoreStaffPermissionMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        path = request.path

        protected = (
            path.startswith("/dashboard/admin/")
            or path.startswith("/staff/manage/")
        )

        if not protected:
            return self.get_response(request)

        user = request.user

        if not user.is_authenticated:
            return self.get_response(request)

        if not user.is_staff:
            return self.get_response(request)

        if user.is_superuser:
            return self.get_response(request)

        try:
            match = resolve(request.path_info)
            url_name = match.url_name
        except Exception:
            return self.get_response(request)

        roles = user_store_roles(user)

        if path.startswith("/staff/manage/"):

            if STORE_OWNER not in roles:
                messages.error(
                    request,
                    "Only the Store Owner can manage staff accounts.",
                )

                return redirect(
                    "admin_dashboard"
                )

            return self.get_response(request)


        for role in roles:

            allowed = ROLE_URL_ACCESS.get(
                role,
                set(),
            )

            if allowed == "*":
                return self.get_response(request)

            if url_name in allowed:
                return self.get_response(request)


        messages.error(
            request,
            (
                "You do not have permission to access "
                "that management area."
            ),
        )

        return redirect(
            "admin_dashboard"
        )
