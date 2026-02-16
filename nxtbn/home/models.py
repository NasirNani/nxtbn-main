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


class SiteNavText(models.Model):
    KEY_SHOP_ALL = "shop_all"
    KEY_CONTACT = "contact"
    KEY_ABOUT_US = "about_us"
    KEY_MORE_INFO = "more_info"

    KEY_CHOICES = [
        (KEY_SHOP_ALL, "Shop All"),
        (KEY_CONTACT, "Contact"),
        (KEY_ABOUT_US, "About Us"),
        (KEY_MORE_INFO, "More Info"),
    ]

    key = models.CharField(max_length=30, choices=KEY_CHOICES, unique=True, verbose_name="Anahtar")
    label_tr = models.CharField(max_length=120, verbose_name="Turkce Metin")
    label_en = models.CharField(max_length=120, verbose_name="Ingilizce Metin")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Siralama")
    is_active = models.BooleanField(default=True, verbose_name="Aktif")

    class Meta:
        ordering = ("sort_order", "key")
        verbose_name = "Navbar ve Footer Metni"
        verbose_name_plural = "Navbar ve Footer Metinleri"

    def __str__(self):
        return f"{self.get_key_display()} ({self.key})"


class FooterSocialLink(models.Model):
    PLATFORM_FACEBOOK = "facebook"
    PLATFORM_INSTAGRAM = "instagram"
    PLATFORM_X = "x"
    PLATFORM_YOUTUBE = "youtube"
    PLATFORM_LINKEDIN = "linkedin"
    PLATFORM_TIKTOK = "tiktok"

    PLATFORM_CHOICES = [
        (PLATFORM_FACEBOOK, "Facebook"),
        (PLATFORM_INSTAGRAM, "Instagram"),
        (PLATFORM_X, "X"),
        (PLATFORM_YOUTUBE, "YouTube"),
        (PLATFORM_LINKEDIN, "LinkedIn"),
        (PLATFORM_TIKTOK, "TikTok"),
    ]

    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, verbose_name="Platform")
    url = models.URLField(verbose_name="Baglanti")
    label = models.CharField(max_length=120, blank=True, default="", verbose_name="Etiket")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Siralama")
    is_active = models.BooleanField(default=True, verbose_name="Aktif")

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "Sosyal Medya Linki"
        verbose_name_plural = "Sosyal Medya Linkleri"

    def __str__(self):
        return self.label or self.get_platform_display()

