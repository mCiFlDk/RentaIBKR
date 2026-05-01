from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP, getcontext
from pathlib import Path
from typing import Iterable
from urllib.request import urlopen
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape


getcontext().prec = 28
ECB_XML_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml"
CACHE_DIR = Path(__file__).resolve().parent / ".cache"
CACHE_FILE = CACHE_DIR / "ecb_hist.xml"
CENT = Decimal("0.01")
DEFAULT_REPLACEMENT_WINDOW_MONTHS = 2
REPLACEMENT_WINDOW_MONTHS_BY_ISIN: dict[str, int] = {}


def d(value: str | int | float | Decimal | None) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))

    text = str(value).strip()
    if not text:
        return Decimal("0")

    if "." in text and "," in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        parts = text.split(",")
        looks_like_thousands = (
            len(parts) > 1
            and 1 <= len(parts[0]) <= 3
            and all(len(part) == 3 and part.isdigit() for part in parts[1:])
        )
        if looks_like_thousands:
            text = "".join(parts)
        else:
            text = text.replace(".", "").replace(",", ".")

    return Decimal(text)


def q(value: Decimal) -> str:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP).to_eng_string()


def approx_equal(a: Decimal, b: Decimal, tolerance: Decimal = CENT) -> bool:
    return abs(a - b) <= tolerance


def add_months(original: date, months: int) -> date:
    year = original.year + (original.month - 1 + months) // 12
    month = (original.month - 1 + months) % 12 + 1
    day = min(
        original.day,
        [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1],
    )
    return date(year, month, day)


@dataclass
class Trade:
    order_id: str
    isin: str
    product: str
    trade_dt: datetime
    quantity: Decimal
    price: Decimal
    currency: str
    gross_local: Decimal
    gross_eur: Decimal
    fee_eur: Decimal
    total_eur: Decimal
    side: str
    eur_source: str


@dataclass
class Instrument:
    symbol: str
    isin: str
    description: str
    asset_category: str
    listing_market: str
    instrument_type: str


@dataclass
class Lot:
    isin: str
    product: str
    acquire_dt: datetime
    quantity_open: Decimal
    unit_cost_eur: Decimal
    unit_gross_eur: Decimal
    unit_fee_eur: Decimal
    deferred_loss_unit_eur: Decimal
    deferred_source_year: int | None
    source_order_id: str


@dataclass
class DisposalMatch:
    acquire_dt: datetime
    quantity: Decimal
    cost_eur: Decimal
    gross_cost_eur: Decimal
    fee_cost_eur: Decimal
    deferred_loss_cost_eur: Decimal
    deferred_source_year: int | None


@dataclass
class Disposal:
    isin: str
    product: str
    sell_dt: datetime
    quantity: Decimal
    proceeds_eur: Decimal
    cost_basis_eur: Decimal
    gain_loss_eur: Decimal
    order_id: str
    gross_proceeds_eur: Decimal
    sell_fee_eur: Decimal
    matches: list[DisposalMatch] = field(default_factory=list)
    blocked_loss_eur: Decimal = Decimal("0")
    replacement_quantity: Decimal = Decimal("0")
    fifo_complete: bool = True

    @property
    def embedded_deferred_loss_eur(self) -> Decimal:
        return sum((match.deferred_loss_cost_eur for match in self.matches), Decimal("0"))

    @property
    def tax_result_before_current_block_eur(self) -> Decimal:
        return self.gain_loss_eur - self.blocked_loss_eur

    @property
    def market_result_without_prior_deferred_eur(self) -> Decimal:
        return self.tax_result_before_current_block_eur + self.embedded_deferred_loss_eur

    @property
    def original_gain_loss_eur(self) -> Decimal:
        return self.tax_result_before_current_block_eur

    @property
    def non_computable_current_loss_eur(self) -> Decimal:
        return self.blocked_loss_eur

    @property
    def f2_real_gain_loss_eur(self) -> Decimal:
        return self.tax_result_before_current_block_eur


@dataclass
class F2Line:
    isin: str
    product: str
    sale_label: str
    quantity: Decimal
    proceeds_eur: Decimal
    acquisition_eur: Decimal
    real_gain_loss_eur: Decimal
    non_computable_loss_eur: Decimal
    integrable_gain_loss_eur: Decimal
    check_two_month_rule: bool
    embedded_deferred_loss_eur: Decimal
    source_disposal: Disposal
    note: str


@dataclass
class CashMovement:
    booking_dt: datetime
    value_date: date
    product: str
    isin: str
    description: str
    currency: str
    amount: Decimal
    amount_eur: Decimal
    order_id: str


@dataclass
class DeferredLoss:
    isin: str
    expires_on: date
    quantity_remaining: Decimal
    loss_per_share_eur: Decimal
    source_year: int
    disposal: Disposal


@dataclass
class Analysis:
    trades: list[Trade]
    cash_movements: list[CashMovement]
    instruments: dict[str, Instrument]
    report_paths: list[Path]
    disposals: list[Disposal]
    open_lots: dict[str, list[Lot]]
    open_lots_at_year_end: dict[str, list[Lot]]
    open_lots_at_history_end: dict[str, list[Lot]]
    warnings: list[str]
    ecb_rates_used: int
    ibkr_rates_used: int
    fx_mode: str
    fx_mode_requested: str
    apply_two_month_rule: bool
    corporate_action_alerts: list[str]
    history_end_date: date | None
    history_end_date_declared: bool


@dataclass
class BrokerFeeSummary:
    deductible_admin_fees: list[CashMovement]
    non_deductible_broker_fees: list[CashMovement]
    trade_fee_movements: list[CashMovement]


@dataclass
class SavingsCompensation:
    capital_income_gross: Decimal
    deductible_admin_fees: Decimal
    capital_income_net_before_offset: Decimal
    capital_gains_net_before_offset: Decimal
    capital_income_offset_applied: Decimal
    capital_gains_offset_applied: Decimal
    capital_income_net_after_current_year: Decimal
    capital_gains_net_after_current_year: Decimal
    carry_income_losses_used_same_bucket: Decimal
    carry_gains_losses_used_same_bucket: Decimal
    carry_income_losses_used_cross: Decimal
    carry_gains_losses_used_cross: Decimal
    capital_income_final: Decimal
    capital_gains_final: Decimal


@dataclass
class ForeignIncomeSummary:
    gross_income_eur: Decimal
    foreign_tax_paid_eur: Decimal
    unmatched_foreign_tax_paid_eur: Decimal
    spanish_tax_rate_hint: Decimal | None
    estimated_spanish_quota_limit_eur: Decimal | None
    estimated_deductible_foreign_tax_eur: Decimal | None


@dataclass
class CarryoverInput:
    income_losses: Decimal
    gains_losses: Decimal


class EcbRateProvider:
    def __init__(self) -> None:
        self._rates_by_date: dict[date, dict[str, Decimal]] | None = None

    def get_rate(self, currency: str, when: date) -> Decimal:
        currency = currency.upper()
        if currency == "EUR":
            return Decimal("1")

        rates_by_date = self._load_rates()
        cursor = when
        lower_bound = min(rates_by_date.keys())
        while cursor >= lower_bound:
            daily = rates_by_date.get(cursor)
            if daily and currency in daily:
                return daily[currency]
            cursor -= timedelta(days=1)
        raise ValueError(f"No ECB rate found for {currency} on or before {when.isoformat()}")

    def _load_rates(self) -> dict[date, dict[str, Decimal]]:
        if self._rates_by_date is not None:
            return self._rates_by_date

        xml_bytes = self._read_cached_or_download()
        root = ET.fromstring(xml_bytes)
        ns = {"gesmes": "http://www.gesmes.org/xml/2002-08-01", "def": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}
        rates_by_date: dict[date, dict[str, Decimal]] = {}
        for cube in root.findall(".//def:Cube[@time]", ns):
            day = date.fromisoformat(cube.attrib["time"])
            day_rates: dict[str, Decimal] = {"EUR": Decimal("1")}
            for rate_cube in cube.findall("def:Cube", ns):
                day_rates[rate_cube.attrib["currency"]] = Decimal(rate_cube.attrib["rate"])
            rates_by_date[day] = day_rates
        self._rates_by_date = rates_by_date
        return rates_by_date

    def _read_cached_or_download(self) -> bytes:
        if CACHE_FILE.exists():
            return CACHE_FILE.read_bytes()

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with urlopen(ECB_XML_URL, timeout=30) as response:
            data = response.read()
        CACHE_FILE.write_bytes(data)
        return data


def read_rows(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        first_line = next((line for line in sample.splitlines() if line.strip()), "")
        if first_line.count(";") > first_line.count(","):
            return list(csv.reader(fh, delimiter=";"))
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        except csv.Error:
            dialect = csv.excel
        return list(csv.reader(fh, dialect))


def parse_ibkr_datetime(value: str) -> datetime:
    return datetime.strptime(value.strip(), "%Y-%m-%d, %H:%M:%S")


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value.strip())


def is_total_currency(value: str) -> bool:
    return value.strip().lower() in {"total", "total en eur", "total in eur"}


def extract_symbol_isin(description: str) -> tuple[str, str]:
    match = re.match(r"\s*([A-Z0-9.\- ]+)\(([A-Z]{2}[A-Z0-9]{9,12})\)", description)
    if not match:
        return "", ""
    return match.group(1).strip(), match.group(2).strip()


def generated_order_id(report_path: Path, symbol: str, side: str, currency: str, trade_dt: datetime) -> str:
    return f"{report_path.name}:{symbol}:{side}:{currency}:{trade_dt:%Y%m%d%H%M%S}"


def derive_fee_eur(gross_eur: Decimal, total_eur: Decimal, side: str) -> Decimal:
    if gross_eur == 0 or total_eur == 0:
        return Decimal("0")
    if side == "BUY":
        return max(total_eur - gross_eur, Decimal("0"))
    if side == "SELL":
        return max(gross_eur - total_eur, Decimal("0"))
    return abs(total_eur - gross_eur)


def start_of_day(day: date) -> datetime:
    return datetime.combine(day, time.min)


def end_of_day(day: date) -> datetime:
    return datetime.combine(day, time.max)


def clone_open_lots(lots_by_isin: dict[str, list[Lot]]) -> dict[str, list[Lot]]:
    cloned: dict[str, list[Lot]] = {}
    for isin, lots in lots_by_isin.items():
        copied_lots = [replace(lot) for lot in lots if lot.quantity_open > 0]
        if copied_lots:
            cloned[isin] = copied_lots
    return cloned


def deferred_loss_total(lots_by_isin: dict[str, list[Lot]]) -> Decimal:
    return sum(
        (lot.quantity_open * lot.deferred_loss_unit_eur for lots in lots_by_isin.values() for lot in lots if lot.quantity_open > 0),
        Decimal("0"),
    )


def get_replacement_window_months(isin: str) -> int:
    return REPLACEMENT_WINDOW_MONTHS_BY_ISIN.get(isin, DEFAULT_REPLACEMENT_WINDOW_MONTHS)


def eur_amount_from_report_currency(amount: Decimal, currency: str, when: date, ecb: EcbRateProvider) -> tuple[Decimal, str]:
    if currency.upper() == "EUR":
        return amount, "EUR"
    return amount / ecb.get_rate(currency, when), "ECB"


def parse_ibkr_instruments(report_paths: list[Path]) -> dict[str, Instrument]:
    instruments: dict[str, Instrument] = {}
    for path in report_paths:
        for row in read_rows(path):
            if len(row) < 11:
                continue
            if row[0] != "Información de instrumento financiero" or row[1] != "Data":
                continue
            if row[2].strip() != "Acciones":
                continue
            symbol = row[3].strip()
            if not symbol:
                continue
            instruments[symbol] = Instrument(
                symbol=symbol,
                description=row[4].strip() or symbol,
                isin=row[6].strip() or symbol,
                asset_category=row[2].strip(),
                listing_market=row[8].strip(),
                instrument_type=row[10].strip(),
            )
    return instruments


def parse_ibkr_trade_row(path: Path, row: list[str], instruments: dict[str, Instrument], ecb: EcbRateProvider) -> tuple[Trade, int] | None:
    if len(row) < 16:
        return None
    if row[0] != "Operaciones" or row[1] != "Data" or row[2] != "Order":
        return None
    if row[3].strip() != "Acciones":
        return None

    symbol = row[5].strip()
    trade_dt = parse_ibkr_datetime(row[6])
    quantity_signed = d(row[7])
    if quantity_signed == 0:
        return None

    currency = row[4].strip() or "EUR"
    gross_local_signed = d(row[10])
    fee_local = abs(d(row[11]))
    gross_local = abs(gross_local_signed)
    gross_eur, gross_source = eur_amount_from_report_currency(gross_local, currency, trade_dt.date(), ecb)
    fee_eur, fee_source = eur_amount_from_report_currency(fee_local, currency, trade_dt.date(), ecb)
    ecb_rates_used = int(gross_source == "ECB") + int(fee_source == "ECB" and fee_local != 0)
    side = "BUY" if quantity_signed > 0 else "SELL"
    if side == "BUY":
        total_eur = gross_eur + fee_eur
    else:
        total_eur = max(gross_eur - fee_eur, Decimal("0"))

    instrument = instruments.get(symbol)
    isin = instrument.isin if instrument else symbol
    product = instrument.description if instrument else symbol

    return (
        Trade(
            order_id=generated_order_id(path, symbol, side, currency, trade_dt),
            isin=isin,
            product=product,
            trade_dt=trade_dt,
            quantity=abs(quantity_signed),
            price=d(row[8]),
            currency=currency,
            gross_local=gross_local,
            gross_eur=abs(gross_eur),
            fee_eur=abs(fee_eur),
            total_eur=total_eur,
            side=side,
            eur_source=gross_source,
        ),
        ecb_rates_used,
    )


def parse_ibkr_cash_movement_row(path: Path, row: list[str], instruments: dict[str, Instrument], ecb: EcbRateProvider) -> tuple[CashMovement, int] | None:
    if len(row) < 2 or row[1] != "Data":
        return None

    section = row[0]
    if section == "Dividendos":
        if len(row) < 6 or is_total_currency(row[2]):
            return None
        currency = row[2].strip() or "EUR"
        value_date = parse_iso_date(row[3])
        description = row[4].strip()
        amount = d(row[5])
    elif section == "Retención de impuestos":
        if len(row) < 6 or is_total_currency(row[2]):
            return None
        currency = row[2].strip() or "EUR"
        value_date = parse_iso_date(row[3])
        description = row[4].strip()
        amount = d(row[5])
    elif section == "Tarifas":
        if len(row) < 7 or is_total_currency(row[2]) or is_total_currency(row[3]) or not row[4].strip():
            return None
        currency = row[3].strip() or "EUR"
        value_date = parse_iso_date(row[4])
        description = row[5].strip()
        amount = d(row[6])
    else:
        return None

    amount_eur, source = eur_amount_from_report_currency(amount, currency, value_date, ecb)
    symbol, isin = extract_symbol_isin(description)
    instrument = instruments.get(symbol)
    product = instrument.description if instrument else symbol
    if not isin and instrument:
        isin = instrument.isin

    return (
        CashMovement(
            booking_dt=start_of_day(value_date),
            value_date=value_date,
            product=product,
            isin=isin,
            description=description,
            currency=currency,
            amount=amount,
            amount_eur=amount_eur,
            order_id=f"{path.name}:{section}:{value_date.isoformat()}:{symbol}:{amount}",
        ),
        int(source == "ECB"),
    )


def parse_ibkr_reports(report_paths: list[Path], ecb: EcbRateProvider) -> tuple[list[Trade], list[CashMovement], dict[str, Instrument], int, int]:
    instruments = parse_ibkr_instruments(report_paths)
    trades: list[Trade] = []
    cash_movements: list[CashMovement] = []
    ecb_rates_used = 0
    ibkr_rates_used = 0

    for path in report_paths:
        for row in read_rows(path):
            parsed_trade = parse_ibkr_trade_row(path, row, instruments, ecb)
            if parsed_trade is not None:
                trade, trade_ecb_rates_used = parsed_trade
                trades.append(trade)
                ecb_rates_used += trade_ecb_rates_used
                continue

            parsed_movement = parse_ibkr_cash_movement_row(path, row, instruments, ecb)
            if parsed_movement is not None:
                movement, movement_ecb_rates_used = parsed_movement
                cash_movements.append(movement)
                ecb_rates_used += movement_ecb_rates_used

    trades.sort(key=lambda t: t.trade_dt)
    cash_movements.sort(key=lambda m: m.booking_dt)
    if not trades:
        reports = ", ".join(str(path) for path in report_paths)
        raise ValueError(
            f"No se ha podido leer ninguna operacion de acciones en {reports}. "
            f"Revisa que sean CSV de informes anuales de Interactive Brokers y que incluyan la seccion Operaciones."
        )
    return trades, cash_movements, instruments, ecb_rates_used, ibkr_rates_used


def warn_same_timestamp_mixed_sides(trades: list[Trade]) -> list[str]:
    warnings: list[str] = []
    grouped: dict[tuple[str, datetime], set[str]] = defaultdict(set)

    for trade in trades:
        grouped[(trade.isin, trade.trade_dt)].add(trade.side)

    for (isin, trade_dt), sides in sorted(grouped.items(), key=lambda item: (item[0][1], item[0][0])):
        if len(sides) > 1:
            warnings.append(
                f"Operaciones BUY/SELL con mismo timestamp para {isin} el {trade_dt:%d/%m/%Y %H:%M}. Revisar orden real de ejecucion."
            )

    return warnings


def aggregate_trades(trades: list[Trade]) -> list[Trade]:
    aggregated: list[Trade] = []

    for trade in trades:
        if (
            aggregated
            and trade.order_id
            and trade.order_id == aggregated[-1].order_id
            and trade.side == aggregated[-1].side
            and trade.isin == aggregated[-1].isin
        ):
            previous = aggregated[-1]
            quantity = previous.quantity + trade.quantity
            aggregated[-1] = Trade(
                order_id=previous.order_id,
                isin=previous.isin,
                product=previous.product,
                trade_dt=min(previous.trade_dt, trade.trade_dt),
                quantity=quantity,
                price=((previous.price * previous.quantity) + (trade.price * trade.quantity)) / quantity,
                currency=previous.currency,
                gross_local=previous.gross_local + trade.gross_local,
                gross_eur=previous.gross_eur + trade.gross_eur,
                fee_eur=previous.fee_eur + trade.fee_eur,
                total_eur=previous.total_eur + trade.total_eur,
                side=previous.side,
                eur_source=previous.eur_source if previous.eur_source == trade.eur_source else "MIXED",
            )
            continue

        aggregated.append(trade)

    return aggregated


def apply_future_deferred_losses(
    trade: Trade,
    base_unit_cost: Decimal,
    pending_losses: list[DeferredLoss],
) -> list[Lot]:
    remaining = trade.quantity
    lots: list[Lot] = []
    base_unit_gross = trade.gross_eur / trade.quantity
    base_unit_fee = trade.fee_eur / trade.quantity

    for deferred in pending_losses:
        if remaining == 0:
            break
        if deferred.isin != trade.isin or deferred.quantity_remaining == 0:
            continue
        if trade.trade_dt.date() > deferred.expires_on:
            continue

        matched_qty = min(remaining, deferred.quantity_remaining)
        if matched_qty == 0:
            continue

        lots.append(
            Lot(
                isin=trade.isin,
                product=trade.product,
                acquire_dt=trade.trade_dt,
                quantity_open=matched_qty,
                unit_cost_eur=base_unit_cost + deferred.loss_per_share_eur,
                unit_gross_eur=base_unit_gross,
                unit_fee_eur=base_unit_fee,
                deferred_loss_unit_eur=deferred.loss_per_share_eur,
                deferred_source_year=deferred.source_year,
                source_order_id=trade.order_id,
            )
        )
        deferred.quantity_remaining -= matched_qty
        deferred.disposal.blocked_loss_eur += matched_qty * deferred.loss_per_share_eur
        deferred.disposal.replacement_quantity += matched_qty
        deferred.disposal.gain_loss_eur += matched_qty * deferred.loss_per_share_eur
        remaining -= matched_qty

    if remaining > 0:
        lots.append(
            Lot(
                isin=trade.isin,
                product=trade.product,
                acquire_dt=trade.trade_dt,
                quantity_open=remaining,
                unit_cost_eur=base_unit_cost,
                unit_gross_eur=base_unit_gross,
                unit_fee_eur=base_unit_fee,
                deferred_loss_unit_eur=Decimal("0"),
                deferred_source_year=None,
                source_order_id=trade.order_id,
            )
        )

    return lots


def apply_preexisting_replacements(
    disposal: Disposal,
    open_lots: list[Lot],
) -> Decimal:
    if disposal.tax_result_before_current_block_eur >= 0 or disposal.quantity == 0:
        return Decimal("0")

    loss_per_share = abs(disposal.tax_result_before_current_block_eur) / disposal.quantity
    remaining_replacement_qty = disposal.quantity
    window_start = add_months(disposal.sell_dt.date(), -get_replacement_window_months(disposal.isin))

    lot_index = 0
    while lot_index < len(open_lots) and remaining_replacement_qty > 0:
        lot = open_lots[lot_index]
        eligible = (
            window_start <= lot.acquire_dt.date() <= disposal.sell_dt.date()
            and lot.quantity_open > 0
            and lot.deferred_loss_unit_eur == 0
        )
        if not eligible:
            lot_index += 1
            continue

        matched_qty = min(remaining_replacement_qty, lot.quantity_open)
        if matched_qty == 0:
            lot_index += 1
            continue

        if matched_qty < lot.quantity_open:
            tagged_lot = replace(
                lot,
                quantity_open=matched_qty,
                unit_cost_eur=lot.unit_cost_eur + loss_per_share,
                deferred_loss_unit_eur=lot.deferred_loss_unit_eur + loss_per_share,
                deferred_source_year=disposal.sell_dt.year,
            )
            remaining_lot = replace(
                lot,
                quantity_open=lot.quantity_open - matched_qty,
            )
            open_lots[lot_index : lot_index + 1] = [tagged_lot, remaining_lot]
            lot_index += 1
        else:
            lot.unit_cost_eur += loss_per_share
            lot.deferred_loss_unit_eur += loss_per_share
            lot.deferred_source_year = disposal.sell_dt.year
            lot_index += 1

        disposal.blocked_loss_eur += matched_qty * loss_per_share
        disposal.replacement_quantity += matched_qty
        disposal.gain_loss_eur += matched_qty * loss_per_share
        remaining_replacement_qty -= matched_qty

    return remaining_replacement_qty


def position_before_dt(trades: Iterable[Trade], cutoff: datetime) -> Decimal:
    position = Decimal("0")
    for trade in trades:
        if trade.trade_dt >= cutoff:
            continue
        if trade.side == "BUY":
            position += trade.quantity
        elif trade.side == "SELL":
            position -= trade.quantity
    return position


def compute_two_month_context(trades: list[Trade], disposal: Disposal) -> tuple[Decimal, Decimal, bool]:
    replacement_window_months = get_replacement_window_months(disposal.isin)
    window_start_dt = start_of_day(add_months(disposal.sell_dt.date(), -replacement_window_months))
    window_end_dt = end_of_day(add_months(disposal.sell_dt.date(), replacement_window_months))
    prior_buys = [
        trade
        for trade in trades
        if trade.side == "BUY" and window_start_dt <= trade.trade_dt <= disposal.sell_dt
    ]
    future_buys = [
        trade
        for trade in trades
        if trade.side == "BUY" and disposal.sell_dt < trade.trade_dt <= window_end_dt
    ]
    prior_buys_qty = sum((trade.quantity for trade in prior_buys), Decimal("0"))
    future_buys_qty = sum((trade.quantity for trade in future_buys), Decimal("0"))
    single_prior_buy_exception = len(prior_buys) == 1 and position_before_dt(trades, window_start_dt) == 0
    return prior_buys_qty, future_buys_qty, single_prior_buy_exception


def run_fifo(
    trades: list[Trade],
    apply_two_month_rule: bool = False,
    history_end_date: date | None = None,
    snapshot_year: int | None = None,
) -> tuple[list[Disposal], dict[str, list[Lot]], dict[str, list[Lot]], dict[str, list[Lot]], list[str]]:
    lots_by_isin: dict[str, list[Lot]] = defaultdict(list)
    pending_losses_by_isin: dict[str, list[DeferredLoss]] = defaultdict(list)
    processed_trades_by_isin: dict[str, list[Trade]] = defaultdict(list)
    disposals: list[Disposal] = []
    warnings: list[str] = []
    last_trade_date = max((trade.trade_dt.date() for trade in trades), default=None)
    coverage_end_date = history_end_date or last_trade_date
    open_lots_at_year_end: dict[str, list[Lot]] | None = None

    for trade in trades:
        if trade.quantity == 0:
            continue

        if snapshot_year is not None and open_lots_at_year_end is None and trade.trade_dt.year > snapshot_year:
            open_lots_at_year_end = clone_open_lots(lots_by_isin)

        active_pending: list[DeferredLoss] = []
        if apply_two_month_rule:
            active_pending = [
                deferred
                for deferred in pending_losses_by_isin[trade.isin]
                if deferred.quantity_remaining > 0 and deferred.expires_on >= trade.trade_dt.date()
            ]
            pending_losses_by_isin[trade.isin] = active_pending

        if trade.side == "BUY":
            lot_cost_total = trade.total_eur if trade.total_eur != 0 else trade.gross_eur + trade.fee_eur
            unit_cost = lot_cost_total / trade.quantity
            if apply_two_month_rule:
                lots_by_isin[trade.isin].extend(apply_future_deferred_losses(trade, unit_cost, active_pending))
            else:
                lots_by_isin[trade.isin].append(
                    Lot(
                        isin=trade.isin,
                        product=trade.product,
                        acquire_dt=trade.trade_dt,
                        quantity_open=trade.quantity,
                        unit_cost_eur=unit_cost,
                        unit_gross_eur=trade.gross_eur / trade.quantity,
                        unit_fee_eur=trade.fee_eur / trade.quantity,
                        deferred_loss_unit_eur=Decimal("0"),
                        deferred_source_year=None,
                        source_order_id=trade.order_id,
                    )
                )
            processed_trades_by_isin[trade.isin].append(trade)
            continue

        quantity_left = trade.quantity
        proceeds_eur = trade.total_eur if trade.total_eur != 0 else trade.gross_eur - trade.fee_eur
        cost_basis = Decimal("0")
        matches: list[DisposalMatch] = []
        available_lots = lots_by_isin[trade.isin]

        while quantity_left > 0 and available_lots:
            lot = available_lots[0]
            consumed = min(quantity_left, lot.quantity_open)
            lot_cost = lot.unit_cost_eur * consumed
            lot_gross_cost = lot.unit_gross_eur * consumed
            lot_fee_cost = lot.unit_fee_eur * consumed
            lot_deferred_cost = lot.deferred_loss_unit_eur * consumed
            matches.append(
                DisposalMatch(
                    acquire_dt=lot.acquire_dt,
                    quantity=consumed,
                    cost_eur=lot_cost,
                    gross_cost_eur=lot_gross_cost,
                    fee_cost_eur=lot_fee_cost,
                    deferred_loss_cost_eur=lot_deferred_cost,
                    deferred_source_year=lot.deferred_source_year,
                )
            )
            cost_basis += lot_cost
            lot.quantity_open -= consumed
            quantity_left -= consumed
            if lot.quantity_open == 0:
                available_lots.pop(0)

        if quantity_left > 0:
            warnings.append(
                f"Venta sin historico suficiente para {trade.product} ({trade.isin}) el {trade.trade_dt:%d/%m/%Y %H:%M}: faltan {quantity_left} titulos en FIFO."
            )

        disposal = Disposal(
            isin=trade.isin,
            product=trade.product,
            sell_dt=trade.trade_dt,
            quantity=trade.quantity,
            proceeds_eur=proceeds_eur,
            cost_basis_eur=cost_basis,
            gain_loss_eur=proceeds_eur - cost_basis,
            order_id=trade.order_id,
            gross_proceeds_eur=trade.gross_eur,
            sell_fee_eur=trade.fee_eur,
            matches=matches,
            fifo_complete=quantity_left == 0,
        )

        if apply_two_month_rule and disposal.fifo_complete:
            _, _, single_prior_buy_exception = compute_two_month_context(processed_trades_by_isin[trade.isin], disposal)
            if single_prior_buy_exception:
                remaining_future_qty = disposal.quantity
            else:
                remaining_future_qty = apply_preexisting_replacements(disposal, available_lots)
            if disposal.tax_result_before_current_block_eur < 0 and disposal.quantity > 0 and remaining_future_qty > 0:
                pending_losses_by_isin[trade.isin].append(
                    DeferredLoss(
                        isin=trade.isin,
                        expires_on=add_months(trade.trade_dt.date(), get_replacement_window_months(trade.isin)),
                        quantity_remaining=remaining_future_qty,
                        loss_per_share_eur=abs(disposal.tax_result_before_current_block_eur) / disposal.quantity,
                        source_year=trade.trade_dt.year,
                        disposal=disposal,
                    )
                )
        elif apply_two_month_rule and not disposal.fifo_complete:
            warnings.append(
                f"No se aplica automaticamente la regla de los 2 meses para {trade.product} ({trade.isin}) el {trade.trade_dt:%d/%m/%Y %H:%M} porque falta historico FIFO."
            )

        disposals.append(disposal)
        processed_trades_by_isin[trade.isin].append(trade)

    if apply_two_month_rule:
        for pending_losses in pending_losses_by_isin.values():
            for deferred in pending_losses:
                if deferred.quantity_remaining == 0:
                    continue
                if coverage_end_date is not None and coverage_end_date >= deferred.expires_on:
                    continue
                warnings.append(
                    f"Perdida pendiente de comprobacion futura para {deferred.disposal.product} ({deferred.isin}) tras la venta del {deferred.disposal.sell_dt:%d/%m/%Y}: {deferred.quantity_remaining} titulos quedan sujetos a posibles compras hasta {deferred.expires_on:%d/%m/%Y}."
                )

    if snapshot_year is not None and open_lots_at_year_end is None:
        open_lots_at_year_end = clone_open_lots(lots_by_isin)

    open_lots_at_history_end = clone_open_lots(lots_by_isin)

    return disposals, lots_by_isin, open_lots_at_year_end or {}, open_lots_at_history_end, warnings


def analyze_two_month_candidates(trades: list[Trade], disposals: list[Disposal]) -> list[str]:
    warnings: list[str] = []
    trades_by_isin: dict[str, list[Trade]] = defaultdict(list)

    for trade in trades:
        trades_by_isin[trade.isin].append(trade)

    for disposal in disposals:
        if disposal.tax_result_before_current_block_eur >= 0:
            continue

        prior_buys_qty, future_buys_qty, single_prior_buy_exception = compute_two_month_context(trades_by_isin[disposal.isin], disposal)
        nearby_buys_qty = future_buys_qty if single_prior_buy_exception else prior_buys_qty + future_buys_qty
        if nearby_buys_qty == 0:
            continue

        warnings.append(
            f"Revisar regla de los 2 meses para {disposal.product} ({disposal.isin}) el {disposal.sell_dt:%d/%m/%Y}: hay compras del mismo valor dentro de la ventana de 2 meses (aprox. {nearby_buys_qty} titulos comprados)."
        )

    return warnings


def analyze_dividends(cash_movements: list[CashMovement], year: int) -> tuple[list[CashMovement], list[CashMovement]]:
    dividends: list[CashMovement] = []
    withholdings: list[CashMovement] = []

    for movement in cash_movements:
        if movement.booking_dt.year != year:
            continue
        desc = movement.description.lower()
        if "dividend" in desc or "dividendo" in desc:
            if "retenci" in desc or "impuesto" in desc or "withholding" in desc:
                withholdings.append(movement)
            else:
                dividends.append(movement)

    return dividends, withholdings


def analyze_interest(cash_movements: list[CashMovement], year: int) -> list[CashMovement]:
    return [
        movement
        for movement in cash_movements
        if movement.booking_dt.year == year and "interest" in movement.description.lower() and movement.amount_eur > 0
    ]


def analyze_fees(cash_movements: list[CashMovement], year: int) -> list[CashMovement]:
    result: list[CashMovement] = []
    for movement in cash_movements:
        if movement.booking_dt.year != year:
            continue
        desc = movement.description.lower()
        if "comision de conectividad" in desc or "connectivity" in desc:
            result.append(movement)
    return result


def analyze_broker_fees(cash_movements: list[CashMovement], year: int, loaded_order_ids: set[str]) -> BrokerFeeSummary:
    deductible_admin_fees: list[CashMovement] = []
    non_deductible_broker_fees: list[CashMovement] = []
    trade_fee_movements: list[CashMovement] = []

    for movement in cash_movements:
        if movement.booking_dt.year != year:
            continue

        desc = movement.description.lower()
        if "costes de transacción" in desc or "costes de transaccion" in desc:
            if movement.order_id and movement.order_id in loaded_order_ids:
                trade_fee_movements.append(movement)
            else:
                non_deductible_broker_fees.append(movement)
            continue

        if "connectivity" in desc or "conectividad" in desc:
            non_deductible_broker_fees.append(movement)
            continue

        if any(token in desc for token in ("custody", "administr", "mantenimiento", "platform fee", "service fee")):
            deductible_admin_fees.append(movement)
            continue

        if "interest" in desc and movement.amount_eur < 0:
            non_deductible_broker_fees.append(movement)
            continue

        if "fee" in desc or "comision" in desc or "comisión" in desc:
            non_deductible_broker_fees.append(movement)

    return BrokerFeeSummary(
        deductible_admin_fees=deductible_admin_fees,
        non_deductible_broker_fees=non_deductible_broker_fees,
        trade_fee_movements=trade_fee_movements,
    )


def calculate_savings_compensation(
    year_disposals: list[Disposal],
    dividends: list[CashMovement],
    interests: list[CashMovement],
    deductible_admin_fees: list[CashMovement],
    carry_income_losses: Decimal,
    carry_gains_losses: Decimal,
) -> SavingsCompensation:
    capital_income_gross = sum((movement.amount_eur for movement in dividends), Decimal("0")) + sum(
        (movement.amount_eur for movement in interests), Decimal("0")
    )
    deductible_admin_fees_total = sum((abs(movement.amount_eur) for movement in deductible_admin_fees), Decimal("0"))
    capital_income_net = capital_income_gross - deductible_admin_fees_total
    capital_gains_net = sum((disposal.gain_loss_eur for disposal in year_disposals), Decimal("0"))

    capital_income_offset_applied = Decimal("0")
    capital_gains_offset_applied = Decimal("0")

    if capital_income_net < 0 and capital_gains_net > 0:
        offset = min(abs(capital_income_net), capital_gains_net * Decimal("0.25"))
        capital_income_net += offset
        capital_gains_net -= offset
        capital_income_offset_applied = offset
    elif capital_gains_net < 0 and capital_income_net > 0:
        offset = min(abs(capital_gains_net), capital_income_net * Decimal("0.25"))
        capital_gains_net += offset
        capital_income_net -= offset
        capital_gains_offset_applied = offset

    carry_income_same = min(max(capital_income_net, Decimal("0")), carry_income_losses)
    capital_income_net -= carry_income_same
    carry_income_remaining = carry_income_losses - carry_income_same

    carry_gains_same = min(max(capital_gains_net, Decimal("0")), carry_gains_losses)
    capital_gains_net -= carry_gains_same
    carry_gains_remaining = carry_gains_losses - carry_gains_same

    carry_income_cross = Decimal("0")
    if carry_income_remaining > 0 and capital_gains_net > 0:
        carry_income_cross = min(carry_income_remaining, capital_gains_net * Decimal("0.25"))
        capital_gains_net -= carry_income_cross

    carry_gains_cross = Decimal("0")
    if carry_gains_remaining > 0 and capital_income_net > 0:
        carry_gains_cross = min(carry_gains_remaining, capital_income_net * Decimal("0.25"))
        capital_income_net -= carry_gains_cross

    return SavingsCompensation(
        capital_income_gross=capital_income_gross,
        deductible_admin_fees=deductible_admin_fees_total,
        capital_income_net_before_offset=capital_income_gross - deductible_admin_fees_total,
        capital_gains_net_before_offset=sum((disposal.gain_loss_eur for disposal in year_disposals), Decimal("0")),
        capital_income_offset_applied=capital_income_offset_applied,
        capital_gains_offset_applied=capital_gains_offset_applied,
        capital_income_net_after_current_year=capital_income_gross
        - deductible_admin_fees_total
        - capital_gains_offset_applied
        + capital_income_offset_applied,
        capital_gains_net_after_current_year=sum((disposal.gain_loss_eur for disposal in year_disposals), Decimal("0"))
        - capital_income_offset_applied
        + capital_gains_offset_applied,
        carry_income_losses_used_same_bucket=carry_income_same,
        carry_gains_losses_used_same_bucket=carry_gains_same,
        carry_income_losses_used_cross=carry_income_cross,
        carry_gains_losses_used_cross=carry_gains_cross,
        capital_income_final=capital_income_net,
        capital_gains_final=capital_gains_net,
    )


def analyze_corporate_actions(cash_movements: list[CashMovement], year: int) -> list[str]:
    alerts: list[str] = []
    keywords = (
        "split",
        "reverse split",
        "spin-off",
        "spinoff",
        "merger",
        "fusion",
        "rights issue",
        "subscription right",
        "suscripcion preferente",
        "prima de emision",
        "devolucion de aportaciones",
        "capital reduction",
        "redemption",
        "delisting",
        "ticker change",
        "stock dividend",
    )
    seen: set[str] = set()
    for movement in cash_movements:
        if movement.booking_dt.year != year:
            continue
        desc = movement.description.lower()
        if "conectividad" in desc or "connectivity" in desc:
            continue
        if any(keyword in desc for keyword in keywords):
            key = f"{movement.booking_dt.date()}|{movement.description}"
            if key not in seen:
                seen.add(key)
                alerts.append(
                    f"Posible evento corporativo a revisar manualmente el {movement.booking_dt:%d/%m/%Y}: {movement.description}"
                )
    return alerts


def summarize_foreign_income(
    dividends: list[CashMovement],
    interests: list[CashMovement],
    withholdings: list[CashMovement],
    spanish_tax_rate_hint: Decimal | None,
) -> ForeignIncomeSummary:
    def is_foreign_income(movement: CashMovement) -> bool:
        if movement.isin:
            return not movement.isin.upper().startswith("ES")
        return movement.currency.upper() != "EUR"

    def is_foreign_withholding(movement: CashMovement) -> bool:
        if movement.isin:
            return not movement.isin.upper().startswith("ES")
        return True

    def choose_best_income_match(
        withholding: CashMovement,
        candidates: list[tuple[int, CashMovement]],
    ) -> tuple[int, CashMovement] | None:
        if not candidates:
            return None

        if withholding.order_id:
            exact_order_matches = [candidate for candidate in candidates if candidate[1].order_id and candidate[1].order_id == withholding.order_id]
            if exact_order_matches:
                return min(
                    exact_order_matches,
                    key=lambda item: (
                        abs((item[1].value_date - withholding.value_date).days),
                        abs((item[1].booking_dt - withholding.booking_dt).total_seconds()),
                    ),
                )

        scored_candidates: list[tuple[tuple[int, int, int, float], tuple[int, CashMovement]]] = []
        for candidate in candidates:
            movement = candidate[1]
            same_isin = bool(withholding.isin and movement.isin and withholding.isin == movement.isin)
            same_product = bool(withholding.product and movement.product and withholding.product == movement.product)
            value_date_distance = abs((movement.value_date - withholding.value_date).days)
            booking_distance_seconds = abs((movement.booking_dt - withholding.booking_dt).total_seconds())

            if not same_isin and not same_product:
                continue
            if value_date_distance > 10:
                continue

            score = (
                0 if same_isin else 1,
                0 if same_product else 1,
                value_date_distance,
                booking_distance_seconds,
            )
            scored_candidates.append((score, candidate))

        if not scored_candidates:
            return None

        scored_candidates.sort(key=lambda item: item[0])
        return scored_candidates[0][1]

    foreign_income_candidates = [movement for movement in dividends + interests if is_foreign_income(movement)]
    matched_income_indexes: set[int] = set()
    matched_foreign_tax = Decimal("0")
    unmatched_foreign_tax = Decimal("0")

    indexed_candidates = list(enumerate(foreign_income_candidates))
    for withholding in (movement for movement in withholdings if is_foreign_withholding(movement)):
        match = choose_best_income_match(withholding, indexed_candidates)
        if match is None:
            unmatched_foreign_tax += abs(withholding.amount_eur)
            continue
        matched_income_indexes.add(match[0])
        matched_foreign_tax += abs(withholding.amount_eur)

    gross_income = sum((foreign_income_candidates[index].amount_eur for index in matched_income_indexes), Decimal("0"))

    if spanish_tax_rate_hint is None:
        return ForeignIncomeSummary(gross_income, matched_foreign_tax, unmatched_foreign_tax, None, None, None)

    limit = gross_income * spanish_tax_rate_hint
    estimated_deductible = min(matched_foreign_tax, limit)
    return ForeignIncomeSummary(gross_income, matched_foreign_tax, unmatched_foreign_tax, spanish_tax_rate_hint, limit, estimated_deductible)


def load_carryover_input(
    carry_income_losses: Decimal,
    carry_gains_losses: Decimal,
    carryover_json: Path | None,
) -> CarryoverInput:
    if carryover_json is None:
        return CarryoverInput(d(carry_income_losses), d(carry_gains_losses))

    data = json.loads(carryover_json.read_text(encoding="utf-8"))
    return CarryoverInput(
        income_losses=d(str(data.get("income_losses", carry_income_losses))),
        gains_losses=d(str(data.get("gains_losses", carry_gains_losses))),
    )


def filter_year_disposals(disposals: Iterable[Disposal], year: int) -> list[Disposal]:
    return [disposal for disposal in disposals if disposal.sell_dt.year == year]


def group_disposals(disposals: list[Disposal]) -> dict[tuple[str, str], list[Disposal]]:
    grouped: dict[tuple[str, str], list[Disposal]] = defaultdict(list)
    for disposal in disposals:
        grouped[(disposal.isin, disposal.product)].append(disposal)
    return dict(sorted(grouped.items(), key=lambda item: (item[0][1], item[0][0])))


def f2_sale_label(disposal: Disposal) -> str:
    return disposal.sell_dt.strftime("%d/%m/%Y %H:%M")


def disposal_prior_year_embedded(disposal: Disposal, year: int) -> Decimal:
    return sum(
        (
            match.deferred_loss_cost_eur
            for match in disposal.matches
            if match.deferred_source_year is not None and match.deferred_source_year < year
        ),
        Decimal("0"),
    )


def split_partial_blocked_disposal(disposal: Disposal) -> tuple[F2Line, F2Line]:
    total_real_result = disposal.tax_result_before_current_block_eur
    blocked_loss = disposal.blocked_loss_eur
    computable_result = total_real_result + blocked_loss
    blocked_qty = disposal.replacement_quantity
    computable_qty = disposal.quantity - blocked_qty

    if disposal.quantity == 0:
        raise ValueError("Cannot split a zero-quantity disposal")
    if total_real_result >= 0:
        raise ValueError(f"Cannot split partially blocked disposal with non-negative real result: {disposal.order_id}")
    if blocked_loss <= 0:
        raise ValueError(f"Cannot split disposal without blocked loss: {disposal.order_id}")

    blocked_ratio = blocked_qty / disposal.quantity
    blocked_proceeds = disposal.proceeds_eur * blocked_ratio
    computable_proceeds = disposal.proceeds_eur - blocked_proceeds

    blocked_acquisition = blocked_proceeds + blocked_loss
    computable_acquisition = computable_proceeds - computable_result

    embedded_blocked = disposal.embedded_deferred_loss_eur * blocked_ratio
    embedded_computable = disposal.embedded_deferred_loss_eur - embedded_blocked
    sale_label = f2_sale_label(disposal)

    if not approx_equal(blocked_proceeds - blocked_acquisition, -blocked_loss):
        raise ValueError(f"Blocked F2 split does not reproduce blocked loss for {disposal.order_id}")
    if not approx_equal(computable_proceeds - computable_acquisition, computable_result):
        raise ValueError(f"Computable F2 split does not reproduce computable result for {disposal.order_id}")
    if not approx_equal(blocked_acquisition + computable_acquisition, disposal.cost_basis_eur):
        raise ValueError(f"Split acquisition does not match original disposal cost for {disposal.order_id}")

    blocked_line = F2Line(
        isin=disposal.isin,
        product=disposal.product,
        sale_label=f"{sale_label} · tramo no computable",
        quantity=blocked_qty,
        proceeds_eur=blocked_proceeds,
        acquisition_eur=blocked_acquisition,
        real_gain_loss_eur=-blocked_loss,
        non_computable_loss_eur=blocked_loss,
        integrable_gain_loss_eur=Decimal("0"),
        check_two_month_rule=True,
        embedded_deferred_loss_eur=embedded_blocked,
        source_disposal=disposal,
        note="Alta F2 con check de recompra; tramo no computable",
    )
    computable_note = "Alta F2 normal; tramo computable de venta con recompra"
    if disposal.embedded_deferred_loss_eur > 0:
        computable_note += "; Integra diferido"
    computable_line = F2Line(
        isin=disposal.isin,
        product=disposal.product,
        sale_label=f"{sale_label} · tramo computable",
        quantity=computable_qty,
        proceeds_eur=computable_proceeds,
        acquisition_eur=computable_acquisition,
        real_gain_loss_eur=computable_result,
        non_computable_loss_eur=Decimal("0"),
        integrable_gain_loss_eur=computable_result,
        check_two_month_rule=False,
        embedded_deferred_loss_eur=embedded_computable,
        source_disposal=disposal,
        note=computable_note,
    )
    return blocked_line, computable_line


def build_f2_lines(disposals: list[Disposal]) -> list[F2Line]:
    lines: list[F2Line] = []
    for disposal in disposals:
        real_result = disposal.tax_result_before_current_block_eur
        blocked_loss = disposal.blocked_loss_eur
        sale_label = f2_sale_label(disposal)
        if blocked_loss == 0:
            note = "Alta F2 normal"
            if disposal.embedded_deferred_loss_eur > 0:
                note += "; Integra diferido"
            lines.append(
                F2Line(
                    isin=disposal.isin,
                    product=disposal.product,
                    sale_label=sale_label,
                    quantity=disposal.quantity,
                    proceeds_eur=disposal.proceeds_eur,
                    acquisition_eur=disposal.cost_basis_eur,
                    real_gain_loss_eur=real_result,
                    non_computable_loss_eur=Decimal("0"),
                    integrable_gain_loss_eur=disposal.gain_loss_eur,
                    check_two_month_rule=False,
                    embedded_deferred_loss_eur=disposal.embedded_deferred_loss_eur,
                    source_disposal=disposal,
                    note=note,
                )
            )
            continue

        if real_result >= 0:
            raise ValueError(f"Blocked loss on non-negative disposal result: {disposal.order_id}")

        if approx_equal(blocked_loss, abs(real_result)):
            lines.append(
                F2Line(
                    isin=disposal.isin,
                    product=disposal.product,
                    sale_label=sale_label,
                    quantity=disposal.quantity,
                    proceeds_eur=disposal.proceeds_eur,
                    acquisition_eur=disposal.cost_basis_eur,
                    real_gain_loss_eur=real_result,
                    non_computable_loss_eur=blocked_loss,
                    integrable_gain_loss_eur=Decimal("0"),
                    check_two_month_rule=True,
                    embedded_deferred_loss_eur=disposal.embedded_deferred_loss_eur,
                    source_disposal=disposal,
                    note="Alta F2 con check de recompra",
                )
            )
            continue

        if blocked_loss < abs(real_result):
            blocked_line, computable_line = split_partial_blocked_disposal(disposal)
            lines.extend([blocked_line, computable_line])
            continue

        raise ValueError(f"Blocked loss exceeds disposal loss beyond tolerance: {disposal.order_id}")
    return lines


def validate_f2_lines(f2_lines: list[F2Line], disposals: list[Disposal]) -> list[str]:
    warnings: list[str] = []
    validations = [
        (
            sum((line.proceeds_eur for line in f2_lines), Decimal("0")),
            sum((disposal.proceeds_eur for disposal in disposals), Decimal("0")),
            "transmisión total",
        ),
        (
            sum((line.acquisition_eur for line in f2_lines), Decimal("0")),
            sum((disposal.cost_basis_eur for disposal in disposals), Decimal("0")),
            "adquisición total",
        ),
        (
            sum((line.integrable_gain_loss_eur for line in f2_lines), Decimal("0")),
            sum((disposal.gain_loss_eur for disposal in disposals), Decimal("0")),
            "resultado integrable total",
        ),
        (
            sum((line.non_computable_loss_eur for line in f2_lines), Decimal("0")),
            sum((disposal.blocked_loss_eur for disposal in disposals), Decimal("0")),
            "pérdida no computable total",
        ),
    ]
    for actual, expected, label in validations:
        if not approx_equal(actual, expected):
            warnings.append(f"Las líneas F2 no cuadran en {label}: líneas {q(actual)} EUR vs disposals {q(expected)} EUR.")
    return warnings


def group_f2_lines(f2_lines: list[F2Line]) -> list[tuple[str, str, str, list[F2Line]]]:
    grouped: dict[tuple[str, str, str], list[F2Line]] = defaultdict(list)
    for line in f2_lines:
        disposal = line.source_disposal
        partial_split = disposal.blocked_loss_eur > 0 and not approx_equal(disposal.blocked_loss_eur, abs(disposal.tax_result_before_current_block_eur))
        if line.check_two_month_rule or line.embedded_deferred_loss_eur > 0 or partial_split:
            key = (line.isin, line.product, line.sale_label)
        else:
            key = (line.isin, line.product, "Agrupado sin incidencias")
        grouped[key].append(line)
    return [
        (isin, product, sale_label, grouped[(isin, product, sale_label)])
        for isin, product, sale_label in sorted(grouped.keys(), key=lambda item: (item[1], item[0], item[2]))
    ]


def render_report(
    analysis: Analysis,
    year: int,
    report_paths: list[Path],
    carryovers: CarryoverInput,
    spanish_savings_tax_rate_hint: Decimal | None,
) -> str:
    year_disposals = filter_year_disposals(analysis.disposals, year)
    f2_lines = build_f2_lines(year_disposals)
    f2_line_warnings = validate_f2_lines(f2_lines, year_disposals)
    grouped = group_f2_lines(f2_lines)
    dividends, withholdings = analyze_dividends(analysis.cash_movements, year)
    interests = analyze_interest(analysis.cash_movements, year)
    broker_fees = analyze_broker_fees(analysis.cash_movements, year, {trade.order_id for trade in analysis.trades if trade.order_id})
    savings = calculate_savings_compensation(
        year_disposals,
        dividends,
        interests,
        broker_fees.deductible_admin_fees,
        carryovers.income_losses,
        carryovers.gains_losses,
    )
    foreign_income = summarize_foreign_income(dividends, interests, withholdings, spanish_savings_tax_rate_hint)

    transmission_total = sum((line.proceeds_eur for line in f2_lines), Decimal("0"))
    acquisition_total = sum((line.acquisition_eur for line in f2_lines), Decimal("0"))
    recognized_total = sum((line.integrable_gain_loss_eur for line in f2_lines), Decimal("0"))
    market_without_prior_deferred_total = sum((disposal.market_result_without_prior_deferred_eur for disposal in year_disposals), Decimal("0"))
    embedded_deferred_total = sum((line.embedded_deferred_loss_eur for line in f2_lines), Decimal("0"))
    fiscal_before_current_block_total = sum((disposal.tax_result_before_current_block_eur for disposal in year_disposals), Decimal("0"))
    deferred_applied_total = sum((line.non_computable_loss_eur for line in f2_lines), Decimal("0"))
    deferred_pending_year_end_total = deferred_loss_total(analysis.open_lots_at_year_end)
    deferred_pending_total = deferred_loss_total(analysis.open_lots_at_history_end)
    dividends_total = sum((movement.amount_eur for movement in dividends), Decimal("0"))
    withholdings_total = sum((abs(movement.amount_eur) for movement in withholdings), Decimal("0"))
    interest_total = sum((movement.amount_eur for movement in interests), Decimal("0"))
    deductible_fees_total = sum((abs(movement.amount_eur) for movement in broker_fees.deductible_admin_fees), Decimal("0"))
    non_deductible_fees_total = sum((abs(movement.amount_eur) for movement in broker_fees.non_deductible_broker_fees), Decimal("0"))
    trade_fee_movements_total = sum((abs(movement.amount_eur) for movement in broker_fees.trade_fee_movements), Decimal("0"))
    blocked_cases = [line for line in f2_lines if line.check_two_month_rule]
    fifo_incomplete_cases = [disposal for disposal in year_disposals if not disposal.fifo_complete]
    max_trade_date = max((trade.trade_dt.date() for trade in analysis.trades), default=None)
    history_end_date_missing = not analysis.history_end_date_declared

    def add_table(lines: list[str], headers: list[str], rows: list[list[str]]) -> None:
        lines.append("| " + " | ".join(headers) + " |")
        separator = ["---"] + ["---:" if index > 0 and headers[index] not in {"Activo", "ISIN", "Fecha / Grupo", "¿Marcar check recompra?", "Acción en Renta WEB", "Motivo", "Conclusión", "Dónde va", "Acción", "Impacto", "Alerta", "Nivel"} else "---" for index in range(1, len(headers))]
        lines.append("| " + " | ".join(separator) + " |")
        for row in rows:
            lines.append("| " + " | ".join(row) + " |")

    def pending_by_isin(lots_by_isin: dict[str, list[Lot]]) -> dict[str, Decimal]:
        result: dict[str, Decimal] = {}
        for isin, lots in lots_by_isin.items():
            amount = sum((lot.quantity_open * lot.deferred_loss_unit_eur for lot in lots if lot.quantity_open > 0), Decimal("0"))
            if amount != 0:
                result[isin] = amount
        return result

    def action_for_group(group_lines: list[F2Line], embedded_prior_year: Decimal) -> str:
        actions = list(dict.fromkeys(line.note for line in group_lines))
        if embedded_prior_year > 0:
            actions.append("REVISAR Renta WEB: imputación de pérdidas de ejercicios anteriores")
        if any(not line.source_disposal.fifo_complete for line in group_lines):
            actions.append("REVISAR: FIFO incompleto")
        return "; ".join(actions)

    def yes_no(value: bool) -> str:
        return "SÍ" if value else "NO"

    generated_by_isin: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    integrated_by_isin: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    prior_year_integrated_by_isin: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    product_by_isin: dict[str, str] = {}

    for disposal in year_disposals:
        product_by_isin[disposal.isin] = disposal.product
        generated_by_isin[disposal.isin] += disposal.blocked_loss_eur
        integrated_by_isin[disposal.isin] += disposal.embedded_deferred_loss_eur
        for match in disposal.matches:
            if match.deferred_source_year is not None and match.deferred_source_year < year:
                prior_year_integrated_by_isin[disposal.isin] += match.deferred_loss_cost_eur

    year_end_pending_by_isin = pending_by_isin(analysis.open_lots_at_year_end)
    history_end_pending_by_isin = pending_by_isin(analysis.open_lots_at_history_end)

    for lots_by_isin in (analysis.open_lots_at_year_end, analysis.open_lots_at_history_end):
        for isin, lots in lots_by_isin.items():
            if isin not in product_by_isin and lots:
                product_by_isin[isin] = lots[0].product

    lines: list[str] = []
    lines.append(f"# Informe IRPF {year} - Interactive Brokers")
    lines.append("")
    lines.append("## 1. Resumen ejecutivo")
    lines.append("")
    add_table(
        lines,
        ["Concepto", "Importe / Estado", "Acción"],
        [
            ["Resultado F2 integrable antes de compensaciones", f"{q(recognized_total)} EUR", "Meter en Renta WEB"],
            ["Valor total de transmisión", f"{q(transmission_total)} EUR", "Informar en F2"],
            ["Valor total de adquisición", f"{q(acquisition_total)} EUR", "Informar en F2"],
            [f"Pérdidas no computables por regla 2 meses generadas en {year}", f"{q(deferred_applied_total)} EUR", "Marcar check solo en las líneas afectadas"],
            [f"Pérdidas diferidas de ventas anteriores integradas en {year}", f"{q(embedded_deferred_total)} EUR", "Verificar si proceden del mismo ejercicio o de ejercicios anteriores"],
            [f"Pérdida diferida pendiente a 31/12/{year}", f"{q(deferred_pending_year_end_total)} EUR", "Si es 0, no queda pérdida bloqueada al cierre"],
            ["Pérdida diferida pendiente al final del histórico cargado", f"{q(deferred_pending_total)} EUR", "Si es 0, no queda pérdida pendiente según el histórico"],
            ["Dividendos brutos", f"{q(dividends_total)} EUR", "Capital mobiliario, si aplica"],
            ["Retención extranjera asociada", f"{q(foreign_income.foreign_tax_paid_eur)} EUR", "Doble imposición, si aplica"],
            ["Intereses", f"{q(interest_total)} EUR", "Capital mobiliario, si aplica"],
        ],
    )
    lines.append("")
    executive_conclusion: list[str] = []
    executive_conclusion.append(f"- Pérdidas compensables: {'SÍ' if recognized_total < 0 else 'NO'}. Resultado F2 integrable actual: {q(recognized_total)} EUR.")
    executive_conclusion.append(f"- Pérdidas bloqueadas pendientes: cierre {q(deferred_pending_year_end_total)} EUR; final histórico {q(deferred_pending_total)} EUR.")
    executive_conclusion.append(f"- Líneas con check de regla de 2 meses: {yes_no(bool(blocked_cases))}.")
    critical_pre_filing = []
    if fifo_incomplete_cases:
        critical_pre_filing.append("FIFO incompleto")
    if history_end_date_missing and any(disposal.f2_real_gain_loss_eur < 0 and disposal.sell_dt.month >= 11 for disposal in year_disposals):
        critical_pre_filing.append("history-end-date ausente")
    if deferred_pending_total > 0:
        critical_pre_filing.append("pérdida diferida pendiente final")
    executive_conclusion.append(f"- Crítico antes de presentar: {', '.join(critical_pre_filing) if critical_pre_filing else 'NO detectado' }.")
    lines.extend(executive_conclusion[:5])
    lines.append("")
    lines.append("## 2. Qué meter en Renta WEB")
    lines.append("")
    renta_rows: list[list[str]] = []
    for isin, product, sale_label, group_lines in grouped:
        proceeds = sum((line.proceeds_eur for line in group_lines), Decimal("0"))
        cost = sum((line.acquisition_eur for line in group_lines), Decimal("0"))
        real_result = sum((line.real_gain_loss_eur for line in group_lines), Decimal("0"))
        deferred_applied = sum((line.non_computable_loss_eur for line in group_lines), Decimal("0"))
        recognized = sum((line.integrable_gain_loss_eur for line in group_lines), Decimal("0"))
        embedded_prior_year = sum(
            (disposal_prior_year_embedded(line.source_disposal, year) for line in group_lines),
            Decimal("0"),
        )
        renta_rows.append(
            [
                product,
                isin,
                sale_label,
                f"{q(proceeds)} EUR",
                f"{q(cost)} EUR",
                f"{q(real_result)} EUR",
                f"{q(deferred_applied)} EUR",
                yes_no(any(line.check_two_month_rule for line in group_lines)),
                f"{q(recognized)} EUR",
                action_for_group(group_lines, embedded_prior_year),
            ]
        )
    add_table(
        lines,
        [
            "Activo",
            "ISIN",
            "Fecha / Grupo",
            "Transmisión EUR",
            "Adquisición EUR",
            "Resultado real",
            "Pérdida no computable 2M",
            "¿Marcar check recompra?",
            "Resultado integrable",
            "Acción en Renta WEB",
        ],
        renta_rows,
    )
    lines.append("")
    lines.append("### Checks de regla de 2 meses")
    lines.append("")
    if blocked_cases:
        check_rows = []
        for line in blocked_cases:
            real_loss = abs(min(line.real_gain_loss_eur, Decimal("0")))
            is_partial = line.source_disposal.blocked_loss_eur > 0 and not approx_equal(line.source_disposal.blocked_loss_eur, abs(line.source_disposal.tax_result_before_current_block_eur))
            check_rows.append(
                [
                    line.sale_label,
                    line.product,
                    line.isin,
                    f"{q(real_loss)} EUR",
                    f"{q(line.non_computable_loss_eur)} EUR",
                    (
                        f"Venta dividida para Renta WEB. Tramo no computable por recompra homogénea dentro de {get_replacement_window_months(line.isin)} meses; {line.quantity} títulos afectados."
                        if is_partial
                        else f"Recompra homogénea dentro de {get_replacement_window_months(line.isin)} meses; {line.source_disposal.replacement_quantity} títulos afectados."
                    ),
                ]
            )
        add_table(lines, ["Fecha", "Activo", "ISIN", "Pérdida real", "Pérdida no computable", "Motivo"], check_rows)
    else:
        lines.append("No hay líneas F2 con check de regla de 2 meses.")
    lines.append("")
    f2_integrable_gains = sum((line.integrable_gain_loss_eur for line in f2_lines if line.integrable_gain_loss_eur > 0), Decimal("0"))
    f2_integrable_losses = abs(sum((line.integrable_gain_loss_eur for line in f2_lines if line.integrable_gain_loss_eur < 0), Decimal("0")))
    f2_net = f2_integrable_gains - f2_integrable_losses
    f2_non_computable = sum((line.non_computable_loss_eur for line in f2_lines), Decimal("0"))
    lines.append("## 3. Control casillas Renta WEB")
    lines.append("")
    add_table(
        lines,
        ["Concepto", "Importe"],
        [
            ["Suma ganancias integrables acciones negociadas", f"{q(f2_integrable_gains)} EUR"],
            ["Suma pérdidas integrables acciones negociadas", f"{q(f2_integrable_losses)} EUR"],
            ["Resultado neto integrable F2", f"{q(f2_net)} EUR"],
            ["Pérdidas no computables por regla 2M", f"{q(f2_non_computable)} EUR"],
        ],
    )
    lines.append("")
    if deferred_pending_total == 0:
        lines.append("No queda pérdida diferida pendiente al final del histórico cargado.")
        lines.append("")
    lines.append("## 4. Validación de pérdidas diferidas")
    lines.append("")
    validation_isins = sorted(set(generated_by_isin) | set(integrated_by_isin) | set(year_end_pending_by_isin) | set(history_end_pending_by_isin))
    validation_rows: list[list[str]] = []
    for isin in validation_isins:
        generated = generated_by_isin.get(isin, Decimal("0"))
        integrated = integrated_by_isin.get(isin, Decimal("0"))
        pending_year_end = year_end_pending_by_isin.get(isin, Decimal("0"))
        pending_history_end = history_end_pending_by_isin.get(isin, Decimal("0"))
        if prior_year_integrated_by_isin.get(isin, Decimal("0")) > 0:
            conclusion = "REVISAR Renta WEB: imputación de pérdidas de ejercicios anteriores"
        elif pending_year_end > 0 and pending_history_end == 0:
            conclusion = "Bloqueada al cierre, liberada posteriormente"
        elif pending_year_end > 0:
            conclusion = "Bloqueada al cierre del ejercicio"
        elif pending_history_end == 0:
            conclusion = "Liberada completamente"
        else:
            conclusion = "Pendiente según histórico cargado"
        validation_rows.append(
            [
                product_by_isin.get(isin, "REVISAR"),
                isin,
                f"{q(generated)} EUR",
                f"{q(integrated)} EUR",
                f"{q(pending_year_end)} EUR",
                f"{q(pending_history_end)} EUR",
                conclusion,
            ]
        )
    if not validation_rows:
        validation_rows.append(["-", "-", "0.00 EUR", "0.00 EUR", "0.00 EUR", "0.00 EUR", "Sin pérdidas diferidas detectadas"])
    add_table(lines, ["Activo", "ISIN", "Pérdida diferida generada", "Pérdida diferida integrada", "Pendiente 31/12", "Pendiente final histórico", "Conclusión"], validation_rows)
    lines.append("")
    lines.append("## 5. Compensaciones base del ahorro")
    lines.append("")
    current_year_cross_comp = savings.capital_income_offset_applied + savings.capital_gains_offset_applied
    prior_year_carry_used = (
        savings.carry_income_losses_used_same_bucket
        + savings.carry_gains_losses_used_same_bucket
        + savings.carry_income_losses_used_cross
        + savings.carry_gains_losses_used_cross
    )
    add_table(
        lines,
        ["Concepto", "Importe"],
        [
            ["Saldo ganancias/pérdidas patrimoniales F2 antes de compensaciones", f"{q(savings.capital_gains_net_before_offset)} EUR"],
            ["Saldo capital mobiliario antes de compensaciones", f"{q(savings.capital_income_net_before_offset)} EUR"],
            ["Compensación aplicada entre bloques del ejercicio", f"{q(current_year_cross_comp)} EUR"],
            ["Arrastres de años anteriores usados", f"{q(prior_year_carry_used)} EUR"],
            ["Saldo final F2 estimado por el script", f"{q(savings.capital_gains_final)} EUR"],
            ["Saldo final capital mobiliario estimado", f"{q(savings.capital_income_final)} EUR"],
        ],
    )
    lines.append("")
    lines.append("Usar como control, no como sustituto del cálculo automático de Renta WEB.")
    lines.append("")
    compensation_conclusion: list[str] = []
    compensation_conclusion.append(f"- Pérdida patrimonial compensable: {'SÍ' if savings.capital_gains_final < 0 else 'NO'}.")
    compensation_conclusion.append(f"- Compensación con capital mobiliario: {'SÍ' if current_year_cross_comp > 0 else 'NO'}.")
    compensation_conclusion.append(
        f"- Saldo negativo para arrastrar: {'SÍ' if savings.capital_gains_final < 0 or savings.capital_income_final < 0 else 'NO'}.")
    lines.extend(compensation_conclusion)
    lines.append("")
    lines.append("## 6. Dividendos, retenciones y doble imposición")
    lines.append("")
    if dividends_total == 0 and interest_total == 0 and withholdings_total == 0:
        lines.append("No se detectan dividendos, intereses ni retenciones extranjeras relevantes.")
    else:
        income_rows = [
            ["Dividendos brutos", f"{q(dividends_total)} EUR", "Capital mobiliario"],
            ["Intereses", f"{q(interest_total)} EUR", "Capital mobiliario"],
            ["Retención extranjera asociada", f"{q(foreign_income.foreign_tax_paid_eur)} EUR", "Deducción doble imposición internacional; estimación heurística"],
            ["Renta extranjera asociada", f"{q(foreign_income.gross_income_eur)} EUR", "Deducción doble imposición internacional; estimación heurística"],
        ]
        if foreign_income.unmatched_foreign_tax_paid_eur > 0:
            income_rows.append(
                [
                    "Retención extranjera no emparejada",
                    f"{q(foreign_income.unmatched_foreign_tax_paid_eur)} EUR",
                    "REVISAR manualmente antes de trasladar a Renta WEB",
                ]
            )
        add_table(lines, ["Concepto", "Importe EUR", "Dónde va"], income_rows)
    lines.append("")
    lines.append("La doble imposición se detecta de forma heurística por descripción del movimiento. Revisa manualmente dividendos y retenciones antes de trasladarlos a Renta WEB.")
    lines.append("")
    lines.append("## 7. Insights fiscales importantes")
    lines.append("")
    insights: list[str] = []
    if blocked_cases and deferred_pending_total == 0:
        insights.append("- Hay líneas con check 2M, pero la pérdida diferida pendiente final es 0; el bloqueo fue temporal y toda la pérdida diferida quedó liberada después.")
    if blocked_cases and deferred_pending_total > 0:
        insights.append("- Hay líneas con check 2M y queda pérdida diferida pendiente al final del histórico; el resultado final todavía depende de ventas futuras de los lotes de sustitución.")
    if embedded_deferred_total > 0 and any(amount > 0 for amount in prior_year_integrated_by_isin.values()):
        insights.append("- Parte del resultado 2025 integra pérdidas diferidas procedentes de ejercicios anteriores; no debe mezclarse con el resultado propio de la venta sin verificar la imputación en Renta WEB.")
    elif embedded_deferred_total > 0:
        insights.append("- El control de casillas F2 debe hacerse con las líneas fiscales F2, no con cada Disposal bruto: una venta parcialmente bloqueada puede dividirse en un tramo no computable con check y otro tramo computable sin check.")
    if fifo_incomplete_cases:
        insights.append("- Hay ventas con FIFO incompleto; en esas líneas se bloquea la aplicación automática de la regla de recompra hasta completar histórico anterior.")
    if history_end_date_missing:
        insights.append("- Falta history-end-date; cualquier pérdida de noviembre o diciembre con ventana futura no completamente cubierta queda con fiabilidad limitada para recompras posteriores.")
    if not blocked_cases:
        insights.append("- No hay líneas F2 con pérdida no computable por recompra; todas las ventas del ejercicio son integrables según el histórico cargado.")
    for insight in insights[:6]:
        lines.append(insight)
    if not insights:
        lines.append("- No se detectan incidencias fiscales adicionales en los datos cargados.")
    lines.append("")
    lines.append("## 8. Alertas críticas antes de presentar")
    lines.append("")
    alerts: list[list[str]] = []
    if fifo_incomplete_cases:
        alerts.append([
            "CRÍTICO",
            f"FIFO incompleto en {len(fifo_incomplete_cases)} venta(s)",
            "El coste real y la regla de recompra de esas líneas no son fiables.",
            "Completar histórico anterior y regenerar el informe.",
        ])
    if history_end_date_missing and any(disposal.f2_real_gain_loss_eur < 0 and disposal.sell_dt.month >= 11 for disposal in year_disposals):
        alerts.append([
            "CRÍTICO",
            "Falta --history-end-date con ventas con pérdida cerca de final de año",
            "La ventana futura de recompra puede no estar completamente cubierta.",
            "Exportar histórico hasta al menos febrero del año siguiente o informar history-end-date real.",
        ])
    if analysis.history_end_date is not None and max_trade_date is not None and analysis.history_end_date < max_trade_date:
        alerts.append([
            "CRÍTICO",
            f"history-end-date {analysis.history_end_date.isoformat()} anterior a la última operación {max_trade_date.isoformat()}",
            "La cobertura temporal declarada es inconsistente con el CSV cargado.",
            "Corregir history-end-date y regenerar.",
        ])
    if deferred_pending_total > 0:
        alerts.append([
            "CRÍTICO",
            "Queda pérdida diferida pendiente al final del histórico cargado",
            "No toda la pérdida bloqueada se ha liberado todavía.",
            "No integrar esa parte pendiente como pérdida compensable hasta su liberación.",
        ])
    if any(amount > 0 for amount in prior_year_integrated_by_isin.values()):
        alerts.append([
            "REVISAR",
            f"Hay pérdidas diferidas procedentes de ejercicios anteriores integradas en {year}",
            "Renta WEB puede requerir imputación separada de ejercicios anteriores.",
            "Verificar las líneas afectadas en la sección de validación de pérdidas diferidas.",
        ])
    same_timestamp_warnings = [warning for warning in analysis.warnings if "mismo timestamp" in warning]
    if same_timestamp_warnings:
        alerts.append([
            "REVISAR",
            "Operaciones BUY/SELL con mismo timestamp",
            "El orden real de ejecución puede alterar FIFO y regla de recompra.",
            "Contrastar el orden exacto en el extracto del broker.",
        ])
    if analysis.corporate_action_alerts:
        alerts.append([
            "REVISAR",
            "Eventos corporativos detectados",
            "Pueden alterar coste, número de títulos o tratamiento fiscal.",
            "Revisar manualmente los eventos listados por el broker.",
        ])
    non_common = [
        warning
        for warning in analysis.warnings
        if warning.startswith("Instrumento no accion comun detectado")
    ]
    if non_common:
        alerts.append([
            "REVISAR",
            f"Instrumentos no accion común detectados ({len(non_common)})",
            "IBKR los agrupa como acciones, pero ETFs/ETCs/otros productos pueden tener tratamiento fiscal distinto.",
            "Revisar manualmente esos instrumentos antes de trasladarlos a Renta WEB.",
        ])
    if history_end_date_missing and not any(disposal.f2_real_gain_loss_eur < 0 and disposal.sell_dt.month >= 11 for disposal in year_disposals):
        alerts.append([
            "INFORMATIVO",
            "No se ha indicado history-end-date",
            "La cobertura temporal se infiere de la última operación del CSV.",
            "Indicar history-end-date real para cerrar la validación de recompras futuras.",
        ])
    for warning in f2_line_warnings:
        alerts.append([
            "CRÍTICO",
            warning,
            "Las líneas fiscales F2 no cuadran con los Disposal originales.",
            "Revisar el split de líneas F2 antes de trasladar datos a Renta WEB.",
        ])
    if alerts:
        add_table(lines, ["Nivel", "Alerta", "Impacto", "Acción"], alerts)
    else:
        lines.append("No se detectan alertas críticas en el informe proporcionado.")
    lines.append("")
    lines.append("## 9. Resumen final para copiar a mano")
    lines.append("")
    lines.append("```text")
    lines.append("F2 acciones:")
    lines.append(f"- Transmisión total: {q(transmission_total)} EUR")
    lines.append(f"- Adquisición total: {q(acquisition_total)} EUR")
    lines.append(f"- Resultado integrable antes de compensaciones: {q(recognized_total)} EUR")
    lines.append(f"- Líneas con check regla 2 meses: {yes_no(bool(blocked_cases))}")
    lines.append(f"- Pérdida diferida pendiente final: {q(deferred_pending_total)} EUR")
    lines.append("")
    lines.append("Capital mobiliario:")
    lines.append(f"- Dividendos/intereses brutos: {q(dividends_total + interest_total)} EUR")
    lines.append(f"- Gastos deducibles: {q(deductible_fees_total)} EUR")
    lines.append(f"- Retención extranjera asociada: {q(foreign_income.foreign_tax_paid_eur)} EUR")
    if foreign_income.unmatched_foreign_tax_paid_eur > 0:
        lines.append(f"- Retención extranjera no emparejada: {q(foreign_income.unmatched_foreign_tax_paid_eur)} EUR")
    lines.append("")
    lines.append("Conclusión:")
    if critical_pre_filing:
        lines.append(f"{'; '.join(critical_pre_filing)}")
    else:
        lines.append("Sin bloqueos finales pendientes ni alertas críticas de presentación.")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def _excel_sheet_name(name: str) -> str:
    invalid = set('[]:*?/\\')
    cleaned = "".join("_" if char in invalid else char for char in name).strip()
    return (cleaned or "Hoja")[:31]


def _excel_col_name(index: int) -> str:
    result = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _excel_cell(value: str | int | float | Decimal | None) -> tuple[str, str]:
    if value is None:
        return "inlineStr", ""
    if isinstance(value, Decimal):
        return "n", q(value)
    if isinstance(value, (int, float)):
        return "n", str(value)
    text = str(value)
    stripped = text.strip()
    if stripped.endswith(" EUR"):
        number_text = stripped[:-4].strip()
        try:
            return "n", q(d(number_text))
        except Exception:
            pass
    return "inlineStr", text


def _build_excel_sheet_xml(rows: list[list[str | int | float | Decimal | None]]) -> str:
    xml_rows: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        cells: list[str] = []
        for col_index, value in enumerate(row, start=1):
            cell_ref = f"{_excel_col_name(col_index)}{row_index}"
            cell_type, cell_value = _excel_cell(value)
            if cell_type == "n":
                cells.append(f'<c r="{cell_ref}" t="n"><v>{escape(cell_value)}</v></c>')
            else:
                cells.append(f'<c r="{cell_ref}" t="inlineStr"><is><t xml:space="preserve">{escape(cell_value)}</t></is></c>')
        xml_rows.append(f"<row r=\"{row_index}\">{''.join(cells)}</row>")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(xml_rows)}</sheetData>"
        '</worksheet>'
    )


def _write_simple_xlsx(workbook_path: Path, sheets: list[tuple[str, list[list[str | int | float | Decimal | None]]]]) -> None:
    workbook_path.parent.mkdir(parents=True, exist_ok=True)
    content_types_override = []
    rels = []
    workbook_sheets = []
    sheet_xml_map: dict[str, str] = {}

    for index, (sheet_name, rows) in enumerate(sheets, start=1):
        sheet_file = f"sheet{index}.xml"
        content_types_override.append(
            f'<Override PartName="/xl/worksheets/{sheet_file}" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
        rels.append(
            f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/{sheet_file}"/>'
        )
        workbook_sheets.append(
            f'<sheet name="{escape(_excel_sheet_name(sheet_name))}" sheetId="{index}" r:id="rId{index}"/>'
        )
        sheet_xml_map[sheet_file] = _build_excel_sheet_xml(rows)

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        f"{''.join(content_types_override)}"
        '</Types>'
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{''.join(workbook_sheets)}</sheets>"
        '</workbook>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{''.join(rels)}"
        '</Relationships>'
    )

    with zipfile.ZipFile(workbook_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        for sheet_file, sheet_xml in sheet_xml_map.items():
            archive.writestr(f"xl/worksheets/{sheet_file}", sheet_xml)


def render_excel_report(
    workbook_path: Path,
    analysis: Analysis,
    year: int,
    report_paths: list[Path],
    carryovers: CarryoverInput,
    spanish_savings_tax_rate_hint: Decimal | None,
) -> None:
    year_disposals = filter_year_disposals(analysis.disposals, year)
    f2_lines = build_f2_lines(year_disposals)
    f2_line_warnings = validate_f2_lines(f2_lines, year_disposals)
    grouped = group_f2_lines(f2_lines)
    dividends, withholdings = analyze_dividends(analysis.cash_movements, year)
    interests = analyze_interest(analysis.cash_movements, year)
    broker_fees = analyze_broker_fees(analysis.cash_movements, year, {trade.order_id for trade in analysis.trades if trade.order_id})
    savings = calculate_savings_compensation(
        year_disposals,
        dividends,
        interests,
        broker_fees.deductible_admin_fees,
        carryovers.income_losses,
        carryovers.gains_losses,
    )
    foreign_income = summarize_foreign_income(
        dividends,
        interests,
        withholdings,
        spanish_savings_tax_rate_hint,
    )

    transmission_total = sum((line.proceeds_eur for line in f2_lines), Decimal("0"))
    acquisition_total = sum((line.acquisition_eur for line in f2_lines), Decimal("0"))
    recognized_total = sum((line.integrable_gain_loss_eur for line in f2_lines), Decimal("0"))
    embedded_deferred_total = sum((line.embedded_deferred_loss_eur for line in f2_lines), Decimal("0"))
    deferred_applied_total = sum((line.non_computable_loss_eur for line in f2_lines), Decimal("0"))
    deferred_pending_year_end_total = deferred_loss_total(analysis.open_lots_at_year_end)
    deferred_pending_total = deferred_loss_total(analysis.open_lots_at_history_end)
    dividends_total = sum((movement.amount_eur for movement in dividends), Decimal("0"))
    withholdings_total = sum((abs(movement.amount_eur) for movement in withholdings), Decimal("0"))
    interest_total = sum((movement.amount_eur for movement in interests), Decimal("0"))
    deductible_fees_total = sum((abs(movement.amount_eur) for movement in broker_fees.deductible_admin_fees), Decimal("0"))

    blocked_cases = [line for line in f2_lines if line.check_two_month_rule]
    fifo_incomplete_cases = [disposal for disposal in year_disposals if not disposal.fifo_complete]
    max_trade_date = max((trade.trade_dt.date() for trade in analysis.trades), default=None)
    history_end_date_missing = not analysis.history_end_date_declared

    def pending_by_isin(lots_by_isin: dict[str, list[Lot]]) -> dict[str, Decimal]:
        result: dict[str, Decimal] = {}
        for isin, lots in lots_by_isin.items():
            amount = sum((lot.quantity_open * lot.deferred_loss_unit_eur for lot in lots if lot.quantity_open > 0), Decimal("0"))
            if amount != 0:
                result[isin] = amount
        return result

    def action_for_group(group_lines: list[F2Line], embedded_prior_year: Decimal) -> str:
        actions = list(dict.fromkeys(line.note for line in group_lines))
        if embedded_prior_year > 0:
            actions.append("REVISAR Renta WEB: imputación de pérdidas de ejercicios anteriores")
        if any(not line.source_disposal.fifo_complete for line in group_lines):
            actions.append("REVISAR: FIFO incompleto")
        return "; ".join(actions)

    generated_by_isin: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    integrated_by_isin: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    prior_year_integrated_by_isin: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    product_by_isin: dict[str, str] = {}
    for disposal in year_disposals:
        product_by_isin[disposal.isin] = disposal.product
        generated_by_isin[disposal.isin] += disposal.blocked_loss_eur
        integrated_by_isin[disposal.isin] += disposal.embedded_deferred_loss_eur
        for match in disposal.matches:
            if match.deferred_source_year is not None and match.deferred_source_year < year:
                prior_year_integrated_by_isin[disposal.isin] += match.deferred_loss_cost_eur

    year_end_pending_by_isin = pending_by_isin(analysis.open_lots_at_year_end)
    history_end_pending_by_isin = pending_by_isin(analysis.open_lots_at_history_end)

    for lots_by_isin in (analysis.open_lots_at_year_end, analysis.open_lots_at_history_end):
        for isin, lots in lots_by_isin.items():
            if isin not in product_by_isin and lots:
                product_by_isin[isin] = lots[0].product

    critical_pre_filing: list[str] = []
    if fifo_incomplete_cases:
        critical_pre_filing.append("FIFO incompleto")
    if history_end_date_missing and any(disposal.f2_real_gain_loss_eur < 0 and disposal.sell_dt.month >= 11 for disposal in year_disposals):
        critical_pre_filing.append("history-end-date ausente")
    if deferred_pending_total > 0:
        critical_pre_filing.append("pérdida diferida pendiente final")

    summary_rows: list[list[str | Decimal]] = [
        ["Concepto", "Importe / Estado", "Acción"],
        ["Resultado F2 integrable antes de compensaciones", recognized_total, "Meter en Renta WEB"],
        ["Valor total de transmisión", transmission_total, "Informar en F2"],
        ["Valor total de adquisición", acquisition_total, "Informar en F2"],
        [f"Pérdidas no computables por regla 2 meses generadas en {year}", deferred_applied_total, "Marcar check solo en las líneas afectadas"],
        [f"Pérdidas diferidas de ventas anteriores integradas en {year}", embedded_deferred_total, "Verificar si proceden del mismo ejercicio o de ejercicios anteriores"],
        [f"Pérdida diferida pendiente a 31/12/{year}", deferred_pending_year_end_total, "Si es 0, no queda pérdida bloqueada al cierre"],
        ["Pérdida diferida pendiente al final del histórico cargado", deferred_pending_total, "Si es 0, no queda pérdida pendiente según el histórico"],
        ["Dividendos brutos", dividends_total, "Capital mobiliario, si aplica"],
        ["Retención extranjera asociada", foreign_income.foreign_tax_paid_eur, "Doble imposición, si aplica"],
        ["Intereses", interest_total, "Capital mobiliario, si aplica"],
        [],
        ["Conclusión", "", ""],
        ["Pérdidas compensables", "SÍ" if recognized_total < 0 else "NO", f"Resultado F2 integrable actual: {q(recognized_total)} EUR"],
        ["Pérdidas bloqueadas pendientes", f"cierre {q(deferred_pending_year_end_total)} EUR", f"final histórico {q(deferred_pending_total)} EUR"],
        ["Líneas con check de regla de 2 meses", "SÍ" if blocked_cases else "NO", ""],
        ["Crítico antes de presentar", ", ".join(critical_pre_filing) if critical_pre_filing else "NO detectado", ""],
    ]

    renta_rows: list[list[str | Decimal]] = [[
        "Activo",
        "ISIN",
        "Fecha / Grupo",
        "Transmisión EUR",
        "Adquisición EUR",
        "Resultado real",
        "Pérdida no computable 2M",
        "¿Marcar check recompra?",
        "Resultado integrable",
        "Acción en Renta WEB",
    ]]
    for isin, product, sale_label, group_lines in grouped:
        proceeds = sum((line.proceeds_eur for line in group_lines), Decimal("0"))
        cost = sum((line.acquisition_eur for line in group_lines), Decimal("0"))
        real_result = sum((line.real_gain_loss_eur for line in group_lines), Decimal("0"))
        deferred_applied = sum((line.non_computable_loss_eur for line in group_lines), Decimal("0"))
        recognized = sum((line.integrable_gain_loss_eur for line in group_lines), Decimal("0"))
        embedded_prior_year = sum(
            (disposal_prior_year_embedded(line.source_disposal, year) for line in group_lines),
            Decimal("0"),
        )
        renta_rows.append([
            product,
            isin,
            sale_label,
            proceeds,
            cost,
            real_result,
            deferred_applied,
            "SÍ" if any(line.check_two_month_rule for line in group_lines) else "NO",
            recognized,
            action_for_group(group_lines, embedded_prior_year),
        ])

    checks_rows: list[list[str | Decimal]] = [["Fecha", "Activo", "ISIN", "Pérdida real", "Pérdida no computable", "Motivo"]]
    if blocked_cases:
        for line in blocked_cases:
            is_partial = line.source_disposal.blocked_loss_eur > 0 and not approx_equal(line.source_disposal.blocked_loss_eur, abs(line.source_disposal.tax_result_before_current_block_eur))
            checks_rows.append([
                line.sale_label,
                line.product,
                line.isin,
                abs(min(line.real_gain_loss_eur, Decimal("0"))),
                line.non_computable_loss_eur,
                (
                    f"Venta dividida para Renta WEB. Tramo no computable por recompra homogénea dentro de {get_replacement_window_months(line.isin)} meses; {line.quantity} títulos afectados."
                    if is_partial
                    else f"Recompra homogénea dentro de {get_replacement_window_months(line.isin)} meses; {line.source_disposal.replacement_quantity} títulos afectados."
                ),
            ])
    else:
        checks_rows.append(["No hay líneas F2 con check de regla de 2 meses.", "", "", "", "", ""])

    f2_integrable_gains = sum((line.integrable_gain_loss_eur for line in f2_lines if line.integrable_gain_loss_eur > 0), Decimal("0"))
    f2_integrable_losses = abs(sum((line.integrable_gain_loss_eur for line in f2_lines if line.integrable_gain_loss_eur < 0), Decimal("0")))
    f2_net = f2_integrable_gains - f2_integrable_losses
    f2_non_computable = sum((line.non_computable_loss_eur for line in f2_lines), Decimal("0"))
    control_rows: list[list[str | Decimal]] = [
        ["Concepto", "Importe"],
        ["Suma ganancias integrables acciones negociadas", f2_integrable_gains],
        ["Suma pérdidas integrables acciones negociadas", f2_integrable_losses],
        ["Resultado neto integrable F2", f2_net],
        ["Pérdidas no computables por regla 2M", f2_non_computable],
    ]

    validation_rows: list[list[str | Decimal]] = [[
        "Activo",
        "ISIN",
        "Pérdida diferida generada",
        "Pérdida diferida integrada",
        "Pendiente 31/12",
        "Pendiente final histórico",
        "Conclusión",
    ]]
    validation_isins = sorted(set(generated_by_isin) | set(integrated_by_isin) | set(year_end_pending_by_isin) | set(history_end_pending_by_isin))
    if validation_isins:
        for isin in validation_isins:
            generated = generated_by_isin.get(isin, Decimal("0"))
            integrated = integrated_by_isin.get(isin, Decimal("0"))
            pending_year_end = year_end_pending_by_isin.get(isin, Decimal("0"))
            pending_history_end = history_end_pending_by_isin.get(isin, Decimal("0"))
            if prior_year_integrated_by_isin.get(isin, Decimal("0")) > 0:
                conclusion = "REVISAR Renta WEB: imputación de pérdidas de ejercicios anteriores"
            elif pending_year_end > 0 and pending_history_end == 0:
                conclusion = "Bloqueada al cierre, liberada posteriormente"
            elif pending_year_end > 0:
                conclusion = "Bloqueada al cierre del ejercicio"
            elif pending_history_end == 0:
                conclusion = "Liberada completamente"
            else:
                conclusion = "Pendiente según histórico cargado"
            validation_rows.append([
                product_by_isin.get(isin, "REVISAR"),
                isin,
                generated,
                integrated,
                pending_year_end,
                pending_history_end,
                conclusion,
            ])
    else:
        validation_rows.append(["-", "-", Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), "Sin pérdidas diferidas detectadas"])

    compensation_rows: list[list[str | Decimal]] = [
        ["Concepto", "Importe"],
        ["Saldo ganancias/pérdidas patrimoniales F2 antes de compensaciones", savings.capital_gains_net_before_offset],
        ["Saldo capital mobiliario antes de compensaciones", savings.capital_income_net_before_offset],
        ["Compensación aplicada entre bloques del ejercicio", savings.capital_income_offset_applied + savings.capital_gains_offset_applied],
        [
            "Arrastres de años anteriores usados",
            savings.carry_income_losses_used_same_bucket
            + savings.carry_gains_losses_used_same_bucket
            + savings.carry_income_losses_used_cross
            + savings.carry_gains_losses_used_cross,
        ],
        ["Saldo final F2 estimado por el script", savings.capital_gains_final],
        ["Saldo final capital mobiliario estimado", savings.capital_income_final],
        [],
        ["Nota", "Usar como control, no como sustituto del cálculo automático de Renta WEB."],
        [],
        ["Conclusión", ""],
        ["Pérdida patrimonial compensable", "SÍ" if savings.capital_gains_final < 0 else "NO"],
        ["Compensación con capital mobiliario", "SÍ" if (savings.capital_income_offset_applied + savings.capital_gains_offset_applied) > 0 else "NO"],
        ["Saldo negativo para arrastrar", "SÍ" if savings.capital_gains_final < 0 or savings.capital_income_final < 0 else "NO"],
    ]

    income_rows: list[list[str | Decimal]] = [["Concepto", "Importe EUR", "Dónde va"]]
    if dividends_total == 0 and interest_total == 0 and withholdings_total == 0:
        income_rows.append(["No se detectan dividendos, intereses ni retenciones extranjeras relevantes.", "", ""])
    else:
        income_rows.extend([
            ["Dividendos brutos", dividends_total, "Capital mobiliario"],
            ["Intereses", interest_total, "Capital mobiliario"],
            ["Retención extranjera asociada", foreign_income.foreign_tax_paid_eur, "Deducción doble imposición internacional; estimación heurística"],
            ["Renta extranjera asociada", foreign_income.gross_income_eur, "Deducción doble imposición internacional; estimación heurística"],
        ])
        if foreign_income.unmatched_foreign_tax_paid_eur > 0:
            income_rows.append(["Retención extranjera no emparejada", foreign_income.unmatched_foreign_tax_paid_eur, "REVISAR manualmente antes de trasladar a Renta WEB."])
        income_rows.append(["Nota", "", "Revisar manualmente dividendos y retenciones antes de trasladarlos a Renta WEB."])

    insights_rows: list[list[str]] = [["Insight"]]
    insights: list[str] = []
    if blocked_cases and deferred_pending_total == 0:
        insights.append("Hay líneas con check 2M, pero la pérdida diferida pendiente final es 0; el bloqueo fue temporal y toda la pérdida diferida quedó liberada después.")
    if blocked_cases and deferred_pending_total > 0:
        insights.append("Hay líneas con check 2M y queda pérdida diferida pendiente al final del histórico; el resultado final todavía depende de ventas futuras de los lotes de sustitución.")
    if embedded_deferred_total > 0 and any(amount > 0 for amount in prior_year_integrated_by_isin.values()):
        insights.append("Parte del resultado 2025 integra pérdidas diferidas procedentes de ejercicios anteriores; no debe mezclarse con el resultado propio de la venta sin verificar la imputación en Renta WEB.")
    elif embedded_deferred_total > 0:
        insights.append("El control de casillas F2 debe hacerse con las líneas fiscales F2, no con cada Disposal bruto: una venta parcialmente bloqueada puede dividirse en un tramo no computable con check y otro tramo computable sin check.")
    if fifo_incomplete_cases:
        insights.append("Hay ventas con FIFO incompleto; en esas líneas se bloquea la aplicación automática de la regla de recompra hasta completar histórico anterior.")
    if history_end_date_missing:
        insights.append("Falta history-end-date; cualquier pérdida de noviembre o diciembre con ventana futura no completamente cubierta queda con fiabilidad limitada para recompras posteriores.")
    if not blocked_cases:
        insights.append("No hay líneas F2 con pérdida no computable por recompra; todas las ventas del ejercicio son integrables según el histórico cargado.")
    if not insights:
        insights.append("No se detectan incidencias fiscales adicionales en los datos cargados.")
    for insight in insights[:6]:
        insights_rows.append([insight])

    alerts_rows: list[list[str]] = [["Nivel", "Alerta", "Impacto", "Acción"]]
    if fifo_incomplete_cases:
        alerts_rows.append(["CRÍTICO", f"FIFO incompleto en {len(fifo_incomplete_cases)} venta(s)", "El coste real y la regla de recompra de esas líneas no son fiables.", "Completar histórico anterior y regenerar el informe."])
    if history_end_date_missing and any(disposal.f2_real_gain_loss_eur < 0 and disposal.sell_dt.month >= 11 for disposal in year_disposals):
        alerts_rows.append(["CRÍTICO", "Falta --history-end-date con ventas con pérdida cerca de final de año", "La ventana futura de recompra puede no estar completamente cubierta.", "Exportar histórico hasta al menos febrero del año siguiente o informar history-end-date real."])
    if analysis.history_end_date is not None and max_trade_date is not None and analysis.history_end_date < max_trade_date:
        alerts_rows.append(["CRÍTICO", f"history-end-date {analysis.history_end_date.isoformat()} anterior a la última operación {max_trade_date.isoformat()}", "La cobertura temporal declarada es inconsistente con el CSV cargado.", "Corregir history-end-date y regenerar."])
    if deferred_pending_total > 0:
        alerts_rows.append(["CRÍTICO", "Queda pérdida diferida pendiente al final del histórico cargado", "No toda la pérdida bloqueada se ha liberado todavía.", "No integrar esa parte pendiente como pérdida compensable hasta su liberación."])
    if any(amount > 0 for amount in prior_year_integrated_by_isin.values()):
        alerts_rows.append(["REVISAR", f"Hay pérdidas diferidas procedentes de ejercicios anteriores integradas en {year}", "Renta WEB puede requerir imputación separada de ejercicios anteriores.", "Verificar las líneas afectadas en la sección de validación de pérdidas diferidas."])
    if any("mismo timestamp" in warning for warning in analysis.warnings):
        alerts_rows.append(["REVISAR", "Operaciones BUY/SELL con mismo timestamp", "El orden real de ejecución puede alterar FIFO y regla de recompra.", "Contrastar el orden exacto en el extracto del broker."])
    if analysis.corporate_action_alerts:
        alerts_rows.append(["REVISAR", "Eventos corporativos detectados", "Pueden alterar coste, número de títulos o tratamiento fiscal.", "Revisar manualmente los eventos listados por el broker."])
    if any(warning.startswith("Instrumento no accion comun detectado") for warning in analysis.warnings):
        alerts_rows.append(["REVISAR", "Instrumentos no accion común detectados", "IBKR los agrupa como acciones, pero ETFs/ETCs/otros productos pueden tener tratamiento fiscal distinto.", "Revisar manualmente esos instrumentos antes de trasladarlos a Renta WEB."])
    if history_end_date_missing and not any(disposal.f2_real_gain_loss_eur < 0 and disposal.sell_dt.month >= 11 for disposal in year_disposals):
        alerts_rows.append(["INFORMATIVO", "No se ha indicado history-end-date", "La cobertura temporal se infiere de la última operación del CSV.", "Indicar history-end-date real para cerrar la validación de recompras futuras."])
    for warning in f2_line_warnings:
        alerts_rows.append(["CRÍTICO", warning, "Las líneas fiscales F2 no cuadran con los Disposal originales.", "Revisar el split de líneas F2 antes de trasladar datos a Renta WEB."])
    if len(alerts_rows) == 1:
        alerts_rows.append(["", "No se detectan alertas críticas en el informe proporcionado.", "", ""])

    final_rows: list[list[str]] = [
        ["F2 acciones", ""],
        ["Transmisión total", q(transmission_total) + " EUR"],
        ["Adquisición total", q(acquisition_total) + " EUR"],
        ["Resultado integrable antes de compensaciones", q(recognized_total) + " EUR"],
        ["Líneas con check regla 2 meses", "SÍ" if blocked_cases else "NO"],
        ["Pérdida diferida pendiente final", q(deferred_pending_total) + " EUR"],
        [],
        ["Capital mobiliario", ""],
        ["Dividendos/intereses brutos", q(dividends_total + interest_total) + " EUR"],
        ["Gastos deducibles", q(deductible_fees_total) + " EUR"],
        ["Retención extranjera asociada", q(foreign_income.foreign_tax_paid_eur) + " EUR"],
        [],
        ["Conclusión", "; ".join(critical_pre_filing) if critical_pre_filing else "Sin bloqueos finales pendientes ni alertas críticas de presentación."],
        [],
        ["Entradas", ""],
        ["Informes IBKR", "; ".join(str(path) for path in report_paths)],
        ["FX valores no EUR", "ECB/BCE"],
        ["History end date", analysis.history_end_date.isoformat() if analysis.history_end_date is not None else "REVISAR"],
    ]

    sheets = [
        ("01 Resumen", summary_rows),
        ("02 Renta WEB", renta_rows),
        ("03 Checks 2M", checks_rows),
        ("04 Control Renta WEB", control_rows),
        ("05 Diferidas", validation_rows),
        ("06 Compensaciones", compensation_rows),
        ("07 Capital mobiliario", income_rows),
        ("08 Insights", insights_rows),
        ("09 Alertas", alerts_rows),
        ("10 Resumen final", final_rows),
    ]
    _write_simple_xlsx(workbook_path, sheets)


def build_analysis(
    report_paths: list[Path],
    year: int,
    apply_two_month_rule: bool = True,
    history_end_date: date | None = None,
) -> Analysis:
    ecb = EcbRateProvider()
    trades, cash_movements, instruments, ecb_rates_used, ibkr_rates_used = parse_ibkr_reports(report_paths, ecb)
    trades = aggregate_trades(trades)
    disposals, open_lots, open_lots_at_year_end, open_lots_at_history_end, warnings = run_fifo(
        trades,
        apply_two_month_rule=apply_two_month_rule,
        history_end_date=history_end_date,
        snapshot_year=year,
    )
    warnings.extend(warn_same_timestamp_mixed_sides(trades))
    for instrument in instruments.values():
        if instrument.instrument_type and instrument.instrument_type.upper() not in {"COMMON", "ADR"}:
            warnings.append(
                f"Instrumento no accion comun detectado en IBKR: {instrument.symbol} ({instrument.isin}) tipo {instrument.instrument_type}. Revisar tratamiento fiscal manualmente."
            )
    max_trade_date = max((trade.trade_dt.date() for trade in trades), default=None)
    if history_end_date is not None and max_trade_date is not None and history_end_date < max_trade_date:
        warnings.append(
            f"--history-end-date {history_end_date.isoformat()} es anterior a la ultima operacion del CSV ({max_trade_date.isoformat()}). Revisa la cobertura del historico."
        )
    if history_end_date is None:
        warnings.append(
            "No se ha indicado --history-end-date. Para ventas cercanas a final de ejercicio puede faltar cobertura suficiente para validar recompras posteriores."
        )
    return Analysis(
        trades=trades,
        cash_movements=cash_movements,
        instruments=instruments,
        report_paths=report_paths,
        disposals=disposals,
        open_lots=open_lots,
        open_lots_at_year_end=open_lots_at_year_end,
        open_lots_at_history_end=open_lots_at_history_end,
        warnings=warnings,
        ecb_rates_used=ecb_rates_used,
        ibkr_rates_used=ibkr_rates_used,
        fx_mode="ecb",
        fx_mode_requested="ecb",
        apply_two_month_rule=apply_two_month_rule,
        corporate_action_alerts=analyze_corporate_actions(cash_movements, year),
        history_end_date=history_end_date or max((trade.trade_dt.date() for trade in trades), default=None),
        history_end_date_declared=history_end_date is not None,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze one or more Interactive Brokers annual activity CSV reports and produce IRPF support reports.")
    parser.add_argument(
        "--ibkr-report",
        "--report",
        dest="ibkr_reports",
        required=True,
        nargs="+",
        type=Path,
        help="Path(s) to Interactive Brokers annual activity CSV report(s). Pass all years needed for FIFO history.",
    )
    parser.add_argument("--year", required=True, type=int, help="Tax year to report")
    parser.add_argument("--output", type=Path, help="Output Markdown file")
    parser.add_argument("--excel-output", type=Path, help="Optional output Excel .xlsx file")
    parser.add_argument(
        "--carry-income-losses",
        type=d,
        default=Decimal("0"),
        help="Negative savings capital income from prior years still pending compensation at 1 January of the tax year",
    )
    parser.add_argument(
        "--carry-gains-losses",
        type=d,
        default=Decimal("0"),
        help="Negative capital gains/losses from prior years still pending compensation at 1 January of the tax year",
    )
    parser.add_argument(
        "--carryover-json",
        type=Path,
        help="Optional JSON file with income_losses and gains_losses keys",
    )
    parser.add_argument(
        "--savings-tax-rate-hint",
        type=d,
        help="Optional decimal rate to estimate the maximum usable foreign-tax credit, for example 0.19",
    )
    parser.add_argument(
        "--history-end-date",
        type=date.fromisoformat,
        help="Last date covered by the exported IBKR history, YYYY-MM-DD. Used to decide whether future repurchase windows are fully covered.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    analysis = build_analysis(
        args.ibkr_reports,
        args.year,
        history_end_date=args.history_end_date,
    )
    carryovers = load_carryover_input(args.carry_income_losses, args.carry_gains_losses, args.carryover_json)
    report = render_report(
        analysis,
        args.year,
        args.ibkr_reports,
        carryovers,
        args.savings_tax_rate_hint,
    )
    excel_output = args.excel_output
    if excel_output is None and args.output is not None:
        excel_output = args.output.with_suffix(".xlsx")
    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"Informe generado en {args.output}")
    else:
        print(report)
    if excel_output is not None:
        render_excel_report(
            excel_output,
            analysis,
            args.year,
            args.ibkr_reports,
            carryovers,
            args.savings_tax_rate_hint,
        )
        print(f"Excel generado en {excel_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
