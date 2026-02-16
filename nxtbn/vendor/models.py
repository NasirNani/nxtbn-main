from django.db import models
from nxtbn.core.models import AbstractBaseModel

class Vendor(AbstractBaseModel):
    name = models.CharField(max_length=100, verbose_name="Ad")
    contact_info = models.TextField(blank=True)

    class Meta:
        verbose_name = "Tedarikci"
        verbose_name_plural = "Tedarikciler"

    def __str__(self):
        return self.name
