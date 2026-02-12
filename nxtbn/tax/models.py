from django.db import models

from nxtbn.core.models import AbstractBaseModel


class TaxRule(AbstractBaseModel):
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=100, blank=True, null=True)
    rate = models.DecimalField(max_digits=5, decimal_places=4, help_text="Tax rate in decimal format, e.g. 0.20")
    is_active = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("priority", "-created_at")

    def __str__(self):
        return f"{self.name} ({self.rate})"
