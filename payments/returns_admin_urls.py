from django.urls import path

from . import returns_admin_views as views


urlpatterns = [

    path(
        "",
        views.returns_refunds_list,
        name="admin_returns_refunds",
    ),

    path(
        "returns/<int:pk>/",
        views.return_detail,
        name="admin_return_detail",
    ),

    path(
        "returns/<int:pk>/review/",
        views.return_review,
        name="admin_return_review",
    ),

    path(
        "returns/<int:pk>/complete/",
        views.return_complete,
        name="admin_return_complete",
    ),

    path(
        "refunds/<int:pk>/",
        views.refund_detail,
        name="admin_refund_detail",
    ),

    path(
        "refunds/<int:pk>/review/",
        views.refund_review,
        name="admin_refund_review",
    ),

    path(
        "refunds/<int:pk>/process/",
        views.refund_process,
        name="admin_refund_process",
    ),
]
