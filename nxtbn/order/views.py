from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from nxtbn.checkout.cart import add_to_cart
from nxtbn.invoice.models import Invoice
from .models import Order


def _order_for_request(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("user").prefetch_related("items", "status_events"),
        id=order_id,
    )
    if request.user.is_staff or (request.user.is_authenticated and order.user_id == request.user.id):
        return order
    raise Http404("Order not found")


def _order_context(order):
    try:
        invoice = order.invoice
    except Invoice.DoesNotExist:
        invoice = None
    return {"order": order, "invoice": invoice}


@login_required
def order_success(request, order_id):
    order = _order_for_request(request, order_id)
    return render(request, "store/order_success.html", _order_context(order))


@login_required
def order_tracking(request, order_id):
    order = _order_for_request(request, order_id)
    return render(request, "store/order_tracking.html", _order_context(order))


@login_required
def order_detail(request, order_id):
    order = _order_for_request(request, order_id)
    return render(request, "store/order_detail.html", _order_context(order))


@login_required
@require_POST
def order_cancel_request(request, order_id):
    order = _order_for_request(request, order_id)
    if order.status in {Order.STATUS_SHIPPED, Order.STATUS_DELIVERED, Order.STATUS_REFUNDED}:
        messages.error(request, "Bu siparis icin iptal talebi olusturulamaz.")
        return redirect("order_detail", order_id=order.id)

    order.cancellation_requested = True
    order.cancellation_reason = (request.POST.get("reason", "") or "").strip()[:255]
    order.save(update_fields=["cancellation_requested", "cancellation_reason"])
    order.status_events.create(
        status=order.status,
        note=f"Cancellation requested: {order.cancellation_reason or 'No reason'}",
        changed_by=request.user,
    )
    messages.success(request, "Iptal talebi alindi.")
    return redirect("order_detail", order_id=order.id)


@login_required
@require_POST
def reorder(request, order_id):
    order = _order_for_request(request, order_id)
    for item in order.items.select_related("variant").all():
        if item.variant_id:
            add_to_cart(request, item.variant_id, quantity=item.quantity)
    messages.success(request, "Siparisteki urunler tekrar sepete eklendi.")
    return redirect("cart")
