
# Create your views here.
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from products.models import Product
from wishlist.selectors.wishlist_selector import WishlistSelector
from wishlist.services.wishlist_service import WishlistService


@login_required
def wishlist_page(request):

    items = WishlistSelector.user_items(
        request.user
    )

    return render(
        request,
        "wishlist/wishlist.html",
        {
            "items": items
        },
    )


@login_required
def toggle_wishlist(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id
    )

    added = WishlistService.toggle(
        request.user,
        product
    )

    count = WishlistSelector.user_items(
        request.user
    ).count()

    return JsonResponse({
        "added": added,
        "count": count
    })