from django.contrib import admin

from nxtbn.core.admin_mixins import OpsAdminMixin, status_update_action
from nxtbn.payment.models import PaymentEvent, PaymentMethodConfig, PaymentTransaction


@admin.register(PaymentMethodConfig)
class PaymentMethodConfigAdmin(OpsAdminMixin, admin.ModelAdmin):
    list_display = ("provider", "is_active", "merchant_id", "created_at")
    list_filter = ("provider", "is_active", "created_at")
    search_fields = ("provider", "merchant_id")
    readonly_fields = ("id", "created_at", "last_modified")
    fieldsets = (
        ("Saglayici", {"fields": ("provider", "is_active")}),
        ("Kimlik Bilgileri", {"fields": ("merchant_id", "public_key", "secret_key")}),
        ("Ek Ayarlar", {"fields": ("extra_config",)}),
        ("Kayit", {"fields": ("id", "created_at", "last_modified"), "classes": ("collapse",)}),
    )


class PaymentEventInline(admin.TabularInline):
    model = PaymentEvent
    extra = 0
    readonly_fields = ("event_type", "idempotency_key", "signature_valid", "processed", "created_at", "raw_payload")
    can_delete = False


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(OpsAdminMixin, admin.ModelAdmin):
    list_display = ("order", "provider", "status", "amount", "currency", "created_at")
    list_filter = ("provider", "status", "currency", "is_processed", "created_at")
    search_fields = ("order__id", "external_id", "token")
    autocomplete_fields = ("order",)
    readonly_fields = ("id", "created_at", "last_modified", "processed_at")
    fieldsets = (
        ("Islem", {"fields": ("order", "provider", "status", "external_id", "token")}),
        ("Tutar", {"fields": ("amount", "currency")}),
        ("Durum", {"fields": ("is_processed", "processed_at", "error_message")}),
        ("Kayit", {"fields": ("id", "created_at", "last_modified"), "classes": ("collapse",)}),
    )
    actions = ("mark_success", "mark_failed", "mark_cancelled")
    inlines = [PaymentEventInline]

    mark_success = status_update_action(
        "Secili islemleri Basarili yap",
        PaymentTransaction.STATUS_SUCCESS,
        allowed_from=(PaymentTransaction.STATUS_PENDING, PaymentTransaction.STATUS_FAILED),
    )
    mark_failed = status_update_action(
        "Secili islemleri Basarisiz yap",
        PaymentTransaction.STATUS_FAILED,
        allowed_from=(PaymentTransaction.STATUS_PENDING, PaymentTransaction.STATUS_SUCCESS),
    )
    mark_cancelled = status_update_action(
        "Secili islemleri Iptal yap",
        PaymentTransaction.STATUS_CANCELLED,
        allowed_from=(PaymentTransaction.STATUS_PENDING, PaymentTransaction.STATUS_SUCCESS),
    )


@admin.register(PaymentEvent)
class PaymentEventAdmin(OpsAdminMixin, admin.ModelAdmin):
    list_display = ("transaction", "event_type", "idempotency_key", "signature_valid", "processed", "created_at")
    list_filter = ("event_type", "signature_valid", "processed", "created_at")
    search_fields = ("transaction__order__id", "idempotency_key")
    autocomplete_fields = ("transaction",)
    readonly_fields = (
        "id",
        "transaction",
        "event_type",
        "idempotency_key",
        "raw_payload",
        "signature_valid",
        "processed",
        "created_at",
        "last_modified",
    )
