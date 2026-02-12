from django.urls import path

from . import views


urlpatterns = [
    path("start/<uuid:transaction_id>/", views.payment_start, name="payment_start"),
    path("failed/<uuid:transaction_id>/", views.payment_failed, name="payment_failed"),
    path("simulate/<uuid:transaction_id>/", views.payment_simulate, name="payment_simulate"),
    path("paytr/callback/", views.paytr_callback, name="paytr_callback"),
]
