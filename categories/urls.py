from django.urls import path

from . import views

urlpatterns = [
    path("", views.category_list, name="category_list"),
    path("<slug:slug>/", views.category_detail, name="category_detail"),
]
