from django.contrib import admin

from nxtbn.home.models import HomeSlide


@admin.register(HomeSlide)
class HomeSlideAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("title", "subtitle")
    raw_id_fields = ("image",)
