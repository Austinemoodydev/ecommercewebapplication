from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from categories.models import Category
from products.models import Product


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return ["home", "shop", "offers", "category_list"]

    def location(self, item):
        return reverse(item)


class ProductSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.7

    def items(self):
        return Product.objects.filter(is_active=True).only("slug", "updated_at")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("product_detail", kwargs={"slug": obj.slug})


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Category.objects.filter(is_active=True).only("slug")

    def location(self, obj):
        return reverse("category_detail", kwargs={"slug": obj.slug})


sitemaps = {
    "static": StaticViewSitemap,
    "products": ProductSitemap,
    "categories": CategorySitemap,
}
