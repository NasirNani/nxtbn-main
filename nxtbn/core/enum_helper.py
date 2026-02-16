from django.db import models

class WeightUnits(models.TextChoices):
    GRAM = 'GRAM', 'Gram'
    KILOGRAM = 'KG', 'Kilogram'
    POUND = 'LB', 'Libre'
    OUNCE = 'OZ', 'Ons'
    TON = 'TON', 'Ton'


class ProductType(models.TextChoices):
    SIMPLE_PRODUCT = 'SIMPLE_PRODUCT', 'Basit Urun'
    GROUPED_PRODUCT = 'GROUPED_PRODUCT', 'Hizmet'
    EXTERNAL_PRODUCT = 'EXTERNAL_PRODUCT', 'Harici/Ortaklik Urunu'
    VARIABLE_PRODUCT = 'VARIABLE_PRODUCT', 'Varyantli Urun'
    SIMPLE_SUBSCRIPTION = 'SIMPLE_SUBSCRIPTION', 'Basit Abonelik'
    VARIABLE_SUBSCRIPTION = 'VARIABLE_SUBSCRIPTION', 'Varyantli Abonelik'
    PRODUCT_BUNDLE = 'PRODUCT_BUNDLE', 'Urun Paketi'

class StockStatus(models.TextChoices):
        IN_STOCK = 'IN_STOCK', 'Stokta'
        OUT_OF_STOCK = 'OUT_OF_STOCK', 'Stokta Yok'
