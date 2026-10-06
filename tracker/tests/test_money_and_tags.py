from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from django.template import Context, Template
from django.test import SimpleTestCase, override_settings

from tracker.money import format_currency, to_money
from tracker.services import AlertLevel, CategorySpending, MonthlySummary, MonthTotal
from tracker.templatetags.tracker_extras import (
    CATEGORY_PALETTE,
    category_color,
    progress_ring,
    spending_donut,
    trend_chart,
)


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


def render(source, **context):
    return Template("{% load tracker_extras %}" + source).render(Context(context))


def spending_row(pk, name, spent, share, limit=None):
    budget = SimpleNamespace(monthly_limit=Decimal(limit)) if limit else None
    return CategorySpending(
        category=SimpleNamespace(pk=pk, name=name),
        spent=Decimal(spent),
        budget=budget,
        share=Decimal(share),
    )


def summary_of(*rows):
    return MonthlySummary(month=date(2026, 10, 1), rows=tuple(rows))


@override_settings(CURRENCY_SYMBOL="₹")
class TemplateTagTests(SimpleTestCase):
    def test_currency_filter_and_symbol(self):
        self.assertEqual(render("{{ value|currency }}", value=Decimal("45.5")), "₹45.50")
        self.assertEqual(render("{% currency_symbol %}"), "₹")

    def test_alert_badge_uses_bootstrap_contextual_colours(self):
        html = render("{% alert_badge level %}", level=AlertLevel.WARNING)
        self.assertIn("bg-warning-subtle", html)
        self.assertIn("text-warning-emphasis", html)
        self.assertIn("Warning", html)

    def test_category_colour_is_stable(self):
        self.assertEqual(
            category_color(SimpleNamespace(pk=3)), category_color(SimpleNamespace(pk=3))
        )
        self.assertIn(category_color(SimpleNamespace(pk=3)), CATEGORY_PALETTE)
        wrapped = SimpleNamespace(pk=len(CATEGORY_PALETTE))
        self.assertEqual(category_color(wrapped), CATEGORY_PALETTE[0])
        self.assertEqual(category_color(None), CATEGORY_PALETTE[0])

    def test_progress_ring_caps_the_ring_but_not_the_label(self):
        self.assertEqual(
            progress_ring(Decimal("115.0"), AlertLevel.DANGER)["value"], Decimal("100")
        )
        html = render(
            "{% progress_ring pct level 'sm' %}", pct=Decimal("115.0"), level=AlertLevel.DANGER
        )
        self.assertIn("115.0%", html)
        self.assertIn("stroke-dasharray: 100 100", html)
        self.assertIn("sw-ring-sm", html)

    def test_progress_ring_without_a_budget(self):
        html = render("{% progress_ring None level %}", level=AlertLevel.NO_BUDGET)
        self.assertIn("No budget set", html)
        self.assertNotIn("sw-ring-value", html)


@override_settings(CURRENCY_SYMBOL="₹")
class ChartTagTests(SimpleTestCase):
    def test_donut_segments_are_largest_first_and_follow_each_other(self):
        summary = summary_of(
            spending_row(1, "Food", "25.00", "25.0"),
            spending_row(2, "Rent", "75.00", "75.0"),
            spending_row(3, "Unused", "0.00", "0"),
        )
        context = spending_donut(summary)
        segments = context["segments"]
        self.assertEqual([s["row"].category.name for s in segments], ["Rent", "Food"])
        self.assertEqual(segments[0]["offset"], 0)
        self.assertEqual(segments[1]["offset"], Decimal("-75.0"))
        self.assertEqual(segments[0]["length"] + segments[0]["gap"], 100)
        self.assertLess(segments[0]["length"], Decimal("75.0"))  # small gap between segments
        self.assertEqual(context["total"], Decimal("100.00"))

    def test_single_category_fills_the_donut(self):
        context = spending_donut(summary_of(spending_row(1, "Food", "40.00", "100.0")))
        self.assertEqual(context["segments"][0]["length"], Decimal("100.0"))

    def test_donut_renders_a_legend(self):
        summary = summary_of(
            spending_row(1, "Food", "25.00", "25.0"), spending_row(2, "Rent", "75.00", "75.0")
        )
        html = render("{% spending_donut summary %}", summary=summary)
        self.assertIn("Rent", html)
        self.assertIn("75.0%", html)
        self.assertIn("₹75.00", html)
        self.assertIn("sw-donut-segment", html)

    def test_donut_without_spending_shows_an_empty_state(self):
        summary = summary_of(spending_row(1, "Food", "0.00", "0"))
        self.assertEqual(spending_donut(summary)["segments"], [])
        self.assertIn(
            "No spending recorded", render("{% spending_donut summary %}", summary=summary)
        )

    def test_trend_bars_scale_to_the_highest_value(self):
        points = [
            MonthTotal(date(2026, 9, 1), Decimal("50.00"), Decimal("100.00")),
            MonthTotal(date(2026, 10, 1), Decimal("200.00"), Decimal("150.00")),
        ]
        context = trend_chart(points, date(2026, 10, 1))
        bars = context["bars"]
        self.assertTrue(context["has_data"])
        self.assertEqual([bar["height"] for bar in bars], [25, 100])
        self.assertEqual([bar["budget_height"] for bar in bars], [50, 75])
        self.assertEqual([bar["is_selected"] for bar in bars], [False, True])
        self.assertTrue(points[1].is_over_budget)
        self.assertFalse(points[0].is_over_budget)

    def test_trend_without_any_data(self):
        points = [MonthTotal(date(2026, 10, 1), Decimal("0.00"), Decimal("0.00"))]
        context = trend_chart(points, date(2026, 10, 1))
        self.assertFalse(context["has_data"])
        self.assertIsNone(context["bars"][0]["budget_height"])
        self.assertIn(
            "spending history", render("{% trend_chart points month %}", points=points, month=None)
        )
