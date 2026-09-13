from django.core.paginator import Paginator
from django.db.models import F
from django.shortcuts import render

from categories.models import Category
from .filters import ProductFilter
from .models import Brand, Product
from .services.product_service import ProductService
from .services.search_service import SearchService


def shop(request):
    products = ProductFilter.apply(SearchService.search_products(request.GET.get("search")), request)
    page_obj = Paginator(products, 12).get_page(request.GET.get("page"))
    return render(request, "products/shop.html", {
        "page_obj": page_obj, "categories": Category.objects.filter(is_active=True),
        "brands": Brand.objects.all(), "selected_sort": request.GET.get("sort"),
        "selected_category": request.GET.get("category"), "selected_brand": request.GET.get("brand"),
        "search": request.GET.get("search"),
    })


def offers(request):
    products = Product.objects.filter(
        is_active=True, discount_price__isnull=False, discount_price__lt=F("price")
    ).select_related("category", "brand").order_by("-updated_at")
    page_obj = Paginator(products, 12).get_page(request.GET.get("page"))
    return render(request, "products/offers.html", {"page_obj": page_obj})


def product_detail(request, slug):
    product = ProductService.get_product(slug)
    related_products = Product.objects.select_related("category", "brand").filter(
        category=product.category, is_active=True
    ).exclude(id=product.id)[:4]
    return render(request, "products/product_detail.html", {
        "product": product, "related_products": related_products,
    })
