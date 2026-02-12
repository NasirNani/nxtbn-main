import csv
import io

from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path, reverse

from .models import Product, ProductReview, ProductVariant


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = (
        "name",
        "price",
        "compare_at_price",
        "variant_image",
        "track_inventory",
        "stock",
        "stock_status",
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    change_form_template = "admin/product/product/change_form.html"
    change_list_template = "admin/product/product/change_list.html"
    list_display = ("name", "vendor", "category", "brand", "is_live", "currency", "created_at")
    list_filter = ("is_live", "vendor", "category", "brand", "type")
    search_fields = ("name", "summary", "description", "brand", "category")
    actions = ("export_selected_as_csv",)
    exclude = ("created_by", "last_modified_by")
    readonly_fields = ("currency",)
    inlines = [ProductVariantInline]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name="product_product_import_csv",
            ),
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_all_as_csv_view),
                name="product_product_export_csv",
            ),
        ]
        return custom_urls + urls

    def save_model(self, request, obj, form, change):
        if not change or obj.created_by_id is None:
            obj.created_by = request.user
        obj.last_modified_by = request.user
        obj.currency = "TRY"
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        product = form.instance
        if not product.default_variant_id:
            first_variant = product.variants.first()
            if first_variant:
                product.default_variant = first_variant
                product.save(update_fields=["default_variant"])

    @admin.action(description="Export selected products as CSV")
    def export_selected_as_csv(self, request, queryset):
        return self._export_queryset_as_csv(queryset)

    def _export_queryset_as_csv(self, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="products_export.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "product_id",
                "name",
                "summary",
                "description",
                "category",
                "brand",
                "vendor",
                "is_live",
                "variant_name",
                "sku",
                "price",
                "compare_at_price",
                "stock",
            ]
        )
        for product in queryset.select_related("vendor", "default_variant").prefetch_related("variants"):
            variants = list(product.variants.all()) or [None]
            for variant in variants:
                writer.writerow(
                    [
                        product.id,
                        product.name,
                        product.summary,
                        product.description,
                        product.category,
                        product.brand,
                        product.vendor.name,
                        product.is_live,
                        getattr(variant, "name", ""),
                        getattr(variant, "sku", ""),
                        getattr(variant, "price", ""),
                        getattr(variant, "compare_at_price", ""),
                        getattr(variant, "stock", ""),
                    ]
                )
        return response

    def export_all_as_csv_view(self, request):
        queryset = Product.objects.all()
        return self._export_queryset_as_csv(queryset)

    def import_csv_view(self, request):
        if request.method == "POST":
            file_obj = request.FILES.get("csv_file")
            if not file_obj:
                self.message_user(request, "Please upload a CSV file.", level=messages.ERROR)
                return redirect("..")

            text_file = io.TextIOWrapper(file_obj.file, encoding="utf-8")
            reader = csv.DictReader(text_file)
            created_products = 0
            updated_products = 0
            created_variants = 0

            from nxtbn.vendor.models import Vendor

            for row in reader:
                name = (row.get("name") or "").strip()
                vendor_name = (row.get("vendor") or "").strip()
                if not name or not vendor_name:
                    continue

                vendor, _ = Vendor.objects.get_or_create(name=vendor_name)
                product_id = (row.get("product_id") or "").strip()
                product = None
                if product_id:
                    product = Product.objects.filter(id=product_id).first()

                defaults = {
                    "summary": (row.get("summary") or "").strip()[:500],
                    "description": (row.get("description") or "").strip()[:500],
                    "category": (row.get("category") or "").strip() or None,
                    "brand": (row.get("brand") or "").strip() or None,
                    "vendor": vendor,
                    "last_modified_by": request.user,
                    "is_live": str(row.get("is_live", "")).strip().lower() in ("1", "true", "yes"),
                }
                if product:
                    for key, value in defaults.items():
                        setattr(product, key, value)
                    product.save()
                    updated_products += 1
                else:
                    product = Product.objects.create(
                        created_by=request.user,
                        **defaults,
                        name=name,
                    )
                    created_products += 1

                variant_name = (row.get("variant_name") or "").strip() or "Default"
                sku = (row.get("sku") or "").strip() or None
                try:
                    stock_value = int(float(row.get("stock") or 0))
                except (TypeError, ValueError):
                    stock_value = 0
                price_value = (row.get("price") or "0.01").strip() or "0.01"
                compare_price_value = (row.get("compare_at_price") or price_value).strip() or price_value
                variant_defaults = {
                    "compare_at_price": compare_price_value,
                    "price": price_value,
                    "stock": stock_value,
                }
                variant = None
                if sku:
                    variant = ProductVariant.objects.filter(sku=sku).first()
                if not variant:
                    variant = product.variants.filter(name=variant_name).first()
                if variant:
                    for key, value in variant_defaults.items():
                        setattr(variant, key, value)
                    variant.name = variant_name
                    variant.save()
                else:
                    ProductVariant.objects.create(
                        product=product,
                        name=variant_name,
                        sku=sku,
                        compare_at_price=variant_defaults["compare_at_price"],
                        price=variant_defaults["price"],
                        stock=variant_defaults["stock"],
                        cost_per_unit=variant_defaults["price"],
                    )
                    created_variants += 1

                if not product.default_variant_id:
                    first_variant = product.variants.first()
                    if first_variant:
                        product.default_variant = first_variant
                        product.save(update_fields=["default_variant"])

            self.message_user(
                request,
                f"CSV import complete. Created products: {created_products}, updated products: {updated_products}, created variants: {created_variants}.",
                level=messages.SUCCESS,
            )
            return redirect(reverse("admin:product_product_changelist"))

        context = {
            **self.admin_site.each_context(request),
            "title": "Import products from CSV",
        }
        return render(request, "admin/product/product/import_csv.html", context)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "name", "sku", "price", "stock", "stock_status")
    list_filter = ("track_inventory", "stock_status", "product__vendor")
    search_fields = ("product__name", "sku", "name")
    filter_horizontal = ("variant_image",)


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "status", "report_count", "created_at")
    list_filter = ("rating", "status", "created_at")
    search_fields = ("product__name", "user__email", "user__username", "comment")
    actions = ("mark_approved", "mark_hidden")

    @admin.action(description="Mark selected reviews as approved")
    def mark_approved(self, request, queryset):
        queryset.update(status="approved")

    @admin.action(description="Mark selected reviews as hidden")
    def mark_hidden(self, request, queryset):
        queryset.update(status="hidden")
