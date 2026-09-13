
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, include
from django.conf import settings
from django.conf.urls.static import static
from core.sitemaps import sitemaps

urlpatterns = [
    path("notifications/", include("notifications.urls")),

    path(
        "dashboard/admin/returns/",
        include("payments.returns_admin_urls"),
    ),

    path(
        "dashboard/admin/delivery/",
        include("delivery.urls"),
    ),

    path(
        "dashboard/admin/payments/",
        include("payments.admin_urls"),
    ),

    path(
        "dashboard/admin/customers/",
        include("crm.urls"),
    ),

    path(
        "dashboard/admin/inventory/",
        include("inventory.urls"),
    ),

    path('admin/', admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("robots.txt", include("core.robots_urls")),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('accounts/social/', include('allauth.urls')),
    path("shop/", include("products.urls")),
    path("categories/", include("categories.urls")),
    path("cart/", include("cart.urls")),
    path("wishlist/", include("wishlist.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("checkout/", include("orders.urls")),
    path("payments/", include("payments.urls")),
    path("reviews/", include("reviews.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)

