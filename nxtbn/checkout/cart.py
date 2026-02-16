from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from nxtbn.discount.models import Coupon
from nxtbn.gift_card.models import GiftCard
from nxtbn.product.models import ProductVariant
from nxtbn.product.utils import is_variant_available
from nxtbn.tax.models import TaxRule

CART_SESSION_KEY = "nxtbn_cart"
PROMO_SESSION_KEY = "nxtbn_promo"
GIFT_CARD_SESSION_KEY = "nxtbn_gift_card"

TWOPLACES = Decimal("0.01")


def _as_money(value):
    return Decimal(value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _cart_dict(request):
    cart = request.session.get(CART_SESSION_KEY, {})
    if not isinstance(cart, dict):
        cart = {}
    return cart


def _save_cart(request, cart):
    request.session[CART_SESSION_KEY] = cart
    request.session.modified = True


def add_to_cart(request, variant_id, quantity=1):
    cart = _cart_dict(request)
    key = str(variant_id)
    current = int(cart.get(key, 0))
    cart[key] = max(1, current + int(quantity))
    _save_cart(request, cart)


def set_quantity(request, variant_id, quantity):
    cart = _cart_dict(request)
    key = str(variant_id)
    qty = int(quantity)
    if qty <= 0:
        cart.pop(key, None)
    else:
        cart[key] = qty
    _save_cart(request, cart)


def remove_from_cart(request, variant_id):
    cart = _cart_dict(request)
    cart.pop(str(variant_id), None)
    _save_cart(request, cart)


def clear_cart(request):
    request.session[CART_SESSION_KEY] = {}
    request.session.pop(PROMO_SESSION_KEY, None)
    request.session.pop(GIFT_CARD_SESSION_KEY, None)
    request.session.modified = True


def set_promo_code(request, promo_code):
    request.session[PROMO_SESSION_KEY] = (promo_code or "").strip().upper()
    request.session.modified = True


def get_promo_code(request):
    return request.session.get(PROMO_SESSION_KEY, "")


def set_gift_card_code(request, code):
    request.session[GIFT_CARD_SESSION_KEY] = (code or "").strip().upper()
    request.session.modified = True


def get_gift_card_code(request):
    return request.session.get(GIFT_CARD_SESSION_KEY, "")


def get_cart_items(request):
    cart = _cart_dict(request)
    if not cart:
        return []

    variants = ProductVariant.objects.select_related("product").filter(id__in=cart.keys())
    variant_map = {str(v.id): v for v in variants}
    items = []
    normalized_cart = {}

    for variant_id, qty in cart.items():
        variant = variant_map.get(variant_id)
        if not variant:
            continue

        quantity = max(1, int(qty))
        if variant.track_inventory:
            if variant.stock <= 0:
                continue
            quantity = min(quantity, variant.stock)
        elif not is_variant_available(variant, quantity=quantity):
            continue

        normalized_cart[variant_id] = quantity
        unit_price = _as_money(variant.price)
        subtotal = _as_money(unit_price * quantity)
        items.append(
            {
                "variant": variant,
                "product": variant.product,
                "quantity": quantity,
                "price_per_unit": unit_price,
                "subtotal": subtotal,
            }
        )

    if normalized_cart != cart:
        _save_cart(request, normalized_cart)

    return items


def calculate_totals(request):
    items = get_cart_items(request)
    subtotal = _as_money(sum(item["subtotal"] for item in items) if items else Decimal("0.00"))

    promo_code = get_promo_code(request)
    discount = Decimal("0.00")
    coupon = None
    coupon_error = ""

    if promo_code:
        now = timezone.now()
        coupon = Coupon.objects.filter(code=promo_code, is_active=True).first()
        if coupon is None:
            coupon_error = "Kupon kodu bulunamadi."
        elif now < coupon.starts_at:
            coupon_error = "Kupon henuz aktif degil."
        elif not coupon.is_usable(subtotal):
            coupon_error = "Kupon su an kullanilamaz."
        else:
            if coupon.discount_type == Coupon.TYPE_PERCENT:
                discount = subtotal * (coupon.discount_value / Decimal("100"))
            else:
                discount = coupon.discount_value

            if coupon.max_discount:
                discount = min(discount, coupon.max_discount)
            discount = _as_money(min(discount, subtotal))

    taxable_amount = _as_money(max(Decimal("0.00"), subtotal - discount))

    active_rules = TaxRule.objects.filter(is_active=True).order_by("priority", "-created_at")
    default_rule = active_rules.filter(category__isnull=True).first() or active_rules.filter(category="").first()
    category_rule_map = {
        (rule.category or "").strip().lower(): rule
        for rule in active_rules
        if (rule.category or "").strip()
    }

    tax = Decimal("0.00")
    tax_breakdown = []
    for item in items:
        category_name = (item["product"].effective_category or "").strip()
        category = category_name.lower()
        rule = category_rule_map.get(category) or default_rule
        if not rule:
            continue

        raw_rate = Decimal(rule.rate)
        normalized_rate = raw_rate / Decimal("100") if raw_rate > Decimal("1") else raw_rate
        discount_share = Decimal("0.00")
        if subtotal > 0:
            discount_share = discount * (item["subtotal"] / subtotal)
        taxable_line = max(Decimal("0.00"), item["subtotal"] - discount_share)
        line_tax = taxable_line * normalized_rate
        tax += line_tax
        tax_breakdown.append(
            {
                "label": rule.name,
                "category": category_name or "-",
                "rate": normalized_rate,
                "amount": _as_money(line_tax),
            }
        )

    tax = _as_money(tax)
    shipping = Decimal("0.00") if taxable_amount >= Decimal("500.00") else Decimal("39.90")
    shipping = _as_money(shipping)
    pre_gift_total = _as_money(taxable_amount + tax + shipping)

    gift_card_code = get_gift_card_code(request)
    gift_card = None
    gift_card_applied = Decimal("0.00")
    gift_card_error = ""
    if gift_card_code:
        gift_card = GiftCard.objects.filter(code=gift_card_code, is_active=True, currency="TRY").first()
        if gift_card is None:
            gift_card_error = "Hediye karti bulunamadi."
        elif not gift_card.is_usable():
            gift_card_error = "Hediye karti kullanilamaz."
        else:
            gift_card_applied = _as_money(min(gift_card.balance, pre_gift_total))

    total = _as_money(max(Decimal("0.00"), pre_gift_total - gift_card_applied))

    return {
        "items": items,
        "subtotal": subtotal,
        "discount": discount,
        "coupon": coupon,
        "coupon_error": coupon_error,
        "tax": tax,
        "tax_breakdown": tax_breakdown,
        "shipping": shipping,
        "pre_gift_total": pre_gift_total,
        "gift_card": gift_card,
        "gift_card_code": gift_card_code,
        "gift_card_applied": gift_card_applied,
        "gift_card_error": gift_card_error,
        "total": total,
        "promo_code": promo_code,
    }
