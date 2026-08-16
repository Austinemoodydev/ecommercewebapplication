from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from orders.models import Order
from products.models import Product


@login_required
def dashboard(request):
    return render(request, "dashboard/dashboard.html")


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "dashboard/order_history.html", {"orders": orders})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, "dashboard/order_detail.html", {"order": order, "items": order.items.select_related("product")})


@staff_member_required
def admin_analytics(request):
    today = timezone.localdate()
    paid_orders = Order.objects.filter(payment_status="paid")
    daily_orders = Order.objects.filter(created_at__date=today)
    context = {
        "today_orders": daily_orders.count(),
        "today_revenue": daily_orders.filter(payment_status="paid").aggregate(total=Sum("total_amount"))["total"] or 0,
        "week_revenue": paid_orders.filter(created_at__date__gte=today - timedelta(days=6)).aggregate(total=Sum("total_amount"))["total"] or 0,
        "pending_orders": Order.objects.filter(status__in=["pending", "confirmed", "processing", "shipped"]).count(),
        "status_counts": Order.objects.values("status").annotate(total=Count("id")).order_by("status"),
        "recent_orders": Order.objects.select_related("user").order_by("-created_at")[:8],
        "low_stock": Product.objects.filter(stock__lt=5).order_by("stock", "name")[:10],
    }
    return render(request, "dashboard/admin_analytics.html", context)
