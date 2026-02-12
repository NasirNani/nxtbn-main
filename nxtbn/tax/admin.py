from django.contrib import admin

from nxtbn.tax.models import TaxRule


@admin.register(TaxRule)
class TaxRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "rate", "priority", "is_active")
    list_filter = ("is_active", "category")
    search_fields = ("name", "category")
