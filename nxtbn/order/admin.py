from django.contrib import admin
from django.urls import path

from nxtbn.core.admin_mixins import OpsAdminMixin, export_queryset_as_csv, status_update_action

from .models import Order, OrderItem, OrderStatusEvent


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "sku", "unit_price", "quantity", "line_total")
    can_delete = False


class OrderStatusEventInline(admin.TabularInline):
    model = OrderStatusEvent
    extra = 0
    readonly_fields = ("status", "note", "changed_by", "created_at")
    can_delete = False


@admin.register(Order)
class OrderAdmin(OpsAdminMixin, admin.ModelAdmin):
    change_list_template = "admin/order/order/change_list.html"
    list_display = ("id", "full_name", "email", "status", "total", "payment_method", "created_at")
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("id", "full_name", "email", "phone", "tracking_number")
    actions = ("mark_processing", "mark_shipped", "mark_delivered", "mark_cancelled", "export_selected_orders_as_csv")
    inlines = [OrderItemInline, OrderStatusEventInline]
    autocomplete_fields = ("user",)
    readonly_fields = ("id", "created_at", "last_modified")
    fieldsets = (
        ("Musteri Bilgileri", {"fields": ("user", "full_name", "email", "phone")}),
        ("Teslimat", {"fields": ("address_line1", "address_line2", "city", "state", "postal_code", "country")}),
        (
            "Siparis ve Odeme",
            {
                "fields": (
                    "status",
                    "payment_method",
                    "payment_reference",
                    "coupon_code",
                    "gift_card_code",
                    "notes",
                )
            },
        ),
        (
            "Kargo ve Iade",
            {
                "fields": (
                    "cancellation_requested",
                    "cancellation_reason",
                    "tracking_number",
                    "tracking_url",
                    "shipped_at",
                    "delivered_at",
                )
            },
        ),
        ("Tutarlar", {"fields": ("subtotal", "discount", "tax", "shipping", "total")}),
        ("Kayit", {"fields": ("id", "created_at", "last_modified"), "classes": ("collapse",)}),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_all_orders_as_csv_view),
                name="order_order_export_csv",
            ),
        ]
        return custom_urls + urls

    mark_processing = status_update_action(
        "Secili siparisleri Isleniyor yap",
        Order.STATUS_PROCESSING,
        allowed_from=(Order.STATUS_PENDING, Order.STATUS_PAID),
    )
    mark_shipped = status_update_action(
        "Secili siparisleri Kargolandi yap",
        Order.STATUS_SHIPPED,
        allowed_from=(Order.STATUS_PROCESSING, Order.STATUS_PAID),
    )
    mark_delivered = status_update_action(
        "Secili siparisleri Teslim edildi yap",
        Order.STATUS_DELIVERED,
        allowed_from=(Order.STATUS_SHIPPED,),
    )
    mark_cancelled = status_update_action(
        "Secili siparisleri Iptal et",
        Order.STATUS_CANCELLED,
        allowed_from=(
            Order.STATUS_PENDING,
            Order.STATUS_PAID,
            Order.STATUS_PROCESSING,
        ),
    )

    @admin.action(description="Secili siparisleri CSV olarak disa aktar")
    def export_selected_orders_as_csv(self, request, queryset):
        return self._export_orders_csv(queryset)

    def _export_orders_csv(self, queryset):
        headers = [
            "order_id",
            "created_at",
            "status",
            "full_name",
            "email",
            "payment_method",
            "subtotal",
            "discount",
            "tax",
            "shipping",
            "total",
            "tracking_number",
        ]
        rows = (
            [
                order.id,
                order.created_at,
                order.status,
                order.full_name,
                order.email,
                order.payment_method,
                order.subtotal,
                order.discount,
                order.tax,
                order.shipping,
                order.total,
                order.tracking_number,
            ]
            for order in queryset.order_by("-created_at")
        )
        return export_queryset_as_csv("orders_export.csv", headers, rows)

    def export_all_orders_as_csv_view(self, request):
        return self._export_orders_csv(Order.objects.all())
