from decimal import ROUND_HALF_UP, Decimal

from django import template
from django.conf import settings

from tracker.money import ZERO, format_currency
from tracker.services import DANGER_THRESHOLD

register = template.Library()

# Identity colours for categories (avatars, legends, chart segments). They are
# deliberately not the green / amber / red used for budget states.
CATEGORY_PALETTE = (
    "#6366f1",
    "#06b6d4",
    "#8b5cf6",
    "#ec4899",
    "#14b8a6",
    "#0ea5e9",
    "#d946ef",
    "#84cc16",
    "#f97316",
    "#64748b",
)
SEGMENT_GAP = Decimal("0.8")


@register.filter
def currency(value):
    """Render a number as money: ``{{ amount|currency }}`` -> ``₹1,234.50``."""
    return format_currency(value)


@register.simple_tag
def currency_symbol():
    return settings.CURRENCY_SYMBOL


@register.filter
def category_color(category):
    """Stable colour for a category, so it looks the same on every page."""
    return CATEGORY_PALETTE[(getattr(category, "pk", None) or 0) % len(CATEGORY_PALETTE)]


@register.inclusion_tag("tracker/partials/alert_badge.html")
def alert_badge(level):
    """Coloured status badge for an ``AlertLevel``."""
    return {"level": level}


@register.inclusion_tag("tracker/partials/progress_ring.html")
def progress_ring(percentage, level, size="md"):
    """Circular usage indicator; the ring is capped at 100% but the label is not."""
    value = min(percentage, DANGER_THRESHOLD) if percentage is not None else ZERO
    return {"percentage": percentage, "value": value, "level": level, "size": size}


@register.inclusion_tag("tracker/partials/spending_donut.html")
def spending_donut(summary):
    """Donut chart of the month's spending split by category."""
    segments = []
    offset = ZERO
    spending_rows = sorted(
        (row for row in summary.rows if row.spent > 0), key=lambda row: row.spent, reverse=True
    )
    for row in spending_rows:
        length = row.share
        visible = (
            length - SEGMENT_GAP if len(spending_rows) > 1 and length > 2 * SEGMENT_GAP else length
        )
        segments.append(
            {
                "row": row,
                "color": category_color(row.category),
                "length": visible,
                "gap": 100 - visible,
                "offset": -offset,
            }
        )
        offset += length
    return {
        "segments": segments,
        "total": summary.total_spent,
        "symbol": settings.CURRENCY_SYMBOL,
    }


@register.inclusion_tag("tracker/partials/trend_chart.html")
def trend_chart(points, selected_month):
    """Bar chart of monthly spending with a dashed marker for each month's budget."""
    peak = max((max(point.spent, point.budget) for point in points), default=ZERO)
    bars = [
        {
            "point": point,
            "height": _percent_of(point.spent, peak),
            "budget_height": _percent_of(point.budget, peak) if point.budget else None,
            "is_selected": point.month == selected_month,
        }
        for point in points
    ]
    return {"bars": bars, "has_data": peak > 0}


def _percent_of(value, peak):
    if not peak:
        return 0
    return int((value * 100 / peak).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
