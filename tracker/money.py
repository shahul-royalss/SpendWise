"""Decimal helpers for money values."""

from decimal import Decimal, InvalidOperation

from django.conf import settings

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def to_money(value) -> Decimal:
    """Round to two decimal places; ``None`` counts as zero.

    SQLite returns SUM() over decimal columns as a float, so totals are
    rounded back to cents before they are compared or displayed.
    """
    if value is None:
        return ZERO
    return Decimal(str(value)).quantize(CENT)


def format_currency(value) -> str:
    """Format a number as money, e.g. ``1234.5`` -> ``₹1,234.50``."""
    if value is None or value == "":
        return "-"
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        return str(value)
    sign = "-" if amount < 0 else ""
    return f"{sign}{settings.CURRENCY_SYMBOL}{abs(amount):,.2f}"
