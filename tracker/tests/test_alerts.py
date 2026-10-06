"""Threshold alert logic: Normal below 80%, Warning from 80%, Danger from 100%."""

from decimal import Decimal

from django.test import SimpleTestCase

from tracker.services import (
    DANGER_THRESHOLD,
    WARNING_THRESHOLD,
    AlertLevel,
    get_alert_level,
    usage_percentage,
)


class AlertLevelTests(SimpleTestCase):
    def assert_level(self, spent, limit, expected):
        level = get_alert_level(Decimal(spent), Decimal(limit))
        self.assertIs(level, expected, f"{spent} of {limit} gave {level}")

    def test_thresholds_are_80_and_100_percent(self):
        self.assertEqual(WARNING_THRESHOLD, Decimal("80"))
        self.assertEqual(DANGER_THRESHOLD, Decimal("100"))

    def test_below_80_percent_is_normal(self):
        for spent in ("0.00", "0.01", "50.00", "79.99"):
            with self.subTest(spent=spent):
                self.assert_level(spent, "100.00", AlertLevel.NORMAL)

    def test_exactly_80_percent_is_warning(self):
        self.assert_level("80.00", "100.00", AlertLevel.WARNING)

    def test_between_80_and_100_percent_is_warning(self):
        for spent in ("80.01", "90.00", "99.99"):
            with self.subTest(spent=spent):
                self.assert_level(spent, "100.00", AlertLevel.WARNING)

    def test_exactly_100_percent_is_danger(self):
        self.assert_level("100.00", "100.00", AlertLevel.DANGER)

    def test_over_100_percent_is_danger(self):
        for spent in ("100.01", "250.00"):
            with self.subTest(spent=spent):
                self.assert_level(spent, "100.00", AlertLevel.DANGER)

    def test_boundaries_are_exact_for_uneven_limits(self):
        cases = [
            ("399.99", "500.00", AlertLevel.NORMAL),
            ("400.00", "500.00", AlertLevel.WARNING),  # exactly 80%
            ("2.39", "3.00", AlertLevel.NORMAL),
            ("2.40", "3.00", AlertLevel.WARNING),  # exactly 80%
            ("26.66", "33.33", AlertLevel.NORMAL),  # 79.99%
            ("26.67", "33.33", AlertLevel.WARNING),  # 80.02%
            ("33.32", "33.33", AlertLevel.WARNING),
            ("33.33", "33.33", AlertLevel.DANGER),
        ]
        for spent, limit, expected in cases:
            with self.subTest(spent=spent, limit=limit):
                self.assert_level(spent, limit, expected)

    def test_missing_limit_means_no_budget(self):
        self.assertIs(get_alert_level(Decimal("10.00"), None), AlertLevel.NO_BUDGET)

    def test_zero_limit_is_treated_as_no_budget(self):
        self.assertIs(get_alert_level(Decimal("10.00"), Decimal("0")), AlertLevel.NO_BUDGET)


class UsagePercentageTests(SimpleTestCase):
    def test_simple_percentages(self):
        self.assertEqual(usage_percentage(Decimal("50"), Decimal("200")), Decimal("25.0"))
        self.assertEqual(usage_percentage(Decimal("80"), Decimal("100")), Decimal("80.0"))
        self.assertEqual(usage_percentage(Decimal("150"), Decimal("100")), Decimal("150.0"))

    def test_rounds_down_so_thresholds_are_never_overstated(self):
        self.assertEqual(usage_percentage(Decimal("79.99"), Decimal("100")), Decimal("79.9"))
        self.assertEqual(usage_percentage(Decimal("99.99"), Decimal("100")), Decimal("99.9"))
        self.assertEqual(usage_percentage(Decimal("2"), Decimal("3")), Decimal("66.6"))

    def test_rejects_a_limit_that_is_not_positive(self):
        for limit in ("0", "-1"):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                usage_percentage(Decimal("10"), Decimal(limit))


class AlertLevelPresentationTests(SimpleTestCase):
    def test_each_level_maps_to_a_bootstrap_style(self):
        expected = {
            AlertLevel.NO_BUDGET: ("No budget", "secondary"),
            AlertLevel.NORMAL: ("Normal", "success"),
            AlertLevel.WARNING: ("Warning", "warning"),
            AlertLevel.DANGER: ("Danger", "danger"),
        }
        for level, (label, css_class) in expected.items():
            with self.subTest(level=level):
                self.assertEqual(level.label, label)
                self.assertEqual(level.css_class, css_class)
                self.assertTrue(level.icon)

    def test_string_value_is_usable_in_templates(self):
        self.assertEqual(str(AlertLevel.WARNING), "warning")
        self.assertEqual(AlertLevel.DANGER, "danger")
