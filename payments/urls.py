from django.urls import path
from . import views
from . import customer_returns

urlpatterns = [
    path(
        "my-returns/",
        customer_returns.customer_returns_refunds,
        name="customer_returns_refunds",
    ),

    path(
        "my-returns/returns/<int:pk>/",
        customer_returns.customer_return_detail,
        name="customer_return_detail",
    ),

    path(
        "my-returns/refunds/<int:pk>/",
        customer_returns.customer_refund_detail,
        name="customer_refund_detail",
    ),

    path("pay/<str:order_number>/", views.initiate_payment, name="initiate_payment"),
    path("callback/", views.mpesa_callback, name="mpesa_callback"),
    path("status/<str:order_number>/", views.check_payment_status, name="check_payment_status"),
    path(
        "refund/<str:order_number>/",
        customer_returns.request_refund,
        name="request_refund",
    ),
    path(
        "return/<str:order_number>/",
        customer_returns.request_return,
        name="request_return",
    ),
]
