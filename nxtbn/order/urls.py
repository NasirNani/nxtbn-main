from django.urls import path

from . import views

urlpatterns = [
    path("<uuid:order_id>/", views.order_detail, name="order_detail"),
    path("<uuid:order_id>/success/", views.order_success, name="order_success"),
    path("<uuid:order_id>/tracking/", views.order_tracking, name="order_tracking"),
    path("<uuid:order_id>/cancel-request/", views.order_cancel_request, name="order_cancel_request"),
    path("<uuid:order_id>/reorder/", views.reorder, name="order_reorder"),
]
