from django.contrib import admin

from nxtbn.discount.models import Coupon


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "discount_value", "is_active", "used_count", "usage_limit", "ends_at")
    list_filter = ("discount_type", "is_active")
    search_fields = ("code",)
