from django.db import models


class MetaGlobal(models.Model):
    regular_menu = models.JSONField()
    mega_menu = models.JSONField()

    uncategorized_footer = models.JSONField()
    categorized_footer = models.JSONField()
    logo = models.ImageField()
    
    metadata = models.JSONField()


class HomeSlide(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True, default="")
    image = models.ForeignKey(
        "filemanager.Image",
        on_delete=models.PROTECT,
        related_name="home_slides",
    )
    cta_label = models.CharField(max_length=60, blank=True, default="")
    cta_url = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")

    def __str__(self):
        return self.title

