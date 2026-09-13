from django.urls import path

from .views import StoreStaffLoginView
from . import staff_management


urlpatterns = [

    path(
        "login/",
        StoreStaffLoginView.as_view(),
        name="staff_login",
    ),


    path(
        "manage/",
        staff_management.staff_list,
        name="staff_manage_list",
    ),

    path(
        "manage/add/",
        staff_management.staff_create,
        name="staff_manage_create",
    ),

    path(
        "manage/<int:pk>/edit/",
        staff_management.staff_edit,
        name="staff_manage_edit",
    ),

    path(
        "manage/<int:pk>/toggle-active/",
        staff_management.staff_toggle_active,
        name="staff_manage_toggle_active",
    ),
]
