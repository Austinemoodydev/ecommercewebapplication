from django.db.models import Q
from django.db.models import Prefetch
from products.models import Product, ProductVariant


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
            "images",
            Prefetch(
                "variants",
                queryset=ProductVariant.objects.filter(
                    is_active=True,
                ).prefetch_related(
                    "option_values__option",
                ).order_by("id"),
                to_attr="available_variants",
            ),
            "options__values",
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
