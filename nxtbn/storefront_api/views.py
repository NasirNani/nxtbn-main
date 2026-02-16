from django.db.models import Avg, Count, Min, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from nxtbn.checkout.cart import add_to_cart, calculate_totals, remove_from_cart, set_quantity
from nxtbn.order.models import Order
from nxtbn.product.models import Product, ProductReview, ProductVariant
from nxtbn.product.utils import is_variant_available
from nxtbn.users.models import CustomerAddress


def _variant_payload(variant):
    return {
        "id": str(variant.id),
        "name": variant.name or "Default",
        "price": str(variant.price),
        "compare_at_price": str(variant.compare_at_price),
        "sku": variant.sku,
        "stock": variant.stock,
        "track_inventory": variant.track_inventory,
        "is_available": is_variant_available(variant),
    }


def _product_payload(product):
    variant = product.default_variant or product.variants.first()
    image_url = ""
    if variant and variant.variant_image.exists():
        image_url = variant.variant_image.first().image.url

    return {
        "id": str(product.id),
        "name": product.name,
        "summary": product.summary,
        "category": product.effective_category,
        "vendor": getattr(product.vendor, "name", ""),
        "price": str(getattr(product, "display_price", None) or (variant.price if variant else "0")),
        "rating": float(getattr(product, "average_rating", 0) or 0),
        "reviews_total": int(getattr(product, "reviews_total", 0) or 0),
        "image_url": image_url,
    }


def _address_payload(address):
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
        "is_default_shipping": address.is_default_shipping,
        "is_default_billing": address.is_default_billing,
        "is_active": address.is_active,
        "created_at": address.created_at,
    }


def _to_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@api_view(["GET"])
@permission_classes([AllowAny])
def products_api(request):
    products = Product.objects.select_related("vendor", "default_variant", "category_ref").prefetch_related(
        "variants", "variants__variant_image"
    )
    live_products = products.filter(is_live=True)
    products = live_products if live_products.exists() else products
    products = products.annotate(
        display_price=Coalesce("default_variant__price", Min("variants__price")),
        reviews_total=Count("reviews", filter=Q(reviews__status=ProductReview.STATUS_APPROVED), distinct=True),
        average_rating=Coalesce(Avg("reviews__rating", filter=Q(reviews__status=ProductReview.STATUS_APPROVED)), 0.0),
    )

    query = (request.GET.get("q", "") or "").strip()
    category = (request.GET.get("category", "") or "").strip()
    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(summary__icontains=query)
            | Q(description__icontains=query)
            | Q(category_ref__name__icontains=query)
            | Q(category__icontains=query)
            | Q(vendor__name__icontains=query)
        )
    if category:
        products = products.filter(Q(category_ref__name=category) | Q(category=category))

    sort = (request.GET.get("sort", "popular") or "popular").strip()
    if sort == "newest":
        products = products.order_by("-created_at")
    elif sort == "price_asc":
        products = products.order_by("display_price", "name")
    elif sort == "price_desc":
        products = products.order_by("-display_price", "name")
    else:
        products = products.order_by("-reviews_total", "-created_at")

    limit = max(1, min(int(request.GET.get("limit", 20)), 100))
    offset = max(0, int(request.GET.get("offset", 0)))
    sliced = products[offset : offset + limit]
    return Response(
        {
            "count": products.count(),
            "limit": limit,
            "offset": offset,
            "results": [_product_payload(product) for product in sliced],
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def product_detail_api(request, product_id):
    product = get_object_or_404(
        Product.objects.select_related("vendor", "default_variant", "category_ref").prefetch_related(
            "variants", "variants__variant_image"
        ),
        id=product_id,
    )
    payload = _product_payload(product)
    payload["description"] = product.description
    payload["variants"] = [_variant_payload(variant) for variant in product.variants.all()]
    payload["reviews"] = [
        {
            "id": str(review.id),
            "rating": review.rating,
            "comment": review.comment,
            "user": review.user.get_full_name() or review.user.username or review.user.email,
            "created_at": review.created_at,
        }
        for review in product.reviews.filter(status=ProductReview.STATUS_APPROVED).select_related("user")
    ]
    return Response(payload)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def review_create_api(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    rating = int(request.data.get("rating", 0))
    if rating < 1 or rating > 5:
        return Response({"detail": "rating must be between 1 and 5"}, status=400)

    review, _created = ProductReview.objects.update_or_create(
        product=product,
        user=request.user,
        defaults={
            "rating": rating,
            "comment": (request.data.get("comment", "") or "").strip(),
            "status": ProductReview.STATUS_APPROVED,
        },
    )
    return Response({"id": str(review.id), "rating": review.rating, "comment": review.comment})


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def cart_api(request):
    if request.method == "POST":
        action = (request.data.get("action", "") or "").strip()
        variant_id = request.data.get("variant_id")
        quantity = int(request.data.get("quantity", 1))
        if not variant_id:
            return Response({"detail": "variant_id is required"}, status=400)

        variant = get_object_or_404(ProductVariant, id=variant_id)
        if action == "remove":
            remove_from_cart(request, variant.id)
        elif action == "set":
            set_quantity(request, variant.id, quantity)
        else:
            add_to_cart(request, variant.id, quantity=quantity)
        return Response(calculate_totals(request))

    return Response(calculate_totals(request))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def orders_api(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items").order_by("-created_at")
    return Response(
        {
            "count": orders.count(),
            "results": [
                {
                    "id": str(order.id),
                    "status": order.status,
                    "total": str(order.total),
                    "created_at": order.created_at,
                    "items_count": order.items.count(),
                }
                for order in orders
            ],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def order_detail_api(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related("items"), id=order_id, user=request.user)
    return Response(
        {
            "id": str(order.id),
            "status": order.status,
            "payment_method": order.payment_method,
            "subtotal": str(order.subtotal),
            "discount": str(order.discount),
            "tax": str(order.tax),
            "shipping": str(order.shipping),
            "total": str(order.total),
            "items": [
                {
                    "id": str(item.id),
                    "name": item.product_name,
                    "sku": item.sku,
                    "unit_price": str(item.unit_price),
                    "quantity": item.quantity,
                    "line_total": str(item.line_total),
                }
                for item in order.items.all()
            ],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def account_summary_api(request):
    orders = Order.objects.filter(user=request.user)
    aggregate = orders.aggregate(total_spend=Coalesce(Sum("total"), 0))
    return Response(
        {
            "user": {
                "id": request.user.id,
                "username": request.user.username,
                "email": request.user.email,
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
            },
            "orders_count": orders.count(),
            "total_spend": str(aggregate["total_spend"]),
            "addresses_count": CustomerAddress.objects.filter(user=request.user, is_active=True).count(),
            "reviews_count": ProductReview.objects.filter(user=request.user).count(),
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def account_orders_api(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items").order_by("-created_at")
    return Response(
        {
            "count": orders.count(),
            "results": [
                {
                    "id": str(order.id),
                    "status": order.status,
                    "total": str(order.total),
                    "created_at": order.created_at,
                    "items_count": order.items.count(),
                    "cancellation_requested": order.cancellation_requested,
                }
                for order in orders
            ],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def account_reviews_api(request):
    reviews = ProductReview.objects.filter(user=request.user).select_related("product").order_by("-created_at")
    return Response(
        {
            "count": reviews.count(),
            "results": [
                {
                    "id": str(review.id),
                    "product": {
                        "id": str(review.product_id),
                        "name": review.product.name,
                    },
                    "rating": review.rating,
                    "comment": review.comment,
                    "status": review.status,
                    "created_at": review.created_at,
                }
                for review in reviews
            ],
        }
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def account_addresses_api(request):
    if request.method == "GET":
        addresses = CustomerAddress.objects.filter(user=request.user, is_active=True).order_by(
            "-is_default_shipping", "-created_at"
        )
        return Response({"count": addresses.count(), "results": [_address_payload(address) for address in addresses]})

    payload = request.data
    required = ("full_name", "city", "district", "address_line1")
    missing = [field for field in required if not (payload.get(field) or "").strip()]
    if missing:
        return Response({"detail": f"missing fields: {', '.join(missing)}"}, status=400)

    address = CustomerAddress.objects.create(
        user=request.user,
        label=(payload.get("label", "") or "").strip()[:50],
        full_name=(payload.get("full_name", "") or "").strip()[:120],
        phone=(payload.get("phone", "") or "").strip()[:30],
        city=(payload.get("city", "") or "").strip()[:100],
        district=(payload.get("district", "") or "").strip()[:100],
        postal_code=(payload.get("postal_code", "") or "").strip()[:20],
        address_line1=(payload.get("address_line1", "") or "").strip()[:180],
        address_line2=(payload.get("address_line2", "") or "").strip()[:180],
        country=(payload.get("country", "Turkiye") or "Turkiye").strip()[:100],
        is_default_shipping=_to_bool(payload.get("is_default_shipping"), False),
        is_default_billing=_to_bool(payload.get("is_default_billing"), False),
    )
    if address.is_default_shipping:
        CustomerAddress.objects.filter(user=request.user).exclude(id=address.id).update(is_default_shipping=False)
    if address.is_default_billing:
        CustomerAddress.objects.filter(user=request.user).exclude(id=address.id).update(is_default_billing=False)
    return Response(_address_payload(address), status=201)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def account_address_detail_api(request, address_id):
    address = get_object_or_404(CustomerAddress.objects.filter(user=request.user, is_active=True), id=address_id)

    if request.method == "DELETE":
        address.is_active = False
        address.is_default_shipping = False
        address.is_default_billing = False
        address.save(update_fields=["is_active", "is_default_shipping", "is_default_billing"])
        return Response(status=204)

    payload = request.data
    fields = [
        "label",
        "full_name",
        "phone",
        "city",
        "district",
        "postal_code",
        "address_line1",
        "address_line2",
        "country",
        "is_default_shipping",
        "is_default_billing",
    ]
    updated_fields = []
    for field in fields:
        if field not in payload:
            continue
        if field in {"is_default_shipping", "is_default_billing"}:
            setattr(address, field, _to_bool(payload.get(field), False))
        else:
            setattr(address, field, payload.get(field))
        updated_fields.append(field)

    if "is_default_shipping" in updated_fields and address.is_default_shipping:
        CustomerAddress.objects.filter(user=request.user).exclude(id=address.id).update(is_default_shipping=False)
    if "is_default_billing" in updated_fields and address.is_default_billing:
        CustomerAddress.objects.filter(user=request.user).exclude(id=address.id).update(is_default_billing=False)

    if updated_fields:
        updated_fields.append("last_modified")
        address.save(update_fields=updated_fields)
    return Response(_address_payload(address))
