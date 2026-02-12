from django.urls import path

from . import views


urlpatterns = [
    path("<uuid:order_id>/download/", views.invoice_download, name="invoice_download"),
]
