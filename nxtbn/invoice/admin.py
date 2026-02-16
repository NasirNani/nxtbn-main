from django.contrib import admin

from nxtbn.core.admin_mixins import OpsAdminMixin, status_update_action
from nxtbn.invoice.models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(OpsAdminMixin, admin.ModelAdmin):
    list_display = ("number", "order", "status", "issued_at", "paid_at")
    list_filter = ("status", "issued_at", "paid_at")
    search_fields = ("id", "number", "order__id", "order__email", "order__full_name")
    autocomplete_fields = ("order",)
    readonly_fields = ("id", "issued_at", "created_at", "last_modified")
    fieldsets = (
        ("Fatura", {"fields": ("order", "number", "status")}),
        ("Detay", {"fields": ("issued_at", "paid_at", "notes")}),
        ("Kayit", {"fields": ("id", "created_at", "last_modified"), "classes": ("collapse",)}),
    )
    actions = ("mark_issued", "mark_paid", "mark_void")

    mark_issued = status_update_action(
        "Secili kayitlari Kesildi yap",
        Invoice.STATUS_ISSUED,
        allowed_from=(Invoice.STATUS_DRAFT, Invoice.STATUS_VOID),
    )
    mark_paid = status_update_action(
        "Secili kayitlari Odendi yap",
        Invoice.STATUS_PAID,
        allowed_from=(Invoice.STATUS_ISSUED,),
    )
    mark_void = status_update_action(
        "Secili kayitlari Iptal yap",
        Invoice.STATUS_VOID,
        allowed_from=(Invoice.STATUS_DRAFT, Invoice.STATUS_ISSUED),
    )
