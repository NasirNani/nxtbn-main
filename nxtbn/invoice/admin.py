from django.contrib import admin

from nxtbn.invoice.models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "order", "status", "issued_at", "paid_at")
    list_filter = ("status",)
    search_fields = ("number", "order__id", "order__email", "order__full_name")
