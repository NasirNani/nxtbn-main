from django.contrib import admin

from nxtbn.payment.models import PaymentEvent, PaymentMethodConfig, PaymentTransaction


@admin.register(PaymentMethodConfig)
class PaymentMethodConfigAdmin(admin.ModelAdmin):
    list_display = ("provider", "is_active", "merchant_id", "created_at")
    list_filter = ("provider", "is_active")


class PaymentEventInline(admin.TabularInline):
    model = PaymentEvent
    extra = 0
    readonly_fields = ("event_type", "idempotency_key", "signature_valid", "processed", "created_at")


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("order", "provider", "status", "amount", "currency", "created_at")
    list_filter = ("provider", "status", "currency")
    search_fields = ("order__id", "external_id", "token")
    inlines = [PaymentEventInline]


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ("transaction", "event_type", "idempotency_key", "signature_valid", "processed", "created_at")
    list_filter = ("event_type", "signature_valid", "processed")
