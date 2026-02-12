from django.db import models

from nxtbn.core.models import AbstractBaseModel


class PaymentMethodConfig(AbstractBaseModel):
    PROVIDER_PAYTR = "paytr"
    PROVIDER_MANUAL = "manual"
    PROVIDER_CHOICES = [
        (PROVIDER_PAYTR, "PayTR"),
        (PROVIDER_MANUAL, "Manual"),
    ]

    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, unique=True)
    is_active = models.BooleanField(default=True)
    public_key = models.CharField(max_length=255, blank=True, default="")
    secret_key = models.CharField(max_length=255, blank=True, default="")
    merchant_id = models.CharField(max_length=100, blank=True, default="")
    extra_config = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.provider


class PaymentTransaction(AbstractBaseModel):
    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    provider = models.CharField(max_length=20, default=PaymentMethodConfig.PROVIDER_PAYTR)
    order = models.ForeignKey("order.Order", on_delete=models.CASCADE, related_name="payment_transactions")
    external_id = models.CharField(max_length=120, blank=True, default="")
    token = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="TRY")
    error_message = models.TextField(blank=True, default="")
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.provider} {self.order_id} {self.status}"


class PaymentEvent(AbstractBaseModel):
    EVENT_REQUEST = "request"
    EVENT_CALLBACK = "callback"
    EVENT_WEBHOOK = "webhook"
    EVENT_CHOICES = [
        (EVENT_REQUEST, "Request"),
        (EVENT_CALLBACK, "Callback"),
        (EVENT_WEBHOOK, "Webhook"),
    ]

    transaction = models.ForeignKey(PaymentTransaction, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    idempotency_key = models.CharField(max_length=120, blank=True, default="")
    raw_payload = models.JSONField(default=dict, blank=True)
    signature_valid = models.BooleanField(default=False)
    processed = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["idempotency_key"]),
        ]

    def __str__(self):
        return f"{self.transaction_id} {self.event_type}"
