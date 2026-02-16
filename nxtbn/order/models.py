from django.conf import settings
from django.db import models

from nxtbn.core.models import AbstractBaseModel
from nxtbn.product.models import Product, ProductVariant


class Order(AbstractBaseModel):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_PROCESSING = "processing"
    STATUS_SHIPPED = "shipped"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELLED = "cancelled"
    STATUS_REFUNDED = "refunded"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Beklemede"),
        (STATUS_PAID, "Odendi"),
        (STATUS_PROCESSING, "Isleniyor"),
        (STATUS_SHIPPED, "Kargolandi"),
        (STATUS_DELIVERED, "Teslim Edildi"),
        (STATUS_CANCELLED, "Iptal Edildi"),
        (STATUS_REFUNDED, "Iade Edildi"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    address_line1 = models.CharField(max_length=180)
    address_line2 = models.CharField(max_length=180, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="Turkiye")

    status = models.CharField(max_length=20, default=STATUS_PENDING, choices=STATUS_CHOICES, verbose_name="Durum")
    payment_method = models.CharField(max_length=30, default="cod", verbose_name="Odeme Yontemi")
    payment_reference = models.CharField(max_length=120, blank=True, default="")
    coupon_code = models.CharField(max_length=30, blank=True)
    gift_card_code = models.CharField(max_length=40, blank=True, default="")
    notes = models.TextField(blank=True)
    cancellation_requested = models.BooleanField(default=False)
    cancellation_reason = models.CharField(max_length=255, blank=True, default="")
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    tracking_number = models.CharField(max_length=120, blank=True, default="")
    tracking_url = models.URLField(blank=True, default="")

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Siparis"
        verbose_name_plural = "Siparisler"

    def __str__(self):
        return f"Siparis {self.id} - {self.full_name}"


class OrderItem(AbstractBaseModel):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL)
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.SET_NULL)
    product_name = models.CharField(max_length=255)
    sku = models.CharField(max_length=60)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


class OrderStatusEvent(AbstractBaseModel):
    order = models.ForeignKey(Order, related_name="status_events", on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
    note = models.CharField(max_length=255, blank=True, default="")
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.order_id} -> {self.status}"
