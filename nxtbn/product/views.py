from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Min, Q, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render

from .models import Product, ProductReview, ProductVariant
from .utils import is_variant_available
from nxtbn.core.enum_helper import StockStatus


def products_list(request):
    products = Product.objects.select_related("vendor", "default_variant").prefetch_related(
        "variants",
        "variants__variant_image",
    )
    live_products = products.filter(is_live=True)
    products = live_products if live_products.exists() else products

    products = products.annotate(
        display_price=Coalesce("default_variant__price", Min("variants__price")),
        reviews_total=Count(
            "reviews",
            filter=Q(reviews__status=ProductReview.STATUS_APPROVED),
            distinct=True,
        ),
        average_rating=Coalesce(
            Avg("reviews__rating", filter=Q(reviews__status=ProductReview.STATUS_APPROVED)),
            Value(0.0),
        ),
        available_variants=Count(
            "variants",
            filter=(
                Q(variants__track_inventory=True, variants__stock__gt=0)
                | Q(variants__track_inventory=False, variants__stock_status=StockStatus.IN_STOCK)
            ),
            distinct=True,
        ),
    )

    categories = (
        products.exclude(category__isnull=True)
        .exclude(category__exact="")
        .values("category")
        .annotate(total=Count("id"))
        .order_by("category")
    )

    selected_category = request.GET.get("category", "").strip()
    selected_prices = request.GET.getlist("price")
    selected_sort = request.GET.get("sort", "popular").strip() or "popular"
    selected_query = request.GET.get("q", "").strip()

    if selected_query:
        products = products.filter(
            Q(name__icontains=selected_query)
            | Q(summary__icontains=selected_query)
            | Q(description__icontains=selected_query)
            | Q(category__icontains=selected_query)
            | Q(vendor__name__icontains=selected_query)
        )

    if selected_category:
        products = products.filter(category=selected_category)

    valid_price_filters = []
    price_query = Q()
    price_ranges = {
        "under_25": Q(display_price__lt=25),
        "25_50": Q(display_price__gte=25, display_price__lt=50),
        "50_100": Q(display_price__gte=50, display_price__lt=100),
        "100_plus": Q(display_price__gte=100),
    }
    for key in selected_prices:
        if key in price_ranges:
            valid_price_filters.append(key)
            price_query |= price_ranges[key]

    if valid_price_filters:
        products = products.filter(price_query)

    if selected_sort == "newest":
        products = products.order_by("-created_at", "-id")
    elif selected_sort == "price_asc":
        products = products.order_by("display_price", "name")
    elif selected_sort == "price_desc":
        products = products.order_by("-display_price", "name")
    elif selected_sort == "rating_desc":
        products = products.order_by("-average_rating", "-reviews_total", "name")
    else:
        selected_sort = "popular"
        products = products.order_by("-reviews_total", "-created_at", "name")

    paginator = Paginator(products, 9)
    page_obj = paginator.get_page(request.GET.get("page") or 1)
    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(
        request,
        "store/catalog.html",
        {
            "products": page_obj.object_list,
            "page_obj": page_obj,
            "categories": categories,
            "selected_category": selected_category,
            "selected_prices": valid_price_filters,
            "selected_sort": selected_sort,
            "selected_query": selected_query,
            "querystring": query_params.urlencode(),
        },
    )


def product_detail(request, product_id):
    product = get_object_or_404(
        Product.objects.select_related("vendor", "default_variant").prefetch_related("variants"),
        id=product_id,
    )
    variants = list(product.variants.all())
    for variant in variants:
        variant.is_available = is_variant_available(variant)
    default_variant = product.default_variant or (variants[0] if variants else None)
    if default_variant and not is_variant_available(default_variant):
        default_variant = next((variant for variant in variants if is_variant_available(variant)), default_variant)
    gallery_images = []
    seen_image_ids = set()

    for variant in variants:
        for image in variant.variant_image.all():
            if image.id in seen_image_ids:
                continue
            seen_image_ids.add(image.id)
            gallery_images.append(image)

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "Yorum yapmak icin giris yapin.")
            return redirect("account_login")

        rating_raw = request.POST.get("rating", "").strip()
        comment = request.POST.get("comment", "").strip()

        try:
            rating = int(rating_raw)
        except (TypeError, ValueError):
            rating = 0

        if rating < 1 or rating > 5:
            messages.error(request, "Puan 1 ile 5 arasinda olmali.")
            return redirect("product_detail", product_id=product.id)

        ProductReview.objects.update_or_create(
            product=product,
            user=request.user,
            defaults={"rating": rating, "comment": comment, "status": ProductReview.STATUS_APPROVED},
        )
        messages.success(request, "Degerlendirmeniz kaydedildi.")
        return redirect("product_detail", product_id=product.id)

    reviews_qs = product.reviews.filter(status=ProductReview.STATUS_APPROVED).select_related("user")
    reviews = list(reviews_qs)
    rating_stats = reviews_qs.aggregate(avg=Avg("rating"), total=Count("id"))
    average_rating = float(rating_stats["avg"] or 0)
    reviews_count = rating_stats["total"] or 0

    histogram_rows = (
        reviews_qs.values("rating")
        .annotate(total=Count("id"))
        .order_by("-rating")
    )
    rating_histogram = {score: 0 for score in range(1, 6)}
    for row in histogram_rows:
        rating_histogram[int(row["rating"])] = int(row["total"])

    related_products = (
        Product.objects.select_related("default_variant")
        .prefetch_related("variants", "variants__variant_image")
        .filter(is_live=True)
        .exclude(id=product.id)
    )
    if product.category:
        related_products = related_products.filter(category=product.category)
    related_products = related_products[:4]

    user_review = None
    if request.user.is_authenticated:
        user_review = next((r for r in reviews if r.user_id == request.user.id), None)

    return render(
        request,
        "store/product_detail.html",
        {
            "product": product,
            "variants": variants,
            "default_variant": default_variant,
            "has_available_variants": any(variant.is_available for variant in variants),
            "gallery_images": gallery_images,
            "reviews": reviews,
            "average_rating": average_rating,
            "reviews_count": reviews_count,
            "rating_histogram": rating_histogram,
            "user_review": user_review,
            "related_products": related_products,
        },
    )
