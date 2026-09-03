from datetime import timedelta
import csv

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from orders.models import Order, OrderItem
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
    start_date, end_date = _report_dates(request)
    paid_orders = _paid_orders(start_date, end_date)
    report_end = end_date + timedelta(days=1)
    daily_orders = Order.objects.filter(created_at__gte=start_date, created_at__lt=report_end)
    top_products = OrderItem.objects.filter(
        order__in=paid_orders,
    ).values("product_name").annotate(
        units=Sum("quantity"), revenue=Sum("subtotal")
    ).order_by("-units", "product_name")[:10]
    context = {
        "start_date": start_date,
        "end_date": end_date,
        "today_orders": daily_orders.count(),
        "today_revenue": paid_orders.aggregate(total=Sum("total_amount"))["total"] or 0,
        "week_revenue": paid_orders.aggregate(total=Sum("total_amount"))["total"] or 0,
        "report_orders": paid_orders.count(),
        "report_customers": paid_orders.values("user_id").distinct().count(),
        "pending_orders": Order.objects.filter(status__in=["pending", "confirmed", "processing", "shipped"]).count(),
        "status_counts": Order.objects.values("status").annotate(total=Count("id")).order_by("status"),
        "recent_orders": Order.objects.select_related("user").order_by("-created_at")[:8],
        "low_stock": Product.objects.filter(stock__lt=5).order_by("stock", "name")[:10],
        "top_products": top_products,
    }
    return render(request, "dashboard/admin_analytics.html", context)


def _report_dates(request):
    today = timezone.localdate()
    default_start = today - timedelta(days=29)
    try:
        start_date = timezone.datetime.strptime(request.GET.get("start", ""), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        start_date = default_start
    try:
        end_date = timezone.datetime.strptime(request.GET.get("end", ""), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        end_date = today
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    return start_date, end_date


def _paid_orders(start_date, end_date):
    return Order.objects.filter(
        payment_status="paid",
        created_at__gte=start_date,
        created_at__lt=end_date + timedelta(days=1),
    )


@staff_member_required
def admin_sales_export(request):
    start_date, end_date = _report_dates(request)
    orders = _paid_orders(start_date, end_date).select_related("user").order_by("created_at")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="sales-{start_date}-to-{end_date}.csv"'
    writer = csv.writer(response)
    writer.writerow(["Order number", "Date", "Customer", "Status", "Payment status", "Total"])
    for order in orders:
        writer.writerow([
            order.order_number,
            order.created_at.isoformat(),
            order.full_name,
            order.get_status_display(),
            order.get_payment_status_display(),
            order.total_amount,
        ])
    return response
