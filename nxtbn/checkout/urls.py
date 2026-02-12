from django.urls import path

from . import views

urlpatterns = [
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<uuid:variant_id>/", views.cart_add, name="cart_add"),
    path("cart/update/<uuid:variant_id>/", views.cart_update, name="cart_update"),
    path("cart/remove/<uuid:variant_id>/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout_view, name="checkout"),
]
