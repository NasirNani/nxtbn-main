from django.contrib import admin

from .models import Document, Image


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "last_modified_by", "created_at")
    search_fields = ("name", "image_alt_text")
    exclude = ("created_by", "last_modified_by")

    def save_model(self, request, obj, form, change):
        if not change or obj.created_by_id is None:
            obj.created_by = request.user
        obj.last_modified_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "last_modified_by", "created_at")
    search_fields = ("name", "image_alt_text")
    exclude = ("created_by", "last_modified_by")

    def save_model(self, request, obj, form, change):
        if not change or obj.created_by_id is None:
            obj.created_by = request.user
        obj.last_modified_by = request.user
        super().save_model(request, obj, form, change)
