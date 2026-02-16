from datetime import timedelta
from decimal import Decimal

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.shortcuts import render
from django.utils import timezone

from nxtbn.order.models import Order
from nxtbn.product.models import Product, ProductReview, ProductVariant


@staff_member_required
def analytics_dashboard(request):
    now = timezone.now()
    start = now - timedelta(days=30)

    orders = Order.objects.all()
    products = Product.objects.all()
    reviews = ProductReview.objects.all()
    variants = ProductVariant.objects.filter(track_inventory=True)

    metrics = {
        "orders_total": orders.count(),
        "orders_pending": orders.filter(status=Order.STATUS_PENDING).count(),
        "orders_processing": orders.filter(status=Order.STATUS_PROCESSING).count(),
        "orders_paid": orders.filter(status=Order.STATUS_PAID).count(),
        "sales_30_days": orders.filter(status__in=[Order.STATUS_PAID, Order.STATUS_PROCESSING, Order.STATUS_SHIPPED, Order.STATUS_DELIVERED], created_at__gte=start).aggregate(
            total=Coalesce(Sum("total"), Value(Decimal("0.00")))
        )["total"],
        "products_total": products.count(),
        "products_live": products.filter(is_live=True).count(),
        "low_stock_count": variants.filter(stock__lte=2).count(),
        "pending_reviews": reviews.filter(status=ProductReview.STATUS_PENDING).count(),
    }

    low_stock_variants = (
        variants.select_related("product")
        .filter(stock__lte=2)
        .order_by("stock", "product__name")[:25]
    )
    order_queue = orders.filter(status__in=[Order.STATUS_PENDING, Order.STATUS_PAID, Order.STATUS_PROCESSING]).order_by("-created_at")[:25]
    review_queue = (
        reviews.filter(status=ProductReview.STATUS_PENDING)
        .select_related("product", "user")
        .order_by("-created_at")[:25]
    )

    sales_by_day = (
        orders.filter(created_at__gte=start, status__in=[Order.STATUS_PAID, Order.STATUS_PROCESSING, Order.STATUS_SHIPPED, Order.STATUS_DELIVERED])
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Coalesce(Sum("total"), Value(Decimal("0.00"))), count=Count("id"))
        .order_by("day")
    )

    context = {
        **admin.site.each_context(request),
        "title": "Operasyon Panosu",
        "metrics": metrics,
        "low_stock_variants": low_stock_variants,
        "order_queue": order_queue,
        "review_queue": review_queue,
        "sales_by_day": sales_by_day,
    }
    return render(request, "admin/dashboard_analytics.html", context)
