from django.urls import path
from . import views

urlpatterns = [
    path("pay/<str:order_number>/", views.initiate_payment, name="initiate_payment"),
    path("callback/", views.mpesa_callback, name="mpesa_callback"),
    path("status/<str:order_number>/", views.check_payment_status, name="check_payment_status"),
]
