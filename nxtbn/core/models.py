import uuid
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


class AbstractBaseUUIDModel(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)

    class Meta:
        abstract = True


class AbstractBaseModel(AbstractBaseUUIDModel):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Olusturulma Tarihi")
    last_modified = models.DateTimeField(auto_now=True, verbose_name="Son Guncellenme Tarihi")

    class Meta:
        abstract = True


class PublishableModel(AbstractBaseModel):
    published_date = models.DateTimeField(blank=True, null=True, verbose_name="Yayin Tarihi")
    is_live = models.BooleanField(default=False, verbose_name="Yayinda")

    def make_live(self):
        if not self.published_date:
            self.published_date = timezone.now()
        self.is_live = True
        self.save()

    def make_inactive(self):
        self.is_live = False
        self.published_date = None
        self.save()

    def clean(self):

        if self.is_live and not self.published_date:
            raise ValidationError("Published content must have a publication date.")

    class Meta:
        abstract = True


class SEOMixin:
    meta_title = models.CharField(
        max_length=800, blank=True, null=True, help_text="Arama motoru optimizasyonu icin baslik."
    )
    meta_description = models.CharField(
        max_length=350, blank=True, null=True, help_text="Arama motorlari icin aciklama."
    )

    class Meta:
        abstract = True
        verbose_name = "SEO Bilgisi"
        verbose_name_plural = "SEO Bilgisi"
