from django.contrib import admin

from nxtbn.core.admin_mixins import AutoUserStampMixin, OpsAdminMixin
from .models import Document, Image


@admin.register(Image)
class ImageAdmin(AutoUserStampMixin, OpsAdminMixin, admin.ModelAdmin):
    list_display = ("name", "created_by", "last_modified_by", "created_at")
    list_filter = ("created_at",)
    search_fields = ("id", "name", "image_alt_text")
    exclude = ("created_by", "last_modified_by")
    readonly_fields = ("id", "created_at", "last_modified")
    fieldsets = (
        ("Medya", {"fields": ("name", "image", "image_alt_text")}),
        ("Kayit", {"fields": ("id", "created_at", "last_modified"), "classes": ("collapse",)}),
    )


@admin.register(Document)
class DocumentAdmin(AutoUserStampMixin, OpsAdminMixin, admin.ModelAdmin):
    list_display = ("name", "created_by", "last_modified_by", "created_at")
    list_filter = ("created_at",)
    search_fields = ("id", "name", "image_alt_text")
    exclude = ("created_by", "last_modified_by")
    readonly_fields = ("id", "created_at", "last_modified")
    fieldsets = (
        ("Dokuman", {"fields": ("name", "document", "image_alt_text")}),
        ("Kayit", {"fields": ("id", "created_at", "last_modified"), "classes": ("collapse",)}),
    )
