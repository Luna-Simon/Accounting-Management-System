import math
from decimal import Decimal, ROUND_HALF_UP


def clean_float(value):
    if value is None:
        return 0.0
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text or text.lower() in {"nan", "na", "n/a", "null"}:
            return 0.0
        try:
            return float(text)
        except ValueError:
            return 0.0
    if isinstance(value, (float, int)):
        if isinstance(value, float) and math.isnan(value):
            return 0.0
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def scale_money(value):
    amount = Decimal(str(clean_float(value)))
    return int((amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def balance_journal_rows(rows):
    ledger = []
    for row in rows:
        entry = dict(row)
        entry["debit"] = scale_money(entry.get("debit", 0))
        entry["credit"] = scale_money(entry.get("credit", 0))
        ledger.append(entry)

    if not ledger:
        return []

    total_debit = sum(int(line["debit"]) for line in ledger)
    total_credit = sum(int(line["credit"]) for line in ledger)
    if total_debit == total_credit:
        return ledger

    difference = total_debit - total_credit
    if difference > 0:
        ledger[-1]["credit"] = int(ledger[-1].get("credit", 0)) + difference
    else:
        ledger[-1]["debit"] = int(ledger[-1].get("debit", 0)) + abs(difference)
    return ledger
