from django.conf import settings
from django.http import HttpResponse


def robots_txt(request):
    sitemap_url = f"{settings.SITE_URL}/sitemap.xml"
    content = "User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /accounts/\nDisallow: /cart/\nDisallow: /checkout/\nDisallow: /dashboard/\nDisallow: /payments/\nDisallow: /wishlist/\nDisallow: /reviews/\n\nSitemap: " + sitemap_url + "\n"
    return HttpResponse(content, content_type="text/plain")