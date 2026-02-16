from django.db import models
from django.utils import timezone

from nxtbn.core.models import AbstractBaseModel


class Invoice(AbstractBaseModel):
    STATUS_DRAFT = "draft"
    STATUS_ISSUED = "issued"
    STATUS_PAID = "paid"
    STATUS_VOID = "void"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Taslak"),
        (STATUS_ISSUED, "Duzenlendi"),
        (STATUS_PAID, "Odendi"),
        (STATUS_VOID, "Iptal"),
    ]

    order = models.OneToOneField("order.Order", on_delete=models.CASCADE, related_name="invoice")
    number = models.CharField(max_length=30, unique=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_ISSUED, verbose_name="Durum")
    issued_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Fatura"
        verbose_name_plural = "Faturalar"

    def __str__(self):
        return self.number

    def save(self, *args, **kwargs):
        if not self.number:
            base = f"INV-{timezone.now():%Y%m%d}-{str(self.order_id).split('-')[0].upper()}"
            number = base
            suffix = 1
            while Invoice.objects.filter(number=number).exclude(id=self.id).exists():
                suffix += 1
                number = f"{base}-{suffix}"
            self.number = number
        super().save(*args, **kwargs)
