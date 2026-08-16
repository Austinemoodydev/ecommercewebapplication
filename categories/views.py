from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from .models import Category


def category_list(request):
    categories = Category.objects.filter(is_active=True).annotate(
        product_count=Count("products", filter=Q(products__is_active=True))
    )
    return render(request, "categories/category_list.html", {"categories": categories})


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    products = category.products.filter(is_active=True).select_related("brand")
    page_obj = Paginator(products, 12).get_page(request.GET.get("page"))
    return render(request, "categories/category_detail.html", {"category": category, "page_obj": page_obj})
