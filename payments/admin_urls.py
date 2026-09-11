from django.urls import path

from . import admin_views


urlpatterns = [

    path(
        "",
        admin_views.admin_payment_list,
        name="admin_payment_list",
    ),

    path(
        "export/",
        admin_views.admin_payment_export_csv,
        name="admin_payment_export_csv",
    ),

    path(
        "<int:pk>/",
        admin_views.admin_payment_detail,
        name="admin_payment_detail",
    ),

    path(
        "<int:pk>/review/resolve/",
        admin_views.admin_payment_review_resolve,
        name="admin_payment_review_resolve",
    ),

    path(
        "<int:pk>/review/reopen/",
        admin_views.admin_payment_review_reopen,
        name="admin_payment_review_reopen",
    ),

]
