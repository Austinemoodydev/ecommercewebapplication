from django.urls import path

from notifications import views


urlpatterns = [

    # ========================================================
    # CUSTOMER
    # ========================================================

    path(
        "",
        views.customer_notifications,
        name="customer_notifications",
    ),

    path(
        "<int:notification_id>/read/",
        views.customer_notification_mark_read,
        name="customer_notification_mark_read",
    ),

    path(
        "mark-all-read/",
        views.customer_notifications_mark_all_read,
        name="customer_notifications_mark_all_read",
    ),


    path(
        "preferences/",
        views.notification_preferences,
        name="notification_preferences",
    ),


    # ========================================================
    # ADMIN
    # ========================================================

    path(
        "admin/",
        views.admin_notifications,
        name="admin_notifications",
    ),


    path(
        "admin/bulk-retry/",
        views.admin_bulk_retry_notifications,
        name="admin_bulk_retry_notifications",
    ),

    path(
        "admin/<int:notification_id>/",
        views.admin_notification_detail,
        name="admin_notification_detail",
    ),

    path(
        "admin/<int:notification_id>/retry/",
        views.admin_retry_notification,
        name="admin_retry_notification",
    ),


    path(
        "admin/<int:notification_id>/retry/<str:channel>/",
        views.admin_retry_notification_channel,
        name="admin_retry_notification_channel",
    ),

]
