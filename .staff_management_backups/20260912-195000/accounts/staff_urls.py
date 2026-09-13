from django.urls import path

from .views import StoreStaffLoginView


urlpatterns = [

    path(
        "login/",
        StoreStaffLoginView.as_view(),
        name="staff_login",
    ),

]
