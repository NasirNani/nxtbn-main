from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model

from nxtbn.core.admin_mixins import OpsAdminMixin
from nxtbn.users.models import CustomerAddress

User = get_user_model()


@admin.register(User)
class UserAdmin(OpsAdminMixin, auth_admin.UserAdmin):
    fieldsets = (("Kullanici", {"fields": ('avatar',)}),) + auth_admin.UserAdmin.fieldsets
    list_display = ["username", "first_name", "last_name", "email", "is_staff", "is_superuser", "is_active", "date_joined"]
    list_filter = ["is_staff", "is_superuser", "is_active", "date_joined"]
    search_fields = ["username", "first_name", "last_name", "email"]


@admin.register(CustomerAddress)
class CustomerAddressAdmin(OpsAdminMixin, admin.ModelAdmin):
    list_display = (
        "full_name",
        "user",
        "label",
        "city",
        "district",
        "is_default_shipping",
        "is_default_billing",
        "is_active",
        "created_at",
    )
    list_filter = ("is_default_shipping", "is_default_billing", "is_active", "city", "district", "created_at")
    search_fields = ("id", "full_name", "label", "city", "district", "postal_code", "user__email", "user__username")
    autocomplete_fields = ("user",)
    readonly_fields = ("id", "created_at", "last_modified")
    fieldsets = (
        ("Kimlik", {"fields": ("user", "label", "full_name", "phone")}),
        ("Adres", {"fields": ("address_line1", "address_line2", "city", "district", "postal_code", "country")}),
        ("Tercihler", {"fields": ("is_default_shipping", "is_default_billing", "is_active")}),
        ("Kayit", {"fields": ("id", "created_at", "last_modified"), "classes": ("collapse",)}),
    )
