from django.contrib import admin

from nxtbn.core.admin_mixins import OpsAdminMixin
from nxtbn.tax.models import TaxRule


@admin.register(TaxRule)
class TaxRuleAdmin(OpsAdminMixin, admin.ModelAdmin):
    list_display = ("name", "category", "rate", "priority", "is_active")
    list_filter = ("is_active", "category", "created_at")
    search_fields = ("id", "name", "category")
    readonly_fields = ("id", "created_at", "last_modified")
    fieldsets = (
        ("Kural", {"fields": ("name", "category", "rate", "priority", "is_active")}),
        ("Kayit", {"fields": ("id", "created_at", "last_modified"), "classes": ("collapse",)}),
    )
