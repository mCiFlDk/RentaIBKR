import unittest
from datetime import date, datetime
from decimal import Decimal

from main import CashMovement, analyze_broker_fees, analyze_interest, summarize_foreign_income


def movement(
    *,
    booking_dt: datetime,
    value_date: date,
    product: str,
    isin: str,
    description: str,
    amount_eur: str,
    order_id: str = "",
    currency: str = "EUR",
) -> CashMovement:
    return CashMovement(
        booking_dt=booking_dt,
        value_date=value_date,
        product=product,
        isin=isin,
        description=description,
        currency=currency,
        amount=Decimal(amount_eur),
        amount_eur=Decimal(amount_eur),
        order_id=order_id,
    )


class ForeignIncomeSummaryTests(unittest.TestCase):
    def test_matches_withholding_by_order_id_and_tracks_unmatched(self) -> None:
        dividend = movement(
            booking_dt=datetime(2025, 7, 15, 9, 0),
            value_date=date(2025, 7, 15),
            product="DEMO ENERGY PLC",
            isin="GB1234567890",
            description="Cash dividend",
            amount_eur="12.50",
            order_id="DIV-001",
        )
        matched_withholding = movement(
            booking_dt=datetime(2025, 7, 15, 9, 1),
            value_date=date(2025, 7, 15),
            product="DEMO ENERGY PLC",
            isin="GB1234567890",
            description="Dividend withholding tax",
            amount_eur="-1.90",
            order_id="DIV-001",
        )
        unmatched_withholding = movement(
            booking_dt=datetime(2025, 8, 1, 9, 0),
            value_date=date(2025, 8, 1),
            product="UNKNOWN",
            isin="",
            description="Dividend withholding tax",
            amount_eur="-0.40",
            order_id="OTHER",
        )

        summary = summarize_foreign_income([dividend], [], [matched_withholding, unmatched_withholding], Decimal("0.19"))

        self.assertEqual(summary.gross_income_eur, Decimal("12.50"))
        self.assertEqual(summary.foreign_tax_paid_eur, Decimal("1.90"))
        self.assertEqual(summary.unmatched_foreign_tax_paid_eur, Decimal("0.40"))
        self.assertEqual(summary.estimated_spanish_quota_limit_eur, Decimal("2.3750"))
        self.assertEqual(summary.estimated_deductible_foreign_tax_eur, Decimal("1.90"))

    def test_matches_withholding_by_isin_product_and_near_date_when_order_id_missing(self) -> None:
        dividend = movement(
            booking_dt=datetime(2025, 5, 10, 8, 30),
            value_date=date(2025, 5, 10),
            product="ACME INC",
            isin="US9999999999",
            description="Cash dividend",
            amount_eur="20.00",
        )
        withholding = movement(
            booking_dt=datetime(2025, 5, 11, 8, 45),
            value_date=date(2025, 5, 11),
            product="ACME INC",
            isin="US9999999999",
            description="Dividend withholding tax",
            amount_eur="-3.00",
        )

        summary = summarize_foreign_income([dividend], [], [withholding], None)

        self.assertEqual(summary.gross_income_eur, Decimal("20.00"))
        self.assertEqual(summary.foreign_tax_paid_eur, Decimal("3.00"))
        self.assertEqual(summary.unmatched_foreign_tax_paid_eur, Decimal("0"))
        self.assertIsNone(summary.estimated_spanish_quota_limit_eur)
        self.assertIsNone(summary.estimated_deductible_foreign_tax_eur)

    def test_ignores_spanish_withholding_for_foreign_tax_summary(self) -> None:
        dividend = movement(
            booking_dt=datetime(2025, 4, 1, 9, 0),
            value_date=date(2025, 4, 1),
            product="ACME ESPANA SA",
            isin="ES1234567890",
            description="Cash dividend",
            amount_eur="10.00",
            order_id="DIV-ES",
        )
        withholding = movement(
            booking_dt=datetime(2025, 4, 1, 9, 1),
            value_date=date(2025, 4, 1),
            product="ACME ESPANA SA",
            isin="ES1234567890",
            description="Dividend withholding tax",
            amount_eur="-1.90",
            order_id="DIV-ES",
        )

        summary = summarize_foreign_income([dividend], [], [withholding], Decimal("0.19"))

        self.assertEqual(summary.gross_income_eur, Decimal("0"))
        self.assertEqual(summary.foreign_tax_paid_eur, Decimal("0"))
        self.assertEqual(summary.unmatched_foreign_tax_paid_eur, Decimal("0"))

    def test_negative_interest_is_not_capital_income(self) -> None:
        negative_interest = movement(
            booking_dt=datetime(2025, 3, 1, 9, 0),
            value_date=date(2025, 3, 1),
            product="Cuenta",
            isin="",
            description="Margin interest",
            amount_eur="-2.50",
        )
        positive_interest = movement(
            booking_dt=datetime(2025, 3, 2, 9, 0),
            value_date=date(2025, 3, 2),
            product="Cuenta",
            isin="",
            description="Cash interest",
            amount_eur="0.75",
        )

        interests = analyze_interest([negative_interest, positive_interest], 2025)
        broker_fees = analyze_broker_fees([negative_interest, positive_interest], 2025, set())

        self.assertEqual(interests, [positive_interest])
        self.assertEqual(broker_fees.non_deductible_broker_fees, [negative_interest])


if __name__ == "__main__":
    unittest.main()
