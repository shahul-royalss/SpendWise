"""Calendar month helpers.

A month is always represented by the ``date`` of its first day, which is also
how ``Budget.month_year`` is stored.
"""

from datetime import date, datetime

from django.utils import timezone

MIN_YEAR = 1900
MAX_YEAR = 2100


def first_day_of_month(value: date) -> date:
    return value.replace(day=1)


def current_month() -> date:
    """First day of the current month in the configured time zone."""
    return first_day_of_month(timezone.localdate())


def add_months(month: date, offset: int) -> date:
    """Shift ``month`` by ``offset`` months (negative goes back) and return the 1st."""
    index = month.year * 12 + (month.month - 1) + offset
    return date(index // 12, index % 12 + 1, 1)


def month_bounds(month: date) -> tuple[date, date]:
    """Return ``(first day, first day of the next month)``, a half-open range."""
    start = first_day_of_month(month)
    return start, add_months(start, 1)


def parse_month(value: str | None) -> date | None:
    """Parse ``YYYY-MM`` as sent by ``<input type="month">``.

    Returns ``None`` for anything missing, malformed or outside the supported
    year range, so callers can fall back to a default.
    """
    if not value:
        return None
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m").date()
    except ValueError:
        return None
    if not MIN_YEAR <= parsed.year <= MAX_YEAR:
        return None
    return parsed
