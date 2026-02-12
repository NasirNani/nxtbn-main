
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model

from nxtbn.users.models import CustomerAddress

User = get_user_model()


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    fieldsets = (("User", {"fields": ('avatar',)}),) + auth_admin.UserAdmin.fieldsets
    list_display = ["username", "first_name", "email", "is_superuser", "is_active", "is_staff",]
    search_fields = ["first_name", "email",]


@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
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
    list_filter = ("is_default_shipping", "is_default_billing", "is_active", "city", "district")
    search_fields = ("full_name", "label", "city", "district", "postal_code", "user__email", "user__username")
