from datetime import date
from unittest import mock

from django.test import SimpleTestCase

from tracker.dates import add_months, current_month, first_day_of_month, month_bounds, parse_month


class MonthHelperTests(SimpleTestCase):
    def test_first_day_of_month(self):
        self.assertEqual(first_day_of_month(date(2026, 10, 17)), date(2026, 10, 1))

    def test_add_months(self):
        cases = [
            (date(2026, 10, 1), 1, date(2026, 11, 1)),
            (date(2026, 12, 1), 1, date(2027, 1, 1)),
            (date(2026, 1, 1), -1, date(2025, 12, 1)),
            (date(2026, 12, 1), 13, date(2028, 1, 1)),
            (date(2026, 3, 1), -15, date(2024, 12, 1)),
            (date(2026, 5, 31), 0, date(2026, 5, 1)),
        ]
        for month, offset, expected in cases:
            with self.subTest(month=month, offset=offset):
                self.assertEqual(add_months(month, offset), expected)

    def test_month_bounds_are_half_open(self):
        self.assertEqual(month_bounds(date(2026, 2, 10)), (date(2026, 2, 1), date(2026, 3, 1)))
        self.assertEqual(month_bounds(date(2026, 12, 31)), (date(2026, 12, 1), date(2027, 1, 1)))

    def test_parse_month_accepts_year_and_month(self):
        self.assertEqual(parse_month("2026-10"), date(2026, 10, 1))
        self.assertEqual(parse_month(" 2026-03 "), date(2026, 3, 1))

    def test_parse_month_rejects_bad_input(self):
        for value in (None, "", "2026-13", "abc", "2026/10", "10-2026", "2026-10-05"):
            with self.subTest(value=value):
                self.assertIsNone(parse_month(value))

    def test_parse_month_rejects_years_out_of_range(self):
        self.assertIsNone(parse_month("1899-12"))
        self.assertIsNone(parse_month("2101-01"))

    def test_current_month_uses_the_local_date(self):
        with mock.patch("tracker.dates.timezone.localdate", return_value=date(2026, 10, 6)):
            self.assertEqual(current_month(), date(2026, 10, 1))
