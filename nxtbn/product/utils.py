from nxtbn.core.enum_helper import StockStatus


def is_variant_available(variant, quantity=1):
    if variant is None:
        return False

    quantity = max(1, int(quantity))
    if variant.track_inventory:
        return variant.stock >= quantity

    return variant.stock_status == StockStatus.IN_STOCK
