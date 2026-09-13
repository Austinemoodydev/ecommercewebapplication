from decimal import (
    Decimal,
    ROUND_HALF_UP,
)


ZERO = Decimal("0.00")
HUNDRED = Decimal("100")
MONEY = Decimal("0.01")


def money(
    value,
):

    return Decimal(
        value or ZERO
    ).quantize(
        MONEY,
        rounding=ROUND_HALF_UP,
    )


def calculate_order_pricing(
    *,
    subtotal,
    shipping_cost=ZERO,
    discount=ZERO,
    tax_enabled=False,
    tax_rate=ZERO,
):

    subtotal = money(
        subtotal
    )

    shipping_cost = money(
        shipping_cost
    )

    discount = money(
        discount
    )

    tax_rate = Decimal(
        tax_rate or ZERO
    )


    # Never allow a discount to produce
    # a negative taxable merchandise value.
    taxable_amount = (
        subtotal
        - discount
    )


    if taxable_amount < ZERO:

        taxable_amount = ZERO


    tax_amount = ZERO


    if (
        tax_enabled
        and tax_rate > ZERO
    ):

        tax_amount = money(
            taxable_amount
            * tax_rate
            / HUNDRED
        )


    total_amount = money(
        taxable_amount
        + tax_amount
        + shipping_cost
    )


    return {

        "subtotal":
            subtotal,

        "discount":
            discount,

        "taxable_amount":
            taxable_amount,

        "tax_rate":
            tax_rate,

        "tax_amount":
            tax_amount,

        "shipping_cost":
            shipping_cost,

        "total_amount":
            total_amount,
    }


def minimum_order_satisfied(
    *,
    subtotal,
    minimum_order_amount,
):

    return (
        money(
            subtotal
        )
        >=
        money(
            minimum_order_amount
        )
    )


def total_from_order_snapshot(
    order,
    *,
    shipping_cost=None,
):

    """
    Recalculate total using historical order
    financial values.

    Important:
    Never read the current StoreSettings tax
    rate here. The order's tax_amount is already
    its historical tax snapshot.
    """

    if shipping_cost is None:

        shipping_cost = (
            order.shipping_cost
        )


    taxable_amount = (
        money(
            order.subtotal
        )
        -
        money(
            order.discount
        )
    )


    if taxable_amount < ZERO:

        taxable_amount = ZERO


    return money(
        taxable_amount
        + money(
            order.tax_amount
        )
        + money(
            shipping_cost
        )
    )
