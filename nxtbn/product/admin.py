import csv
import io
import re

from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from nxtbn.core.admin_mixins import AutoUserStampMixin, OpsAdminMixin, export_queryset_as_csv
from nxtbn.core.enum_helper import ProductType, StockStatus
from nxtbn.filemanager.models import Image
from nxtbn.vendor.models import Vendor

from .admin_forms import QuickProductCreateForm
from .models import Category, Product, ProductReview, ProductVariant


def _normalize_text(value):
    return re.sub(r"\s+", " ", (value or "").strip())


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    classes = ("collapse",)
    fields = (
        "name",
        "sku",
        "price",
        "compare_at_price",
        "cost_per_unit",
        "variant_image",
        "track_inventory",
        "stock",
        "low_stock_threshold",
        "stock_status",
    )
    show_change_link = True


@admin.register(Category)
class CategoryAdmin(OpsAdminMixin, admin.ModelAdmin):
    add_form_template = "admin/product/category/add_form.html"
    list_display = ("name", "is_active", "sort_order", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    readonly_fields = ("id", "created_at", "last_modified")
    fieldsets = (
        ("Kategori", {"fields": ("name", "slug", "is_active", "sort_order")}),
        ("Kayit", {"fields": ("id", "created_at", "last_modified"), "classes": ("collapse",)}),
    )


@admin.register(Product)
class ProductAdmin(AutoUserStampMixin, OpsAdminMixin, admin.ModelAdmin):
    change_form_template = "admin/product/product/change_form.html"
    change_list_template = "admin/product/product/change_list.html"
    list_display = ("name", "vendor", "category_name", "brand", "is_live", "currency", "created_at")
    list_filter = ("is_live", "vendor", "category_ref", "brand", "type", "created_at")
    search_fields = ("id", "name", "summary", "description", "brand", "category_ref__name", "category")
    actions = ("export_selected_as_csv",)
    exclude = ("created_by", "last_modified_by")
    readonly_fields = ("id", "currency", "created_at", "last_modified", "category")
    inlines = [ProductVariantInline]
    autocomplete_fields = ("vendor", "category_ref", "default_variant")
    filter_horizontal = ("media", "related_to")
    fieldsets = (
        ("Temel Bilgiler", {"fields": ("name", "vendor", "category_ref", "type", "is_live", "published_date")}),
        ("Katalog", {"fields": ("brand", "subscribable"), "classes": ("collapse",)}),
        ("Aciklama", {"fields": ("summary", "description"), "classes": ("collapse",)}),
        ("Iliski ve Medya", {"fields": ("related_to", "media"), "classes": ("collapse",)}),
        ("Varyant ve Fiyat", {"fields": ("default_variant", "currency"), "classes": ("collapse",)}),
        ("Uyumluluk", {"fields": ("category",), "classes": ("collapse",)}),
        ("Kayit", {"fields": ("id", "created_at", "last_modified"), "classes": ("collapse",)}),
    )

    @admin.display(description="Kategori")
    def category_name(self, obj):
        return obj.effective_category or "-"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("vendor", "category_ref", "default_variant")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if request.LANGUAGE_CODE and request.LANGUAGE_CODE.startswith("tr"):
            if "name" in form.base_fields:
                form.base_fields["name"].label = _("Urun Adi")
            if "vendor" in form.base_fields:
                form.base_fields["vendor"].label = _("Tedarikci")
            if "category_ref" in form.base_fields:
                form.base_fields["category_ref"].label = _("Kategori")
        return form

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if not formfield:
            return formfield

        labels = {
            "tr": {"name": _("Urun Adi"), "vendor": _("Tedarikci"), "category_ref": _("Kategori")},
            "en": {"name": _("Name"), "vendor": _("Vendor"), "category_ref": _("Category")},
        }
        lang = "tr" if (request.LANGUAGE_CODE or "").startswith("tr") else "en"
        if db_field.name in labels[lang]:
            formfield.label = labels[lang][db_field.name]
        return formfield

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "quick-add/",
                self.admin_site.admin_view(self.quick_add_view),
                name="product_product_quick_add",
            ),
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

    def _create_quick_product(self, request, cleaned_data):
        product_name = cleaned_data["name"].strip()
        category_ref = cleaned_data["category_ref"]
        vendor = cleaned_data["resolved_vendor"]
        stock_value = cleaned_data["stock"] or 0
        price_value = cleaned_data["price"]
        is_turkish = (request.LANGUAGE_CODE or "").startswith("tr")
        summary_text = (
            f"{product_name} icin hizli olusturulan urun kaydi."
            if is_turkish
            else f"Quickly created product record for {product_name}."
        )
        description_text = (
            f"{product_name} urunu icin temel aciklama."
            if is_turkish
            else f"Basic description for {product_name}."
        )
        default_variant_name = "Varsayilan" if is_turkish else "Default"

        product = Product.objects.create(
            created_by=request.user,
            last_modified_by=request.user,
            name=product_name,
            summary=summary_text,
            description=description_text,
            category_ref=category_ref,
            vendor=vendor,
            type=ProductType.SIMPLE_PRODUCT,
            currency="TRY",
            is_live=False,
        )
        variant = ProductVariant.objects.create(
            product=product,
            name=default_variant_name,
            compare_at_price=price_value,
            price=price_value,
            cost_per_unit=price_value,
            stock=stock_value,
            track_inventory=True,
            stock_status=StockStatus.IN_STOCK if stock_value > 0 else StockStatus.OUT_OF_STOCK,
        )
        Product.objects.filter(pk=product.pk).update(default_variant=variant, last_modified_by=request.user)
        product.default_variant = variant

        uploaded_image = cleaned_data.get("image")
        if uploaded_image:
            image_record = Image.objects.create(
                created_by=request.user,
                last_modified_by=request.user,
                name=_normalize_text(product_name)[:255],
                image=uploaded_image,
                image_alt_text=_normalize_text(product_name)[:255],
            )
            variant.variant_image.add(image_record)
        return product

    def quick_add_view(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied

        can_create_vendor = request.user.has_perm("vendor.add_vendor")
        if request.method == "POST":
            form = QuickProductCreateForm(request.POST, request.FILES, can_create_vendor=can_create_vendor)
            if form.is_valid():
                product = self._create_quick_product(request, form.cleaned_data)
                is_turkish = (request.LANGUAGE_CODE or "").startswith("tr")
                success_message = "Hizli urun olusturma tamamlandi." if is_turkish else "Quick product creation completed."
                self.message_user(request, success_message, level=messages.SUCCESS)

                if "_addanother" in request.POST:
                    return redirect(reverse("admin:product_product_quick_add"))
                return redirect(reverse("admin:product_product_change", args=[product.pk]))
        else:
            form = QuickProductCreateForm(can_create_vendor=can_create_vendor)

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": _("Hizli Urun Ekle") if (request.LANGUAGE_CODE or "").startswith("tr") else _("Quick Add Product"),
            "form": form,
            "is_popup": request.GET.get("_popup") or request.POST.get("_popup"),
            "is_popup_var": "_popup",
            "to_field_var": "_to_field",
            "to_field": request.GET.get("_to_field") or request.POST.get("_to_field"),
            "advanced_add_url": reverse("admin:product_product_add"),
            "changelist_url": reverse("admin:product_product_changelist"),
        }
        return render(request, "admin/product/product/quick_add.html", context)

    def save_model(self, request, obj, form, change):
        obj.currency = "TRY"
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        product = form.instance
        if not product.default_variant_id:
            first_variant = product.variants.first()
            if first_variant:
                Product.objects.filter(pk=product.pk).update(default_variant=first_variant)

    @admin.action(description="Secili urunleri CSV olarak disa aktar")
    def export_selected_as_csv(self, request, queryset):
        return self._export_queryset_as_csv(queryset)

    def _export_queryset_as_csv(self, queryset):
        headers = [
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
        rows = []
        for product in queryset.select_related("vendor", "default_variant", "category_ref").prefetch_related("variants"):
            variants = list(product.variants.all()) or [None]
            for variant in variants:
                rows.append(
                    [
                        product.id,
                        product.name,
                        product.summary,
                        product.description,
                        product.effective_category,
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
        return export_queryset_as_csv("products_export.csv", headers, rows)

    def export_all_as_csv_view(self, request):
        queryset = Product.objects.all()
        return self._export_queryset_as_csv(queryset)

    def import_csv_view(self, request):
        if request.method == "POST":
            file_obj = request.FILES.get("csv_file")
            if not file_obj:
                self.message_user(request, _("Lutfen bir CSV dosyasi yukleyin."), level=messages.ERROR)
                return redirect("..")

            text_file = io.TextIOWrapper(file_obj.file, encoding="utf-8")
            reader = csv.DictReader(text_file)
            created_products = 0
            updated_products = 0
            created_variants = 0

            for row in reader:
                name = _normalize_text(row.get("name"))
                vendor_name = _normalize_text(row.get("vendor"))
                if not name or not vendor_name:
                    continue

                vendor = Vendor.objects.filter(name__iexact=vendor_name).order_by("name").first()
                if not vendor:
                    vendor = Vendor.objects.create(name=vendor_name)

                raw_category = _normalize_text(row.get("category"))
                category_ref = Category.resolve_from_name(raw_category, create=True) if raw_category else None

                product_id = _normalize_text(row.get("product_id"))
                product = Product.objects.filter(id=product_id).first() if product_id else None
                defaults = {
                    "summary": (row.get("summary") or "").strip()[:500],
                    "description": (row.get("description") or "").strip()[:500],
                    "category_ref": category_ref,
                    "category": (category_ref.name if category_ref else None),
                    "brand": _normalize_text(row.get("brand")) or None,
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

                variant_name = _normalize_text(row.get("variant_name")) or "Default"
                sku = _normalize_text(row.get("sku")) or None
                try:
                    stock_value = int(float(row.get("stock") or 0))
                except (TypeError, ValueError):
                    stock_value = 0
                price_value = _normalize_text(row.get("price")) or "0.01"
                compare_price_value = _normalize_text(row.get("compare_at_price")) or price_value
                variant_defaults = {
                    "compare_at_price": compare_price_value,
                    "price": price_value,
                    "stock": stock_value,
                    "stock_status": StockStatus.IN_STOCK if stock_value > 0 else StockStatus.OUT_OF_STOCK,
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
                        stock_status=variant_defaults["stock_status"],
                        cost_per_unit=variant_defaults["price"],
                    )
                    created_variants += 1

                if not product.default_variant_id:
                    first_variant = product.variants.first()
                    if first_variant:
                        Product.objects.filter(pk=product.pk).update(default_variant=first_variant)

            self.message_user(
                request,
                _(
                    "CSV ice aktarma tamamlandi. Yeni urun: %(created)s, guncellenen urun: %(updated)s, yeni varyant: %(variants)s."
                )
                % {"created": created_products, "updated": updated_products, "variants": created_variants},
                level=messages.SUCCESS,
            )
            return redirect(reverse("admin:product_product_changelist"))

        context = {
            **self.admin_site.each_context(request),
            "title": _("CSV ile urun ice aktar"),
        }
        return render(request, "admin/product/product/import_csv.html", context)


@admin.register(ProductVariant)
class ProductVariantAdmin(OpsAdminMixin, admin.ModelAdmin):
    list_display = ("product", "name", "sku", "price", "stock", "stock_status")
    list_filter = ("track_inventory", "stock_status", "product__vendor")
    search_fields = ("id", "product__name", "sku", "name")
    filter_horizontal = ("variant_image",)
    autocomplete_fields = ("product",)
    readonly_fields = ("id",)
    fieldsets = (
        ("Kimlik", {"fields": ("id", "product", "name", "sku")}),
        ("Fiyat", {"fields": ("price", "compare_at_price", "cost_per_unit")}),
        ("Stok", {"fields": ("track_inventory", "stock", "low_stock_threshold", "stock_status")}),
        ("Lojistik", {"fields": ("weight_unit", "weight_value", "variant_image")}),
    )


@admin.register(ProductReview)
class ProductReviewAdmin(OpsAdminMixin, admin.ModelAdmin):
    list_display = ("product", "user", "rating", "status", "report_count", "created_at")
    list_filter = ("rating", "status", "created_at")
    search_fields = ("id", "product__name", "user__email", "user__username", "comment")
    actions = ("mark_approved", "mark_hidden")
    autocomplete_fields = ("product", "user")
    readonly_fields = ("id", "created_at", "last_modified")
    fieldsets = (
        ("Degerlendirme", {"fields": ("product", "user", "rating", "comment")}),
        ("Moderasyon", {"fields": ("status", "report_count")}),
        ("Kayit", {"fields": ("id", "created_at", "last_modified"), "classes": ("collapse",)}),
    )

    @admin.action(description="Secili yorumlari onayla")
    def mark_approved(self, request, queryset):
        queryset.update(status="approved")

    @admin.action(description="Secili yorumlari gizle")
    def mark_hidden(self, request, queryset):
        queryset.update(status="hidden")
