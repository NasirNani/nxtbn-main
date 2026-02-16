from django.apps import apps
from django.http import Http404
from django.db import DatabaseError
from django.shortcuts import render
from django.db.models import Count
from django.db.models.functions import Coalesce

from nxtbn.home.models import HomeSlide
from nxtbn.product.models import Product
from nxtbn.product.utils import resolve_product_card_image


MODULES = [
    {"label": "home", "title": "Home", "description": "Landing pages and storefront entry points."},
    {"label": "checkout", "title": "Checkout", "description": "Cart and checkout flow orchestration."},
    {"label": "core", "title": "Core", "description": "Core framework primitives and shared features."},
    {"label": "dashboard_api", "title": "Dashboard API", "description": "Dashboard-facing API surface."},
    {"label": "discount", "title": "Discount", "description": "Discount rules and promotional logic."},
    {"label": "filemanager", "title": "File Manager", "description": "Media and document storage."},
    {"label": "gift_card", "title": "Gift Card", "description": "Gift card issuance and redemption."},
    {"label": "invoice", "title": "Invoice", "description": "Invoice lifecycle and exports."},
    {"label": "order", "title": "Order", "description": "Order placement and tracking."},
    {"label": "payment", "title": "Payment", "description": "Payment processing and settlement."},
    {"label": "plugins", "title": "Plugins", "description": "Plugin registry and extension points."},
    {"label": "product", "title": "Product", "description": "Product catalog and variants."},
    {"label": "seo", "title": "SEO", "description": "Metadata and search optimization."},
    {"label": "storefront_api", "title": "Storefront API", "description": "Storefront API contracts."},
    {"label": "tax", "title": "Tax", "description": "Tax rules and calculations."},
    {"label": "users", "title": "Users", "description": "Authentication and account management."},
    {"label": "vendor", "title": "Vendor", "description": "Vendor and marketplace management."},
]

MODULE_MAP = {module["label"]: module for module in MODULES}


def _build_model_summary(app_label):
    app_config = apps.get_app_config(app_label)
    summaries = []

    for model in app_config.get_models():
        total = "N/A"
        try:
            total = model.objects.count()
        except DatabaseError:
            total = "Pending migration"
        summaries.append({"name": model._meta.verbose_name_plural.title(), "count": total})

    return summaries

def home(request):
    hero_slides = HomeSlide.objects.select_related("image").filter(is_active=True)
    products = Product.objects.select_related("vendor", "default_variant").prefetch_related(
        "variants",
        "variants__variant_image",
    )
    live_products = products.filter(is_live=True)
    featured_products = live_products if live_products.exists() else products
    featured_products = list(featured_products[:6])
    for product in featured_products:
        product.card_image = resolve_product_card_image(product)

    categories = (
        Product.objects.annotate(display_category=Coalesce("category_ref__name", "category"))
        .exclude(display_category__isnull=True)
        .exclude(display_category__exact="")
        .values("display_category")
        .annotate(total=Count("id"))
        .order_by("-total", "display_category")[:6]
    )
    categories = [{"category": row["display_category"], "total": row["total"]} for row in categories]

    return render(
        request,
        "home/index.html",
        {
            "hero_slides": hero_slides,
            "featured_products": featured_products,
            "categories": categories,
        },
    )


def modules_index(request):
    return render(request, "home/modules_index.html", {"modules": MODULES})


def about_page(request):
    return render(request, "home/about.html")


def contact_page(request):
    return render(request, "home/contact.html")


def module_detail(request, app_label):
    module = MODULE_MAP.get(app_label)
    if module is None:
        raise Http404("Module not found")

    model_summaries = _build_model_summary(app_label)

    return render(
        request,
        "home/module_detail.html",
        {"module": module, "model_summaries": model_summaries},
    )
