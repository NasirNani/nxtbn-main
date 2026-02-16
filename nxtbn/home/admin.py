from django.contrib import admin

from nxtbn.core.admin_mixins import OpsAdminMixin
from nxtbn.home.models import FooterSocialLink, HomeSlide, SiteNavText


@admin.register(HomeSlide)
class HomeSlideAdmin(OpsAdminMixin, admin.ModelAdmin):
    list_display = ("title", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("id", "title", "subtitle", "cta_label", "cta_url")
    autocomplete_fields = ("image",)
    readonly_fields = ("id",)
    fieldsets = (
        ("Icerik", {"fields": ("title", "subtitle", "image")}),
        ("Aksiyon", {"fields": ("cta_label", "cta_url", "is_active", "sort_order")}),
        ("Kayit", {"fields": ("id",)}),
    )


@admin.register(SiteNavText)
class SiteNavTextAdmin(OpsAdminMixin, admin.ModelAdmin):
    list_display = ("key", "label_tr", "label_en", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("key", "label_tr", "label_en")
    readonly_fields = ("key",)
    ordering = ("sort_order", "key")
    fieldsets = (
        ("Kimlik", {"fields": ("key",)}),
        ("Metin", {"fields": ("label_tr", "label_en", "is_active", "sort_order")}),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FooterSocialLink)
class FooterSocialLinkAdmin(OpsAdminMixin, admin.ModelAdmin):
    list_display = ("platform", "label", "url", "is_active", "sort_order")
    list_filter = ("platform", "is_active")
    search_fields = ("label", "url")
    readonly_fields = ("id",)
    ordering = ("sort_order", "id")
    fieldsets = (
        ("Sosyal Medya", {"fields": ("platform", "label", "url", "is_active", "sort_order")}),
        ("Kayit", {"fields": ("id",)}),
    )
