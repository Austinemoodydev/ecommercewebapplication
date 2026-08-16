from django.shortcuts import render

from categories.models import Category
from products.models import Product


def home(request):
    return render(request, "core/home.html", {
        "featured_products": Product.objects.filter(featured=True, is_active=True).select_related("category")[:8],
        "home_categories": Category.objects.filter(is_active=True)[:4],
    })
