from django.db import transaction

from products.models import Product, ProductVariant

from .models import InventoryMovement


class InventoryAdjustmentError(Exception):
    pass


INBOUND_TYPES = {
    "restock",
    "adjustment_in",
    "return",
}

OUTBOUND_TYPES = {
    "adjustment_out",
    "damaged",
}


def record_inventory_movement(
    *,
    product=None,
    variant=None,
    movement_type,
    quantity,
    stock_before,
    stock_after,
    reference="",
    notes="",
    user=None,
):

    movement = InventoryMovement(
        product=product,
        variant=variant,
        movement_type=movement_type,
        quantity=quantity,
        stock_before=stock_before,
        stock_after=stock_after,
        reference=reference,
        notes=notes,
        created_by=user,
    )

    movement.full_clean()
    movement.save()

    return movement


@transaction.atomic
def adjust_product_stock(
    *,
    product_id,
    movement_type,
    quantity,
    reference="",
    notes="",
    user=None,
):

    if quantity <= 0:
        raise InventoryAdjustmentError(
            "Quantity must be greater than zero."
        )

    product = (
        Product.objects
        .select_for_update()
        .get(pk=product_id)
    )

    stock_before = product.stock

    if movement_type in INBOUND_TYPES:

        stock_after = (
            stock_before + quantity
        )

    elif movement_type in OUTBOUND_TYPES:

        stock_after = (
            stock_before - quantity
        )

        if stock_after < 0:
            raise InventoryAdjustmentError(
                "There is not enough physical stock "
                "for this adjustment."
            )

        if stock_after < product.reserved_stock:
            raise InventoryAdjustmentError(
                (
                    "This adjustment would reduce "
                    "physical stock below stock already "
                    "reserved by customer orders."
                )
            )

    else:
        raise InventoryAdjustmentError(
            "Unsupported inventory movement type."
        )

    product.stock = stock_after

    product.save(
        update_fields=[
            "stock",
            "updated_at",
        ]
    )

    return record_inventory_movement(
        product=product,
        movement_type=movement_type,
        quantity=quantity,
        stock_before=stock_before,
        stock_after=stock_after,
        reference=reference,
        notes=notes,
        user=user,
    )


@transaction.atomic
def adjust_variant_stock(
    *,
    variant_id,
    movement_type,
    quantity,
    reference="",
    notes="",
    user=None,
):

    if quantity <= 0:
        raise InventoryAdjustmentError(
            "Quantity must be greater than zero."
        )

    variant = (
        ProductVariant.objects
        .select_for_update()
        .select_related("product")
        .get(pk=variant_id)
    )

    stock_before = variant.stock

    if movement_type in INBOUND_TYPES:

        stock_after = (
            stock_before + quantity
        )

    elif movement_type in OUTBOUND_TYPES:

        stock_after = (
            stock_before - quantity
        )

        if stock_after < 0:
            raise InventoryAdjustmentError(
                "There is not enough physical stock "
                "for this adjustment."
            )

        if stock_after < variant.reserved_stock:
            raise InventoryAdjustmentError(
                (
                    "This adjustment would reduce "
                    "physical stock below stock already "
                    "reserved by customer orders."
                )
            )

    else:
        raise InventoryAdjustmentError(
            "Unsupported inventory movement type."
        )

    variant.stock = stock_after

    variant.save(
        update_fields=[
            "stock",
        ]
    )

    return record_inventory_movement(
        variant=variant,
        movement_type=movement_type,
        quantity=quantity,
        stock_before=stock_before,
        stock_after=stock_after,
        reference=reference,
        notes=notes,
        user=user,
    )
