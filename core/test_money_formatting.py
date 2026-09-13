from decimal import Decimal

from django.template import (
    Context,
    Template,
)
from django.test import SimpleTestCase

from core.templatetags.money import money
from dashboard.forms import (
    AdminProductForm,
    AdminProductVariantForm,
    normalize_retail_price,
)


class MoneyFormattingTests(
    SimpleTestCase
):

    def test_whole_shillings_hide_decimal_places(
        self
    ):

        self.assertEqual(
            money(
                Decimal("75000.00")
            ),
            "75,000",
        )


    def test_fractional_money_keeps_two_decimals(
        self
    ):

        self.assertEqual(
            money(
                Decimal("74999.50")
            ),
            "74,999.50",
        )


    def test_large_money_has_grouping(
        self
    ):

        self.assertEqual(
            money(
                Decimal("1250000.00")
            ),
            "1,250,000",
        )


    def test_template_filter_is_available_globally(
        self
    ):

        output = Template(
            "{{ amount|money }}"
        ).render(
            Context(
                {
                    "amount": (
                        Decimal(
                            "75000.00"
                        )
                    )
                }
            )
        )

        self.assertEqual(
            output,
            "75,000",
        )


class RetailPriceNormalizationTests(
    SimpleTestCase
):

    def test_retail_price_rounds_to_nearest_shilling(
        self
    ):

        self.assertEqual(
            normalize_retail_price(
                Decimal(
                    "74999.98"
                )
            ),
            Decimal(
                "75000"
            ),
        )


    def test_retail_price_rounds_down_when_appropriate(
        self
    ):

        self.assertEqual(
            normalize_retail_price(
                Decimal(
                    "74999.20"
                )
            ),
            Decimal(
                "74999"
            ),
        )


    def test_product_price_input_uses_whole_shillings(
        self
    ):

        self.assertEqual(
            AdminProductForm
            .base_fields[
                "price"
            ]
            .widget
            .attrs[
                "step"
            ],
            "1",
        )


    def test_sale_price_input_uses_whole_shillings(
        self
    ):

        self.assertEqual(
            AdminProductForm
            .base_fields[
                "discount_price"
            ]
            .widget
            .attrs[
                "step"
            ],
            "1",
        )


    def test_variant_price_input_uses_whole_shillings(
        self
    ):

        self.assertEqual(
            AdminProductVariantForm
            .base_fields[
                "price"
            ]
            .widget
            .attrs[
                "step"
            ],
            "1",
        )
