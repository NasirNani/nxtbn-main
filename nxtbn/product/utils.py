from nxtbn.core.enum_helper import StockStatus


def is_variant_available(variant, quantity=1):
    if variant is None:
        return False

    quantity = max(1, int(quantity))
    if variant.track_inventory:
        return variant.stock >= quantity

    return variant.stock_status == StockStatus.IN_STOCK


def resolve_product_card_image(product):
    """
    Resolve best available card image:
    1) default variant image
    2) first image from any other variant
    """
    checked_variant_ids = set()
    ordered_variants = []

    if getattr(product, "default_variant", None):
        ordered_variants.append(product.default_variant)
        checked_variant_ids.add(product.default_variant_id)

    for variant in product.variants.all():
        if variant.id in checked_variant_ids:
            continue
        ordered_variants.append(variant)

    for variant in ordered_variants:
        image = variant.variant_image.first()
        if image:
            return image
    return None
