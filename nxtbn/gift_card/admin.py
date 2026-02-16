from django.contrib import admin

from nxtbn.core.admin_mixins import OpsAdminMixin
from nxtbn.gift_card.models import GiftCard, GiftCardTransaction


class GiftCardTransactionInline(admin.TabularInline):
    model = GiftCardTransaction
    extra = 0
    readonly_fields = ("transaction_type", "amount", "order", "note", "created_at")
    can_delete = False


@admin.register(GiftCard)
class GiftCardAdmin(OpsAdminMixin, admin.ModelAdmin):
    list_display = ("code", "balance", "currency", "is_active", "expires_at")
    list_filter = ("is_active", "currency", "expires_at", "created_at")
    search_fields = ("id", "code")
    readonly_fields = ("id", "created_at", "last_modified")
    fieldsets = (
        ("Kart", {"fields": ("code", "balance", "currency")}),
        ("Gecerlilik", {"fields": ("is_active", "expires_at")}),
        ("Kayit", {"fields": ("id", "created_at", "last_modified"), "classes": ("collapse",)}),
    )
    inlines = [GiftCardTransactionInline]


@admin.register(GiftCardTransaction)
class GiftCardTransactionAdmin(OpsAdminMixin, admin.ModelAdmin):
    list_display = ("gift_card", "transaction_type", "amount", "order", "created_at")
    list_filter = ("transaction_type", "created_at")
    search_fields = ("id", "gift_card__code", "order__id", "note")
    autocomplete_fields = ("gift_card", "order")
    readonly_fields = ("id", "created_at", "last_modified")
