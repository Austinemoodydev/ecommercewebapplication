from django.core.paginator import Paginator
from django.db.models import Count, Exists, F, OuterRef, Q
from django.shortcuts import render

from categories.models import Category
from orders.models import OrderItem
from .filters import ProductFilter
from .models import Brand, Product, ProductVariant
from .services.product_service import ProductService
from .services.search_service import SearchService


def shop(request):
    selected_category_slugs = [value for value in request.GET.getlist("category") if value]
    selected_brand_slugs = [value for value in request.GET.getlist("brand") if value]
    products = ProductFilter.apply(SearchService.search_products(request.GET.get("search")), request)
    products = products.annotate(
        has_active_variants=Exists(
            ProductVariant.objects.filter(
                product_id=OuterRef("pk"),
                is_active=True,
            )
        )
    )
    page_obj = Paginator(products, 12).get_page(request.GET.get("page"))
    categories = Category.objects.filter(is_active=True).annotate(
        product_count=Count("products", filter=Q(products__is_active=True), distinct=True)
    ).order_by("-product_count", "name")
    brands = Brand.objects.filter(is_active=True).annotate(
        product_count=Count("products", filter=Q(products__is_active=True), distinct=True)
    ).filter(product_count__gt=0).order_by("-product_count", "name")
    return render(request, "products/shop.html", {
        "page_obj": page_obj, "categories": categories,
        "brands": brands, "selected_sort": request.GET.get("sort"),
        "selected_category_slugs": selected_category_slugs,
        "selected_brand_slugs": selected_brand_slugs,
        "selected_categories": categories.filter(slug__in=selected_category_slugs),
        "selected_brands": brands.filter(slug__in=selected_brand_slugs),
        "selected_filter_count": len(selected_category_slugs) + len(selected_brand_slugs),
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

    related_products = (
        Product.objects
        .select_related(
            "category",
            "brand",
        )
        .filter(
            category=product.category,
            is_active=True,
        )
        .exclude(id=product.id)[:4]
    )

    can_review = False

    if request.user.is_authenticated:

        can_review = OrderItem.objects.filter(
            order__user=request.user,
            order__payment_status__in=[
                "paid",
                "partially_refunded",
            ],
            product=product,
        ).exists()

    return render(
        request,
        "products/product_detail.html",
        {
            "product": product,
            "structured_options": list(product.options.all()),
            "related_products": related_products,
            "can_review": can_review,
        },
    )
