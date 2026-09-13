from django.urls import path
from . import views
from . import reports_views
from . import abandoned_cart_views
from core import settings_views
from orders import document_views
from orders import credit_note_views
from delivery.customer_views import (
    customer_delivery_tracking,
    available_delivery_options,
)



urlpatterns = [
    path(
        "admin/reports/",
        reports_views.sales_reports,
        name="admin_sales_reports",
    ),

    path(
        "admin/reports/export/",
        reports_views.sales_reports_csv,
        name="admin_sales_reports_csv",
    ),


    # =========================================================
    # CUSTOMER DELIVERY TRACKING
    # =========================================================

    path(
        "orders/<str:order_number>/track/",
        customer_delivery_tracking,
        name="customer_delivery_tracking",
    ),

    path(
        "delivery-options/",
        available_delivery_options,
        name="available_delivery_options",
    ),


    # =========================================================
    # CUSTOMER DASHBOARD
    # =========================================================

    path(
        "",
        views.dashboard,
        name="dashboard",
    ),

    path(
        "orders/",
        views.order_history,
        name="order_history",
    ),

    path(
        "orders/<str:order_number>/",
        views.order_detail,
        name="order_detail",
    ),

    path(
        "orders/<str:order_number>/invoice/",
        document_views.customer_invoice,
        name="customer_order_invoice",
    ),

    path(
        "orders/<str:order_number>/receipt/",
        document_views.customer_receipt,
        name="customer_order_receipt",
    ),

    path(
        "orders/<str:order_number>/documents/<str:document_type>/email/",
        document_views.customer_document_email,
        name="customer_order_document_email",
    ),

    path(
        "credit-notes/<int:refund_id>/",
        credit_note_views.customer_credit_note,
        name="customer_credit_note",
    ),

    path(
        "credit-notes/<int:refund_id>/email/",
        credit_note_views.customer_credit_note_email,
        name="customer_credit_note_email",
    ),


    # =========================================================
    # STORE MANAGEMENT DASHBOARD
    # =========================================================

    path(
        "admin/",
        views.admin_dashboard,
        name="admin_dashboard",
    ),


    # =========================================================
    # STORE SETTINGS
    # =========================================================

    path(
        "admin/settings/",
        settings_views.admin_store_settings,
        name="admin_store_settings",
    ),


    # =========================================================
    # ABANDONED CARTS
    # =========================================================

    path(
        "admin/abandoned-carts/",
        abandoned_cart_views.admin_abandoned_cart_list,
        name="admin_abandoned_cart_list",
    ),

    path(
        "admin/abandoned-carts/<int:pk>/",
        abandoned_cart_views.admin_abandoned_cart_detail,
        name="admin_abandoned_cart_detail",
    ),


    # =========================================================
    # ORDER MANAGEMENT
    # =========================================================

    path(
        "admin/orders/",
        views.admin_order_list,
        name="admin_order_list",
    ),

    path(
        "admin/orders/<str:order_number>/",
        views.admin_order_detail,
        name="admin_order_detail",
    ),

    path(
        "admin/orders/<str:order_number>/invoice/",
        document_views.admin_invoice,
        name="admin_order_invoice",
    ),

    path(
        "admin/orders/<str:order_number>/receipt/",
        document_views.admin_receipt,
        name="admin_order_receipt",
    ),

    path(
        "admin/orders/<str:order_number>/documents/<str:document_type>/email/",
        document_views.admin_document_email,
        name="admin_order_document_email",
    ),

    path(
        "admin/credit-notes/<int:refund_id>/",
        credit_note_views.admin_credit_note,
        name="admin_credit_note",
    ),

    path(
        "admin/credit-notes/<int:refund_id>/email/",
        credit_note_views.admin_credit_note_email,
        name="admin_credit_note_email",
    ),

    path(
        "admin/orders/<str:order_number>/status/",
        views.admin_order_update_status,
        name="admin_order_update_status",
    ),

    path(
        "admin/orders/<str:order_number>/shipping/",
        views.admin_order_update_shipping,
        name="admin_order_update_shipping",
    ),


    # =========================================================
    # PRODUCT MANAGEMENT
    # =========================================================

    path(
        "admin/products/",
        views.admin_product_list,
        name="admin_product_list",
    ),

    path(
        "admin/products/add/",
        views.admin_product_create,
        name="admin_product_create",
    ),

    path(
        "admin/products/<int:pk>/",
        views.admin_product_detail,
        name="admin_product_detail",
    ),

    path(
        "admin/products/<int:pk>/edit/",
        views.admin_product_edit,
        name="admin_product_edit",
    ),

    path(
        "admin/products/<int:pk>/toggle-active/",
        views.admin_product_toggle_active,
        name="admin_product_toggle_active",
    ),

    path(
        "admin/products/<int:pk>/toggle-featured/",
        views.admin_product_toggle_featured,
        name="admin_product_toggle_featured",
    ),


    # =========================================================
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


    # =========================================================
    # REPORTS / ANALYTICS
    # =========================================================

    path(
        "admin/analytics/",
        views.admin_analytics,
        name="admin_analytics",
    ),

    path(
        "admin/analytics/export/",
        views.admin_sales_export,
        name="admin_sales_export",
    ),

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

]
