from django.db.models import Q
from products.models import Product


class ProductSelector:

    @staticmethod
    def get_active_products():
        return Product.objects.select_related(
            "category",
            "brand"
        ).filter(
            is_active=True
        )

    @staticmethod
    def featured():
        return Product.objects.select_related(
            "category",
            "brand"
        ).filter(
            featured=True,
            is_active=True
        )

    @staticmethod
    def by_slug(slug):
        return Product.objects.select_related(
            "category",
            "brand"
        ).prefetch_related(
            "images"
        ).get(
            slug=slug,
            is_active=True
        )

    @staticmethod
    def search(query):
        return Product.objects.select_related(
            "category",
            "brand"
        ).filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(sku__icontains=query),
            is_active=True
        )
