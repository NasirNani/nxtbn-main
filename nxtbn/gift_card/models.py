from django.db import models
from django.utils import timezone

from nxtbn.core.models import AbstractBaseModel


class GiftCard(AbstractBaseModel):
    code = models.CharField(max_length=40, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="TRY")
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.code

    @property
    def is_expired(self):
        return self.expires_at is not None and timezone.now() > self.expires_at

    def is_usable(self):
        return self.is_active and not self.is_expired and self.balance > 0


class GiftCardTransaction(AbstractBaseModel):
    TYPE_ISSUE = "issue"
    TYPE_REDEEM = "redeem"
    TYPE_REFUND = "refund"
    TYPE_CHOICES = [
        (TYPE_ISSUE, "Issue"),
        (TYPE_REDEEM, "Redeem"),
        (TYPE_REFUND, "Refund"),
    ]

    gift_card = models.ForeignKey(GiftCard, on_delete=models.CASCADE, related_name="transactions")
    order = models.ForeignKey("order.Order", null=True, blank=True, on_delete=models.SET_NULL, related_name="gift_card_transactions")
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return f"{self.gift_card.code} {self.transaction_type} {self.amount}"
