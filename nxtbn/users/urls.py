from django.urls import path

from nxtbn.users import views

urlpatterns = [
    path("profile/", views.account_dashboard, name="account_profiles"),
    path("panel/", views.account_dashboard, name="account_dashboard"),
    path("addresses/", views.account_addresses, name="account_addresses"),
    path("addresses/add/", views.account_address_add, name="account_address_add"),
    path("addresses/<uuid:address_id>/edit/", views.account_address_edit, name="account_address_edit"),
    path("addresses/<uuid:address_id>/delete/", views.account_address_delete, name="account_address_delete"),
    path(
        "addresses/<uuid:address_id>/default-shipping/",
        views.account_address_default_shipping,
        name="account_address_default_shipping",
    ),
    path(
        "addresses/<uuid:address_id>/default-billing/",
        views.account_address_default_billing,
        name="account_address_default_billing",
    ),
    path("orders/", views.account_orders, name="account_orders"),
    path("reviews/", views.account_reviews, name="account_reviews"),
    path("security/", views.account_security, name="account_security"),
]
