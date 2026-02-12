import logging

from allauth.account.models import EmailAddress
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from nxtbn.order.models import Order
from nxtbn.product.models import ProductReview
from nxtbn.users.forms import CustomerAddressForm, CustomerProfileForm
from nxtbn.users.models import CustomerAddress

logger = logging.getLogger(__name__)

ORDER_STATUS_FILTERS = {
    Order.STATUS_PENDING,
    Order.STATUS_PAID,
    Order.STATUS_PROCESSING,
    Order.STATUS_SHIPPED,
    Order.STATUS_DELIVERED,
    Order.STATUS_CANCELLED,
    Order.STATUS_REFUNDED,
}


def _panel_context(request, section):
    return {
        "account_nav_section": section,
        "account_sidebar": [
            {"key": "dashboard", "url_name": "account_dashboard", "label_tr": "Genel Bakis", "label_en": "Overview"},
            {"key": "addresses", "url_name": "account_addresses", "label_tr": "Adreslerim", "label_en": "My Addresses"},
            {"key": "orders", "url_name": "account_orders", "label_tr": "Siparislerim", "label_en": "My Orders"},
            {"key": "reviews", "url_name": "account_reviews", "label_tr": "Yorumlarim", "label_en": "My Reviews"},
            {"key": "security", "url_name": "account_security", "label_tr": "Guvenlik", "label_en": "Security"},
        ],
    }


def _set_default_flags_for_user(address):
    if address.is_default_shipping:
        CustomerAddress.objects.filter(user=address.user).exclude(id=address.id).update(is_default_shipping=False)
    if address.is_default_billing:
        CustomerAddress.objects.filter(user=address.user).exclude(id=address.id).update(is_default_billing=False)


def _address_for_user(user, address_id):
    return get_object_or_404(CustomerAddress.objects.filter(user=user, is_active=True), id=address_id)


@login_required
def account_dashboard(request):
    orders = (
        Order.objects.filter(user=request.user)
        .annotate(items_count=Count("items"))
        .order_by("-created_at")
    )
    totals = orders.aggregate(order_total=Sum("total"))
    recent_orders = list(orders[:5])

    if request.method == "POST":
        form = CustomerProfileForm(request.POST, initial={
            "username": request.user.username,
            "email": request.user.email,
        })
        if form.is_valid():
            form.save(request.user)
            messages.success(request, "Profil bilgileriniz guncellendi.")
            return redirect("account_dashboard")
    else:
        form = CustomerProfileForm(initial={
            "username": request.user.username,
            "email": request.user.email,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
        })

    context = {
        **_panel_context(request, "dashboard"),
        "profile_form": form,
        "orders": recent_orders,
        "orders_count": orders.count(),
        "order_total": totals["order_total"] or 0,
    }
    return render(request, "account/panel/dashboard.html", context)


@login_required
def profile_view(request):
    return redirect("account_dashboard")


@login_required
def account_addresses(request):
    addresses = CustomerAddress.objects.filter(user=request.user, is_active=True).order_by("-is_default_shipping", "-created_at")
    context = {
        **_panel_context(request, "addresses"),
        "addresses": addresses,
    }
    return render(request, "account/panel/addresses.html", context)


@login_required
def account_address_add(request):
    if request.method == "POST":
        form = CustomerAddressForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                address = form.save(commit=False)
                address.user = request.user
                address.save()
                _set_default_flags_for_user(address)
            messages.success(request, "Adres eklendi.")
            return redirect("account_addresses")
    else:
        form = CustomerAddressForm(initial={"country": "Turkiye"})

    context = {
        **_panel_context(request, "addresses"),
        "form": form,
        "address": None,
    }
    return render(request, "account/panel/address_form.html", context)


@login_required
def account_address_edit(request, address_id):
    address = _address_for_user(request.user, address_id)
    if request.method == "POST":
        form = CustomerAddressForm(request.POST, instance=address)
        if form.is_valid():
            with transaction.atomic():
                address = form.save()
                _set_default_flags_for_user(address)
            messages.success(request, "Adres guncellendi.")
            return redirect("account_addresses")
    else:
        form = CustomerAddressForm(instance=address)

    context = {
        **_panel_context(request, "addresses"),
        "form": form,
        "address": address,
    }
    return render(request, "account/panel/address_form.html", context)


@login_required
@require_POST
def account_address_delete(request, address_id):
    address = _address_for_user(request.user, address_id)
    address.is_active = False
    address.is_default_shipping = False
    address.is_default_billing = False
    address.save(update_fields=["is_active", "is_default_shipping", "is_default_billing"])
    messages.success(request, "Adres kaldirildi.")
    return redirect("account_addresses")


@login_required
@require_POST
def account_address_default_shipping(request, address_id):
    address = _address_for_user(request.user, address_id)
    with transaction.atomic():
        CustomerAddress.objects.filter(user=request.user).update(is_default_shipping=False)
        address.is_default_shipping = True
        address.save(update_fields=["is_default_shipping"])
    messages.success(request, "Varsayilan teslimat adresi guncellendi.")
    return redirect("account_addresses")


@login_required
@require_POST
def account_address_default_billing(request, address_id):
    address = _address_for_user(request.user, address_id)
    with transaction.atomic():
        CustomerAddress.objects.filter(user=request.user).update(is_default_billing=False)
        address.is_default_billing = True
        address.save(update_fields=["is_default_billing"])
    messages.success(request, "Varsayilan fatura adresi guncellendi.")
    return redirect("account_addresses")


@login_required
def account_orders(request):
    orders = (
        Order.objects.filter(user=request.user)
        .annotate(items_count=Count("items"))
    )

    selected_status = (request.GET.get("status") or "").strip()
    selected_sort = (request.GET.get("sort") or "latest").strip()

    if selected_status in ORDER_STATUS_FILTERS:
        orders = orders.filter(status=selected_status)
    else:
        selected_status = ""

    if selected_sort == "oldest":
        orders = orders.order_by("created_at")
    elif selected_sort == "total_desc":
        orders = orders.order_by("-total", "-created_at")
    elif selected_sort == "total_asc":
        orders = orders.order_by("total", "-created_at")
    else:
        selected_sort = "latest"
        orders = orders.order_by("-created_at")

    paginator = Paginator(orders, 10)
    page_obj = paginator.get_page(request.GET.get("page") or 1)
    context = {
        **_panel_context(request, "orders"),
        "page_obj": page_obj,
        "orders": page_obj.object_list,
        "selected_status": selected_status,
        "selected_sort": selected_sort,
        "status_values": sorted(ORDER_STATUS_FILTERS),
    }
    return render(request, "account/panel/orders.html", context)


@login_required
def account_reviews(request):
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        review = get_object_or_404(
            ProductReview.objects.select_related("product"),
            id=request.POST.get("review_id"),
            user=request.user,
        )
        if action == "delete":
            review_id = str(review.id)
            review.delete()
            logger.info("customer_review_deleted user_id=%s review_id=%s", request.user.id, review_id)
            messages.success(request, "Yorum silindi.")
            return redirect("account_reviews")

        if action == "update":
            rating_raw = (request.POST.get("rating") or "").strip()
            comment = (request.POST.get("comment") or "").strip()
            try:
                rating = int(rating_raw)
            except (TypeError, ValueError):
                rating = 0
            if rating < 1 or rating > 5:
                messages.error(request, "Puan 1 ile 5 arasinda olmali.")
                return redirect("account_reviews")
            review.rating = rating
            review.comment = comment
            review.save(update_fields=["rating", "comment", "last_modified"])
            logger.info("customer_review_updated user_id=%s review_id=%s", request.user.id, review.id)
            messages.success(request, "Yorum guncellendi.")
            return redirect("account_reviews")

    reviews = ProductReview.objects.filter(user=request.user).select_related("product").order_by("-created_at")
    paginator = Paginator(reviews, 10)
    page_obj = paginator.get_page(request.GET.get("page") or 1)
    context = {
        **_panel_context(request, "reviews"),
        "page_obj": page_obj,
        "reviews": page_obj.object_list,
    }
    return render(request, "account/panel/reviews.html", context)


@login_required
def account_security(request):
    email_addresses = EmailAddress.objects.filter(user=request.user).order_by("-verified", "-primary", "-id")
    primary_email = email_addresses.filter(primary=True).first()
    context = {
        **_panel_context(request, "security"),
        "email_addresses": email_addresses,
        "primary_email": primary_email,
    }
    return render(request, "account/panel/security.html", context)
