import re
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils.text import slugify

from nxtbn.core.enum_helper import ProductType, StockStatus, WeightUnits
from nxtbn.core.models import PublishableModel, SEOMixin, AbstractBaseUUIDModel, AbstractBaseModel
from nxtbn.filemanager.models import Document, Image
from nxtbn.vendor.models import Vendor


def _normalize_text(value):
    return re.sub(r"\s+", " ", (value or "").strip())


class Category(AbstractBaseModel):
    name = models.CharField(max_length=100, unique=True, verbose_name="Kategori Adi")
    slug = models.SlugField(max_length=120, unique=True, verbose_name="Slug")
    is_active = models.BooleanField(default=True, verbose_name="Aktif")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Siralama")

    class Meta:
        verbose_name = "Kategori"
        verbose_name_plural = "Kategoriler"
        ordering = ("sort_order", "name")
        constraints = [
            models.UniqueConstraint(Lower("name"), name="product_category_name_ci_unique"),
        ]

    def __str__(self):
        return self.name

    @staticmethod
    def normalize_name(value):
        return _normalize_text(value)

    @classmethod
    def _build_unique_slug(cls, value, *, exclude_pk=None):
        base_slug = (slugify(value) or "kategori")[:100]
        candidate = base_slug
        index = 2
        queryset = cls.objects.all()
        if exclude_pk:
            queryset = queryset.exclude(pk=exclude_pk)
        while queryset.filter(slug=candidate).exists():
            suffix = f"-{index}"
            candidate = f"{base_slug[: 120 - len(suffix)]}{suffix}"
            index += 1
        return candidate

    @classmethod
    def resolve_from_name(cls, value, *, create=False):
        normalized = cls.normalize_name(value)
        if not normalized:
            return None

        existing = cls.objects.filter(name__iexact=normalized).order_by("name").first()
        if existing:
            return existing
        if not create:
            return None
        return cls.objects.create(name=normalized, slug=cls._build_unique_slug(normalized))

    def save(self, *args, **kwargs):
        self.name = self.normalize_name(self.name)
        if not self.name:
            raise ValidationError("Category name cannot be empty.")
        self.slug = self._build_unique_slug(self.slug or self.name, exclude_pk=self.pk)
        super().save(*args, **kwargs)


class Product(PublishableModel, SEOMixin):
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='products_created')
    last_modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='products_modified', null=True, blank=True)
    name = models.CharField(max_length=255)
    summary = models.TextField(max_length=500)
    description = models.TextField(max_length=500)
    media = models.ManyToManyField(Document, blank=True)
    category = models.CharField(max_length=100, blank=True, null=True, verbose_name="Kategori")
    category_ref = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name="products",
        blank=True,
        null=True,
        verbose_name="Kategori",
    )
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name='+')
    brand = models.CharField(max_length=100, blank=True, null=True, verbose_name="Marka")
    type = models.CharField(max_length=25, default=ProductType.SIMPLE_PRODUCT, choices=ProductType.choices, verbose_name="Urun Turu")
    subscribable = models.BooleanField(verbose_name="Abonelige Uygun", default=True)
    related_to = models.ManyToManyField("self", blank=True)
    currency = models.CharField(verbose_name="Para Birimi", default="TRY", max_length=10)
    default_variant = models.OneToOneField(
        "ProductVariant",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    class Meta:
        verbose_name = "Urun"
        verbose_name_plural = "Urunler"

    def __str__(self):
        return self.name

    @property
    def effective_category(self):
        if self.category_ref_id and self.category_ref:
            return self.category_ref.name
        return _normalize_text(self.category) or ""

    def _sync_category_compatibility(self):
        if self.category_ref_id:
            self.category = _normalize_text(getattr(self.category_ref, "name", "")) or None
            return

        normalized_text = _normalize_text(self.category)
        self.category = normalized_text or None
        if normalized_text:
            self.category_ref = Category.resolve_from_name(normalized_text, create=True)

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        self.currency = "TRY"
        self._sync_category_compatibility()
        if update_fields is not None:
            update_fields_set = set(update_fields)
            if "category_ref" in update_fields_set or "category" in update_fields_set:
                update_fields_set.update({"category_ref", "category"})
            update_fields_set.add("currency")
            kwargs["update_fields"] = tuple(update_fields_set)
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
    stock = models.IntegerField(default=0, verbose_name="Stok")
    low_stock_threshold = models.IntegerField(default=0, verbose_name="Dusuk Stok Esigi")

    # if track_inventory is not enabled
    stock_status = models.CharField(default=StockStatus.IN_STOCK, choices=StockStatus.choices, max_length=15, verbose_name="Stok Durumu")


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
        (STATUS_PENDING, "Beklemede"),
        (STATUS_APPROVED, "Onaylandi"),
        (STATUS_HIDDEN, "Gizli"),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="product_reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    comment = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_APPROVED, verbose_name="Durum")
    report_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=["product", "user"], name="unique_product_review_per_user"),
            models.CheckConstraint(check=models.Q(rating__gte=1) & models.Q(rating__lte=5), name="rating_between_1_and_5"),
        ]

    def __str__(self):
        return f"{self.product.name} review by {self.user}"
