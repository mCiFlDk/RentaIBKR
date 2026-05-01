import tempfile
import unittest
from pathlib import Path

from main import EcbRateProvider, build_analysis, d, parse_ibkr_reports


class ParsingAndHistoryTests(unittest.TestCase):
    def test_parse_ibkr_report_accepts_semicolon_delimited_csv(self) -> None:
        path = Path(tempfile.gettempdir()) / "ibkr_semicolon_report.csv"
        path.write_text(
            "Operaciones;Header;DataDiscriminator;Categoría de activo;Divisa;Símbolo;Fecha/Hora;Cantidad;Precio trans.;Precio de cier.;Productos;Tarifa/com.;Básico;PyG realizadas;MTM P/G;Código\n"
            "Operaciones;Data;Order;Acciones;EUR;ACME;2025-01-10, 09:30:00;1;10;10;-10;0;10;0;0;O\n"
            "Información de instrumento financiero;Header;Categoría de activo;Símbolo;Descripción;Conid;Id. de seguridad;Underlying;Merc. de cotización;Multiplicador;Tipo;Código\n"
            "Información de instrumento financiero;Data;Acciones;ACME;ACME INC;1;US1234567890;ACME;NYSE;1;COMMON;\n",
            encoding="utf-8",
        )

        trades, cash_movements, instruments, ecb_rates_used, ibkr_rates_used = parse_ibkr_reports([path], EcbRateProvider())

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].isin, "US1234567890")
        self.assertEqual(cash_movements, [])
        self.assertIn("ACME", instruments)
        self.assertEqual(ecb_rates_used, 0)
        self.assertEqual(ibkr_rates_used, 0)

    def test_parse_ibkr_report_rejects_empty_parse(self) -> None:
        path = Path(tempfile.gettempdir()) / "ibkr_invalid_report.csv"
        path.write_text("Statement,Header,Nombre del campo,Valor del campo\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "No se ha podido leer ninguna operacion"):
            parse_ibkr_reports([path], EcbRateProvider())

    def test_decimal_parser_handles_ibkr_thousands_quantities(self) -> None:
        self.assertEqual(d("1,200"), d("1200"))
        self.assertEqual(d("12,34"), d("12.34"))

    def test_history_end_date_tracks_whether_user_declared_it(self) -> None:
        analysis = build_analysis(
            [Path("examples/demo_ibkr_2025.csv")],
            2025,
            history_end_date=None,
        )

        self.assertFalse(analysis.history_end_date_declared)
        self.assertIsNotNone(analysis.history_end_date)


if __name__ == "__main__":
    unittest.main()
