from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid
from django.utils.text import slugify
from django.conf import settings

from nxtbn.core.enum_helper import ProductType, StockStatus, WeightUnits
from nxtbn.core.models import PublishableModel, SEOMixin, AbstractBaseUUIDModel, AbstractBaseModel
from nxtbn.filemanager.models import Document, Image
from nxtbn.vendor.models import Vendor



class Product(PublishableModel, SEOMixin):
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='products_created')
    last_modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='products_modified', null=True, blank=True)
    name = models.CharField(max_length=255)
    summary = models.TextField(max_length=500)
    description = models.TextField(max_length=500)
    media = models.ManyToManyField(Document, blank=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name='+')
    brand = models.CharField(max_length=100, blank=True, null=True)
    type = models.CharField(max_length=25, default=ProductType.SIMPLE_PRODUCT, choices=ProductType.choices)
    subscribable = models.BooleanField(verbose_name="Subscribable", default=True)
    related_to = models.ManyToManyField("self", blank=True)
    currency = models.CharField(verbose_name="Currency", default="TRY", max_length=10)
    default_variant = models.OneToOneField(
        "ProductVariant",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.currency = "TRY"
        super().save(*args, **kwargs)


class ProductVariant(AbstractBaseUUIDModel):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    variant_image = models.ManyToManyField(Image, blank=True)
    name = models.CharField(max_length=255, blank=True, null=True)

    compare_at_price = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal('0.01'))])
    price = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal('0.01'))])
    cost_per_unit = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.01"))],
        default=Decimal("0.01"),
    )

  
    track_inventory = models.BooleanField(default=True)

    # if track_inventory is enabled
    stock = models.IntegerField(default=0, verbose_name="Stock")
    low_stock_threshold = models.IntegerField(default=0, verbose_name="Stock")

    # if track_inventory is not enabled
    stock_status = models.CharField(default=StockStatus.IN_STOCK, choices=StockStatus.choices, max_length=15)


    sku = models.CharField(max_length=50, unique=True, blank=True, null=True, default=None)
    weight_unit = models.CharField(
        max_length=5,
        choices=WeightUnits.choices,
        blank=True,
        null=True
    )
    weight_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    def __str__(self):
        variant_name = self.name if self.name else 'Default'
        return f"{self.product.name} - {variant_name} (SKU: {self.sku})"

    def _generate_sku(self):
        base_name = self.name or self.product.name or "item"
        prefix = slugify(base_name).upper().replace("-", "")
        if not prefix:
            prefix = "ITEM"
        prefix = prefix[:18]

        while True:
            suffix = uuid.uuid4().hex[:8].upper()
            candidate = f"{prefix}-{suffix}"[:50]
            if not ProductVariant.objects.filter(sku=candidate).exists():
                return candidate

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = self._generate_sku()
        super().save(*args, **kwargs)


class ProductReview(AbstractBaseModel):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_HIDDEN = "hidden"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_HIDDEN, "Hidden"),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="product_reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    comment = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_APPROVED)
    report_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=["product", "user"], name="unique_product_review_per_user"),
            models.CheckConstraint(check=models.Q(rating__gte=1) & models.Q(rating__lte=5), name="rating_between_1_and_5"),
        ]

    def __str__(self):
        return f"{self.product.name} review by {self.user}"
