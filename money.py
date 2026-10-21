from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def parse(txt):
    cleaned = txt.replace(",", "").strip()
    if not cleaned:
        return 0
    try:
        value = Decimal(cleaned)
        if not value.is_finite():
            raise InvalidOperation
    except InvalidOperation:
        raise ValueError(f"'{txt.strip()}' is not a valid amount.") from None
    return int((value * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def fmt(cents, blank_zero=True):
    if cents == 0:
        return "" if blank_zero else "0.00"
    text = f"{abs(cents) / 100:,.2f}"
    return f"({text})" if cents < 0 else text
