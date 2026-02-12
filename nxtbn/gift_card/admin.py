from django.contrib import admin

from nxtbn.gift_card.models import GiftCard, GiftCardTransaction


class GiftCardTransactionInline(admin.TabularInline):
    model = GiftCardTransaction
    extra = 0
    readonly_fields = ("transaction_type", "amount", "order", "note", "created_at")


@admin.register(GiftCard)
class GiftCardAdmin(admin.ModelAdmin):
    list_display = ("code", "balance", "currency", "is_active", "expires_at")
    list_filter = ("is_active", "currency")
    search_fields = ("code",)
    inlines = [GiftCardTransactionInline]


@admin.register(GiftCardTransaction)
class GiftCardTransactionAdmin(admin.ModelAdmin):
    list_display = ("gift_card", "transaction_type", "amount", "order", "created_at")
    list_filter = ("transaction_type",)
