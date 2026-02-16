from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from nxtbn.core.admin_mixins import OpsAdminMixin
from .models import Vendor


@admin.register(Vendor)
class VendorAdmin(OpsAdminMixin, admin.ModelAdmin):
    add_form_template = "admin/vendor/vendor/add_form.html"
    list_display = ("name", "created_at", "last_modified")
    list_filter = ("created_at",)
    search_fields = ("id", "name", "contact_info")
    readonly_fields = ("id", "created_at", "last_modified")
    fieldsets = (
        ("Tedarikci", {"fields": ("name", "contact_info")}),
        ("Kayit", {"fields": ("id", "created_at", "last_modified"), "classes": ("collapse",)}),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        is_turkish = (request.LANGUAGE_CODE or "").startswith("tr")
        if "name" in form.base_fields:
            form.base_fields["name"].label = _("Ad") if is_turkish else _("Name")
        if "contact_info" in form.base_fields:
            form.base_fields["contact_info"].label = _("Iletisim Bilgisi") if is_turkish else _("Contact Info")
        return form
