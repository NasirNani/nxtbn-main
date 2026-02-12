from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from nxtbn.gift_card.models import GiftCardTransaction
from nxtbn.invoice.models import Invoice
from nxtbn.order.models import Order, OrderItem
from nxtbn.payment.models import PaymentTransaction
from nxtbn.product.models import ProductVariant
from nxtbn.product.utils import is_variant_available
from nxtbn.users.models import CustomerAddress

from .cart import (
    add_to_cart,
    calculate_totals,
    clear_cart,
    remove_from_cart,
    set_gift_card_code,
    set_promo_code,
    set_quantity,
)
from .forms import CheckoutForm


def _generate_invoice_number(order):
    base = f"INV-{timezone.now():%Y%m%d}-{str(order.id).split('-')[0].upper()}"
    number = base
    suffix = 1
    while Invoice.objects.filter(number=number).exists():
        suffix += 1
        number = f"{base}-{suffix}"
    return number


def _serialize_address(address):
    return {
        "id": str(address.id),
        "label": address.label,
        "full_name": address.full_name,
        "phone": address.phone,
        "city": address.city,
        "district": address.district,
        "postal_code": address.postal_code,
        "address_line1": address.address_line1,
        "address_line2": address.address_line2,
        "country": address.country,
    }


def _resolve_checkout_snapshot(form, selected_address):
    district = form.cleaned_data["district"]
    if selected_address:
        return {
            "full_name": selected_address.full_name,
            "phone": selected_address.phone,
            "address_line1": selected_address.address_line1,
            "address_line2": selected_address.address_line2,
            "city": selected_address.city,
            "state": selected_address.district,
            "postal_code": selected_address.postal_code,
            "country": selected_address.country,
        }
    return {
        "full_name": form.cleaned_data["full_name"],
        "phone": form.cleaned_data["phone"],
        "address_line1": form.cleaned_data["address_line1"],
        "address_line2": form.cleaned_data["address_line2"],
        "city": form.cleaned_data["city"],
        "state": form.cleaned_data["state"] or district,
        "postal_code": form.cleaned_data["postal_code"],
        "country": form.cleaned_data["country"],
    }


def _save_address_from_checkout(user, form):
    if not form.cleaned_data.get("save_address"):
        return None

    cleaned = form.cleaned_data
    has_default_shipping = CustomerAddress.objects.filter(user=user, is_active=True, is_default_shipping=True).exists()
    has_default_billing = CustomerAddress.objects.filter(user=user, is_active=True, is_default_billing=True).exists()

    address, _created = CustomerAddress.objects.get_or_create(
        user=user,
        full_name=cleaned["full_name"],
        phone=cleaned["phone"],
        city=cleaned["city"],
        district=cleaned["district"],
        postal_code=cleaned["postal_code"],
        address_line1=cleaned["address_line1"],
        address_line2=cleaned["address_line2"],
        country=cleaned["country"],
        defaults={
            "label": "Checkout",
            "is_default_shipping": not has_default_shipping,
            "is_default_billing": not has_default_billing,
        },
    )
    return address


def cart_view(request):
    if request.method == "POST":
        action = request.POST.get("action", "").strip()
        promo = request.POST.get("promo_code", "")
        gift_card = request.POST.get("gift_card_code", "")

        if action == "apply_coupon":
            set_promo_code(request, promo)
            totals = calculate_totals(request)
            if totals["coupon_error"]:
                messages.error(request, totals["coupon_error"])
            elif totals["coupon"]:
                messages.success(request, "Kupon uygulandi.")
        elif action == "remove_coupon":
            set_promo_code(request, "")
            messages.success(request, "Kupon kaldirildi.")
        elif action == "apply_gift_card":
            set_gift_card_code(request, gift_card)
            totals = calculate_totals(request)
            if totals["gift_card_error"]:
                messages.error(request, totals["gift_card_error"])
            elif totals["gift_card"]:
                messages.success(request, "Hediye karti uygulandi.")
        elif action == "remove_gift_card":
            set_gift_card_code(request, "")
            messages.success(request, "Hediye karti kaldirildi.")
        return redirect("cart")

    totals = calculate_totals(request)
    return render(request, "store/cart.html", totals)


@require_POST
def cart_add(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    quantity = max(1, int(request.POST.get("quantity", "1")))
    if not is_variant_available(variant, quantity):
        messages.error(request, "Secilen varyant stokta yok.")
        return redirect(request.POST.get("next") or reverse("cart"))

    add_to_cart(request, variant.id, quantity=quantity)
    messages.success(request, f"Added {variant.product.name} to cart.")
    return redirect(request.POST.get("next") or reverse("cart"))


@require_POST
def cart_update(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    quantity = max(0, int(request.POST.get("quantity", "1")))
    if quantity > 0 and not is_variant_available(variant, quantity):
        messages.error(request, "Stok miktarini astiniz.")
        return redirect("cart")

    set_quantity(request, variant_id, quantity)
    return redirect("cart")


@require_POST
def cart_remove(request, variant_id):
    remove_from_cart(request, variant_id)
    return redirect("cart")


def checkout_view(request):
    if not request.user.is_authenticated:
        login_url = f"{reverse('account_login')}?next={request.path}"
        messages.info(request, "Odeme icin giris yapmalisiniz.")
        return redirect(login_url)

    totals = calculate_totals(request)
    if not totals["items"]:
        messages.error(request, "Your cart is empty.")
        return redirect("products_list")

    saved_addresses = list(
        CustomerAddress.objects.filter(user=request.user, is_active=True).order_by("-is_default_shipping", "-created_at")
    )
    default_shipping = next((addr for addr in saved_addresses if addr.is_default_shipping), None)

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            selected_address = None
            if form.cleaned_data.get("use_saved_address") and form.cleaned_data.get("address_id"):
                selected_address = get_object_or_404(
                    CustomerAddress.objects.filter(user=request.user, is_active=True),
                    id=form.cleaned_data["address_id"],
                )

            for item in totals["items"]:
                if not is_variant_available(item["variant"], item["quantity"]):
                    messages.error(request, f"{item['product'].name} stokta kalmadi.")
                    return redirect("cart")

            with transaction.atomic():
                snapshot = _resolve_checkout_snapshot(form, selected_address)
                order = Order.objects.create(
                    user=request.user,
                    full_name=snapshot["full_name"],
                    email=form.cleaned_data["email"],
                    phone=snapshot["phone"],
                    address_line1=snapshot["address_line1"],
                    address_line2=snapshot["address_line2"],
                    city=snapshot["city"],
                    state=snapshot["state"],
                    postal_code=snapshot["postal_code"],
                    country=snapshot["country"],
                    payment_method=form.cleaned_data["payment_method"],
                    notes=form.cleaned_data["notes"],
                    subtotal=totals["subtotal"],
                    discount=totals["discount"] + totals.get("gift_card_applied", 0),
                    tax=totals["tax"],
                    shipping=totals["shipping"],
                    total=totals["total"],
                    coupon_code=totals["promo_code"],
                    gift_card_code=totals.get("gift_card_code", ""),
                )
                if not selected_address:
                    _save_address_from_checkout(request.user, form)

                order.status_events.create(
                    status=Order.STATUS_PENDING,
                    note="Order created",
                    changed_by=request.user,
                )

                for item in totals["items"]:
                    variant = item["variant"]
                    OrderItem.objects.create(
                        order=order,
                        product=item["product"],
                        variant=variant,
                        product_name=item["product"].name,
                        sku=variant.sku or "",
                        unit_price=item["price_per_unit"],
                        quantity=item["quantity"],
                        line_total=item["subtotal"],
                    )

                    if variant.track_inventory:
                        ProductVariant.objects.filter(id=variant.id, stock__gte=item["quantity"]).update(
                            stock=F("stock") - item["quantity"]
                        )

                if totals["coupon"]:
                    totals["coupon"].used_count = F("used_count") + 1
                    totals["coupon"].save(update_fields=["used_count"])

                if totals.get("gift_card") and totals.get("gift_card_applied", 0) > 0:
                    gift_card = totals["gift_card"]
                    gift_card.balance = F("balance") - totals["gift_card_applied"]
                    gift_card.save(update_fields=["balance"])
                    GiftCardTransaction.objects.create(
                        gift_card=gift_card,
                        order=order,
                        transaction_type=GiftCardTransaction.TYPE_REDEEM,
                        amount=totals["gift_card_applied"],
                        note="Checkout redemption",
                    )

                Invoice.objects.create(
                    order=order,
                    number=_generate_invoice_number(order),
                    status=Invoice.STATUS_ISSUED,
                )

                if form.cleaned_data["payment_method"] == "paytr":
                    transaction_obj = PaymentTransaction.objects.create(
                        provider="paytr",
                        order=order,
                        amount=order.total,
                        currency="TRY",
                    )
                    clear_cart(request)
                    messages.info(request, "Odeme sayfasina yonlendiriliyorsunuz.")
                    return redirect("payment_start", transaction_id=transaction_obj.id)

                order.status = Order.STATUS_PROCESSING
                order.save(update_fields=["status"])
                order.status_events.create(
                    status=Order.STATUS_PROCESSING,
                    note="Order moved to processing",
                    changed_by=request.user,
                )

            clear_cart(request)
            messages.success(request, "Siparis olusturuldu.")
            return redirect("order_success", order_id=order.id)
    else:
        default_initial = {}
        if default_shipping:
            default_initial.update(
                {
                    "address_id": default_shipping.id,
                    "use_saved_address": True,
                    "full_name": default_shipping.full_name,
                    "phone": default_shipping.phone,
                    "address_line1": default_shipping.address_line1,
                    "address_line2": default_shipping.address_line2,
                    "city": default_shipping.city,
                    "district": default_shipping.district,
                    "state": default_shipping.district,
                    "postal_code": default_shipping.postal_code,
                    "country": default_shipping.country,
                }
            )
        initial = {
            **default_initial,
            "email": request.user.email,
        }
        if not initial.get("full_name"):
            initial["full_name"] = request.user.get_full_name()
        if not initial.get("country"):
            initial["country"] = "Turkiye"
        form = CheckoutForm(initial=initial)

    context = {
        "form": form,
        "saved_addresses": saved_addresses,
        "saved_addresses_json": [_serialize_address(address) for address in saved_addresses],
        **totals,
    }
    return render(request, "store/checkout.html", context)
