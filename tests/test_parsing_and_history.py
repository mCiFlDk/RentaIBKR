import tempfile
import unittest
from pathlib import Path

from main import EcbRateProvider, build_analysis, parse_transactions


class ParsingAndHistoryTests(unittest.TestCase):
    def test_parse_transactions_accepts_semicolon_delimited_csv(self) -> None:
        path = Path(tempfile.gettempdir()) / "degiro_semicolon_transactions.csv"
        path.write_text(
            "Date;Time;Product;ISIN;Exchange;Venue;Quantity;Price;Currency;GrossLocal;LocalTotal;GrossEUR;FXRate;Notes;FeeEUR;TotalEUR;Reserved;OrderID\n"
            "10-01-2025;09:30;ACME INC;US1234567890;;;1;10;EUR;10;;10;;;0;10;;BUY-1\n",
            encoding="utf-8",
        )

        trades, ecb_rates_used, degiro_rates_used = parse_transactions(path, EcbRateProvider())

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].order_id, "BUY-1")
        self.assertEqual(ecb_rates_used, 0)
        self.assertEqual(degiro_rates_used, 0)

    def test_parse_transactions_rejects_empty_parse(self) -> None:
        path = Path(tempfile.gettempdir()) / "degiro_invalid_transactions.csv"
        path.write_text("Date;Time;Product\n10-01-2025;09:30;ACME INC\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "No se ha podido leer ninguna operacion"):
            parse_transactions(path, EcbRateProvider())

    def test_history_end_date_tracks_whether_user_declared_it(self) -> None:
        analysis = build_analysis(
            Path("examples/demo_transactions.csv"),
            Path("examples/demo_account.csv"),
            2025,
            history_end_date=None,
        )

        self.assertFalse(analysis.history_end_date_declared)
        self.assertIsNotNone(analysis.history_end_date)


if __name__ == "__main__":
    unittest.main()
