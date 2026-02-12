from django.db import models
from django.utils import timezone

from nxtbn.core.models import AbstractBaseModel


class Coupon(AbstractBaseModel):
    TYPE_PERCENT = "percent"
    TYPE_FIXED = "fixed"
    DISCOUNT_TYPE_CHOICES = [
        (TYPE_PERCENT, "Percent"),
        (TYPE_FIXED, "Fixed"),
    ]

    code = models.CharField(max_length=40, unique=True)
    discount_type = models.CharField(max_length=12, choices=DISCOUNT_TYPE_CHOICES, default=TYPE_PERCENT)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_discount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.code

    @property
    def is_expired(self):
        return self.ends_at is not None and timezone.now() > self.ends_at

    def is_usable(self, subtotal):
        if not self.is_active or self.is_expired:
            return False
        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            return False
        return subtotal >= self.min_subtotal
