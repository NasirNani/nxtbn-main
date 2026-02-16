from django.contrib import admin

from nxtbn.core.admin_mixins import OpsAdminMixin
from nxtbn.discount.models import Coupon


@admin.register(Coupon)
class CouponAdmin(OpsAdminMixin, admin.ModelAdmin):
    list_display = ("code", "discount_type", "discount_value", "is_active", "used_count", "usage_limit", "ends_at")
    list_filter = ("discount_type", "is_active", "starts_at", "ends_at", "created_at")
    search_fields = ("id", "code")
    readonly_fields = ("id", "used_count", "created_at", "last_modified")
    fieldsets = (
        ("Kupon", {"fields": ("code", "discount_type", "discount_value")}),
        ("Kosullar", {"fields": ("min_subtotal", "max_discount", "usage_limit")}),
        ("Durum", {"fields": ("is_active", "starts_at", "ends_at", "used_count")}),
        ("Kayit", {"fields": ("id", "created_at", "last_modified"), "classes": ("collapse",)}),
    )
