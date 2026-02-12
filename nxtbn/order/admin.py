import csv

from django.contrib import admin
from django.http import HttpResponse
from django.urls import path

from .models import Order, OrderItem, OrderStatusEvent


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "sku", "unit_price", "quantity", "line_total")


class OrderStatusEventInline(admin.TabularInline):
    model = OrderStatusEvent
    extra = 0
    readonly_fields = ("status", "note", "changed_by", "created_at")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    change_list_template = "admin/order/order/change_list.html"
    list_display = ("id", "full_name", "email", "status", "total", "payment_method", "created_at")
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("full_name", "email", "id")
    actions = ("mark_processing", "mark_shipped", "mark_delivered", "mark_cancelled", "export_selected_orders_as_csv")
    inlines = [OrderItemInline, OrderStatusEventInline]

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

    @admin.action(description="Mark selected orders as Processing")
    def mark_processing(self, request, queryset):
        queryset.update(status=Order.STATUS_PROCESSING)

    @admin.action(description="Mark selected orders as Shipped")
    def mark_shipped(self, request, queryset):
        queryset.update(status=Order.STATUS_SHIPPED)

    @admin.action(description="Mark selected orders as Delivered")
    def mark_delivered(self, request, queryset):
        queryset.update(status=Order.STATUS_DELIVERED)

    @admin.action(description="Mark selected orders as Cancelled")
    def mark_cancelled(self, request, queryset):
        queryset.update(status=Order.STATUS_CANCELLED)

    @admin.action(description="Export selected orders as CSV")
    def export_selected_orders_as_csv(self, request, queryset):
        return self._export_orders_csv(queryset)

    def _export_orders_csv(self, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="orders_export.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
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
        )
        for order in queryset.order_by("-created_at"):
            writer.writerow(
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
            )
        return response

    def export_all_orders_as_csv_view(self, request):
        return self._export_orders_csv(Order.objects.all())
