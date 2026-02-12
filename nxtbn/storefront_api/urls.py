from django.urls import path

from . import views


urlpatterns = [
    path("products/", views.products_api, name="api_products"),
    path("products/<uuid:product_id>/", views.product_detail_api, name="api_product_detail"),
    path("products/<uuid:product_id>/reviews/", views.review_create_api, name="api_product_review_create"),
    path("cart/", views.cart_api, name="api_cart"),
    path("orders/", views.orders_api, name="api_orders"),
    path("orders/<uuid:order_id>/", views.order_detail_api, name="api_order_detail"),
    path("account/summary/", views.account_summary_api, name="api_account_summary"),
    path("account/orders/", views.account_orders_api, name="api_account_orders"),
    path("account/reviews/", views.account_reviews_api, name="api_account_reviews"),
    path("account/addresses/", views.account_addresses_api, name="api_account_addresses"),
    path("account/addresses/<uuid:address_id>/", views.account_address_detail_api, name="api_account_address_detail"),
]
