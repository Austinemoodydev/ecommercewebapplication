from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from products.models import Product
from orders.models import OrderItem
from .models import Review


@login_required
@require_POST
def submit_review(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    eligible_purchase = OrderItem.objects.filter(
        order__user=request.user,
        order__payment_status__in=[
            "paid",
            "partially_refunded",
        ],
        product=product,
    ).exists()

    if not eligible_purchase:

        messages.error(
            request,
            (
                "Only customers who purchased "
                "this product can leave a review."
            ),
        )

        return redirect(
            "product_detail",
            slug=product.slug,
        )

    rating = request.POST.get("rating")
    comment = request.POST.get("comment", "").strip()

    if not rating or not rating.isdigit() or not (1 <= int(rating) <= 5):
        messages.error(request, "Please select a valid rating.")
        return redirect("product_detail", slug=product.slug)

    Review.objects.update_or_create(
        product=product,
        user=request.user,
        defaults={
            "rating": int(rating),
            "comment": comment,
            "verified_purchase": True,
        },
    )

    messages.success(request, "Your review has been saved.")

    return redirect("product_detail", slug=product.slug)
