from decimal import Decimal

from django.template import Context, Template
from django.test import SimpleTestCase, override_settings

from tracker.money import format_currency, to_money
from tracker.services import AlertLevel


class ToMoneyTests(SimpleTestCase):
    def test_none_is_zero(self):
        self.assertEqual(to_money(None), Decimal("0.00"))

    def test_float_noise_from_sqlite_sums_is_removed(self):
        self.assertEqual(to_money(0.1 + 0.2), Decimal("0.30"))
        self.assertEqual(to_money(sum([0.1] * 10)), Decimal("1.00"))

    def test_decimals_are_rounded_to_cents(self):
        self.assertEqual(to_money(Decimal("45.5")), Decimal("45.50"))


@override_settings(CURRENCY_SYMBOL="₹")
class FormatCurrencyTests(SimpleTestCase):
    def test_symbol_grouping_and_two_decimals(self):
        self.assertEqual(format_currency(Decimal("1234.5")), "₹1,234.50")
        self.assertEqual(format_currency(Decimal("0")), "₹0.00")

    def test_negative_amounts(self):
        self.assertEqual(format_currency(Decimal("-20")), "-₹20.00")

    def test_missing_values(self):
        self.assertEqual(format_currency(None), "-")
        self.assertEqual(format_currency(""), "-")

    def test_non_numeric_values_are_returned_unchanged(self):
        self.assertEqual(format_currency("abc"), "abc")

    @override_settings(CURRENCY_SYMBOL="$")
    def test_symbol_is_configurable(self):
        self.assertEqual(format_currency(5), "$5.00")


@override_settings(CURRENCY_SYMBOL="₹")
class TemplateTagTests(SimpleTestCase):
    def render(self, source, **context):
        return Template("{% load tracker_extras %}" + source).render(Context(context))

    def test_currency_filter(self):
        self.assertEqual(self.render("{{ value|currency }}", value=Decimal("45.5")), "₹45.50")

    def test_alert_badge_tag(self):
        html = self.render("{% alert_badge level %}", level=AlertLevel.WARNING)
        self.assertIn("text-bg-warning", html)
        self.assertIn("Warning", html)
