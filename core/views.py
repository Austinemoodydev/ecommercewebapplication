from django.shortcuts import render

from categories.models import Category
from products.models import Product


def home(request):
    return render(request, "core/home.html", {
        "featured_products": Product.objects.filter(featured=True, is_active=True).select_related("category")[:8],
        "home_categories": Category.objects.filter(is_active=True)[:4],
    })


def legal_page(request, page):
    templates = {
        "terms": "core/legal/terms.html",
        "privacy": "core/legal/privacy.html",
        "delivery": "core/legal/delivery.html",
        "refund": "core/legal/refund.html",
        "cookies": "core/legal/cookies.html",
    }
    return render(request, templates[page])
