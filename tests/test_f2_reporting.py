import unittest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from main import Analysis, CarryoverInput, Disposal, build_f2_lines, render_report


def partial_blocked_disposal() -> Disposal:
    return Disposal(
        isin="US1234567890",
        product="DEMO BIOTECH INC",
        sell_dt=datetime(2025, 2, 20, 15, 45),
        quantity=Decimal("100"),
        proceeds_eur=Decimal("799.00"),
        cost_basis_eur=Decimal("1001.00"),
        gain_loss_eur=Decimal("-80.80"),
        order_id="SELL-001",
        gross_proceeds_eur=Decimal("800.00"),
        sell_fee_eur=Decimal("1.00"),
        blocked_loss_eur=Decimal("121.20"),
        replacement_quantity=Decimal("60"),
        fifo_complete=True,
    )


def gain_disposal(*, product: str, isin: str, when: datetime, proceeds: str, cost: str, order_id: str) -> Disposal:
    return Disposal(
        isin=isin,
        product=product,
        sell_dt=when,
        quantity=Decimal("1"),
        proceeds_eur=Decimal(proceeds),
        cost_basis_eur=Decimal(cost),
        gain_loss_eur=Decimal(proceeds) - Decimal(cost),
        order_id=order_id,
        gross_proceeds_eur=Decimal(proceeds),
        sell_fee_eur=Decimal("0"),
        fifo_complete=True,
    )


class F2ReportingTests(unittest.TestCase):
    def test_partial_blocked_disposal_splits_into_two_f2_lines(self) -> None:
        disposal = partial_blocked_disposal()

        f2_lines = build_f2_lines([disposal])

        self.assertEqual(len(f2_lines), 2)
        self.assertEqual(sum((line.integrable_gain_loss_eur for line in f2_lines), Decimal("0")), Decimal("-80.80"))
        self.assertEqual(sum((line.non_computable_loss_eur for line in f2_lines), Decimal("0")), Decimal("121.20"))
        self.assertEqual(sum((line.proceeds_eur for line in f2_lines), Decimal("0")), Decimal("799.00"))
        self.assertEqual(sum((line.acquisition_eur for line in f2_lines), Decimal("0")), Decimal("1001.00"))
        self.assertEqual(sum((Decimal("1") for line in f2_lines if line.check_two_month_rule), Decimal("0")), Decimal("1"))

    def test_render_report_contains_expected_f2_control_totals(self) -> None:
        disposals = [
            partial_blocked_disposal(),
            gain_disposal(
                product="DEMO BIOTECH INC",
                isin="US1234567890",
                when=datetime(2025, 6, 20, 16, 0),
                proceeds="719.00",
                cost="542.20",
                order_id="SELL-002",
            ),
            gain_disposal(
                product="DEMO ENERGY PLC",
                isin="GB1234567890",
                when=datetime(2025, 11, 10, 14, 0),
                proceeds="919.00",
                cost="801.00",
                order_id="SELL-003",
            ),
        ]
        analysis = Analysis(
            trades=[],
            cash_movements=[],
            instruments={},
            report_paths=[Path("ibkr.csv")],
            disposals=disposals,
            open_lots={},
            open_lots_at_year_end={},
            open_lots_at_history_end={},
            warnings=[],
            ecb_rates_used=0,
            ibkr_rates_used=0,
            fx_mode="ecb",
            fx_mode_requested="ecb",
            apply_two_month_rule=True,
            corporate_action_alerts=[],
            history_end_date=date(2026, 2, 28),
            history_end_date_declared=True,
        )

        report = render_report(
            analysis,
            2025,
            [Path("ibkr.csv")],
            CarryoverInput(Decimal("0"), Decimal("0")),
            None,
        )

        self.assertIn("| Suma ganancias integrables acciones negociadas | 294.80 EUR |", report)
        self.assertIn("| Suma pérdidas integrables acciones negociadas | 80.80 EUR |", report)
        self.assertIn("| Resultado neto integrable F2 | 214.00 EUR |", report)
        self.assertIn("| Pérdidas no computables por regla 2M | 121.20 EUR |", report)


if __name__ == "__main__":
    unittest.main()
