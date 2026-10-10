from django.shortcuts import render
from django.db.models import Q
from django.utils import timezone

from categories.models import Category
from products.models import Product
from .models import HomepageSlide


def home(request):
    now = timezone.now()
    return render(request, "core/home.html", {
        "featured_products": Product.objects.filter(featured=True, is_active=True).select_related("category")[:8],
        "home_categories": Category.objects.filter(is_active=True)[:4],
        "homepage_slides": HomepageSlide.objects.filter(
            is_enabled=True,
        ).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(ends_at__isnull=True) | Q(ends_at__gt=now),
        ).select_related("category", "product"),
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
