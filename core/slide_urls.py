from django.urls import path

from . import slide_views


urlpatterns = [
    path("", slide_views.slide_list, name="homepage_slide_list"),
    path("add/", slide_views.slide_create, name="homepage_slide_create"),
    path("<int:pk>/edit/", slide_views.slide_edit, name="homepage_slide_edit"),
    path("<int:pk>/toggle/", slide_views.slide_toggle, name="homepage_slide_toggle"),
]
