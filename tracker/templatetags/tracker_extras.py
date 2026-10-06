from django import template

from tracker.money import format_currency

register = template.Library()


@register.filter
def currency(value):
    """Render a number as money: ``{{ amount|currency }}`` -> ``₹1,234.50``."""
    return format_currency(value)


@register.inclusion_tag("tracker/partials/alert_badge.html")
def alert_badge(level):
    """Coloured status badge for an ``AlertLevel``."""
    return {"level": level}
