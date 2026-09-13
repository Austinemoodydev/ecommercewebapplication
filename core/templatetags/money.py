from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_UP,
)

from django import template


register = template.Library()


@register.filter(name="money")
def money(value):
    """
    Format a monetary value for display.

    Examples:

        75000.00
        -> 75,000

        74999.00
        -> 74,999

        74999.50
        -> 74,999.50

        1234567.89
        -> 1,234,567.89

    This filter changes presentation only.
    It does not change database values.
    """

    if value in (
        None,
        "",
    ):
        return "0"

    try:
        amount = Decimal(
            str(value)
        )
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ):
        return value

    amount = amount.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    if (
        amount
        == amount.to_integral_value()
    ):
        return format(
            amount,
            ",.0f",
        )

    return format(
        amount,
        ",.2f",
    )
