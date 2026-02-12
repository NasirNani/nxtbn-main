from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q

from nxtbn.core.models import AbstractBaseModel

class User(AbstractUser):
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)


class CustomerAddress(AbstractBaseModel):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=50, blank=True, default="")
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30, blank=True, default="")
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True, default="")
    address_line1 = models.CharField(max_length=180)
    address_line2 = models.CharField(max_length=180, blank=True, default="")
    country = models.CharField(max_length=100, default="Turkiye")
    is_default_shipping = models.BooleanField(default=False)
    is_default_billing = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("-is_default_shipping", "-created_at")
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["city"]),
            models.Index(fields=["district"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(is_default_shipping=True, is_active=True),
                name="unique_default_shipping_address_per_user",
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(is_default_billing=True, is_active=True),
                name="unique_default_billing_address_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.full_name} ({self.city}/{self.district})"
