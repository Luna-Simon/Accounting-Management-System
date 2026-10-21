import math
from decimal import Decimal, ROUND_HALF_UP


def cln(val):
    if val is None:
        return 0.0
    if isinstance(val, str):
        t = val.strip().replace(",", "")
        if not t or t.lower() in {"nan", "na", "n/a", "null"}:
            return 0.0
        try:
            return float(t)
        except ValueError:
            return 0.0
    if isinstance(val, (float, int)):
        if isinstance(val, float) and math.isnan(val):
            return 0.0
        return float(val)
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def to_cents(val):
    amt = Decimal(str(cln(val)))
    return int((amt * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def fix_balance(rows):
    ledger = []
    for row in rows:
        e = dict(row)
        e["debit"] = to_cents(e.get("debit", 0))
        e["credit"] = to_cents(e.get("credit", 0))
        ledger.append(e)

    if not ledger:
        return []

    total_dr = sum(int(l["debit"]) for l in ledger)
    total_cr = sum(int(l["credit"]) for l in ledger)
    if total_dr == total_cr:
        return ledger

    diff = total_dr - total_cr
    if diff > 0:
        ledger[-1]["credit"] = int(ledger[-1].get("credit", 0)) + diff
    else:
        ledger[-1]["debit"] = int(ledger[-1].get("debit", 0)) + abs(diff)
    return ledger
