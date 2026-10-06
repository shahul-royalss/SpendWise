from datetime import date
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from tracker.dates import current_month
from tracker.services import AlertLevel

from .factories import create_budget, create_category, create_expense, create_user


@override_settings(CURRENCY_SYMBOL="₹")
class DashboardViewTests(TestCase):
    """October 2026: Food 84% (warning), Transport 115% (danger), Utilities 10% (normal),
    Health has no budget."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user("alice")
        food = create_category(cls.user, "Food")
        transport = create_category(cls.user, "Transport")
        utilities = create_category(cls.user, "Utilities")
        health = create_category(cls.user, "Health")
        create_budget(cls.user, food, "500.00")
        create_budget(cls.user, transport, "200.00")
        create_budget(cls.user, utilities, "1000.00")
        create_expense(cls.user, food, "420.00", date(2026, 10, 3), "Groceries")
        create_expense(cls.user, transport, "230.00", date(2026, 10, 4), "Fuel")
        create_expense(cls.user, utilities, "100.00", date(2026, 10, 5), "Internet")
        create_expense(cls.user, health, "50.00", date(2026, 10, 6), "Pharmacy")

    def setUp(self):
        self.client.force_login(self.user)

    def get(self, month="2026-10"):
        return self.client.get(reverse("tracker:dashboard"), {"month": month})

    def test_shows_monthly_totals(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        summary = response.context["summary"]
        self.assertEqual(summary.total_spent, Decimal("800.00"))
        self.assertEqual(summary.total_budget, Decimal("1700.00"))
        self.assertEqual(summary.remaining_budget, Decimal("950.00"))
        self.assertContains(response, "₹800.00")
        self.assertContains(response, "₹1,700.00")
        self.assertContains(response, "₹950.00")
        self.assertEqual(response.context["expense_count"], 4)

    def test_shows_remaining_budget_per_category(self):
        response = self.get()
        remaining = {row.category.name: row.remaining for row in response.context["summary"].rows}
        self.assertEqual(
            remaining,
            {
                "Food": Decimal("80.00"),
                "Health": None,
                "Transport": Decimal("-30.00"),
                "Utilities": Decimal("900.00"),
            },
        )
        self.assertContains(response, "-₹30.00")
        self.assertContains(response, "₹900.00")

    def test_badge_for_every_alert_state(self):
        response = self.get()
        levels = {row.category.name: row.alert_level for row in response.context["summary"].rows}
        self.assertEqual(
            levels,
            {
                "Food": AlertLevel.WARNING,
                "Health": AlertLevel.NO_BUDGET,
                "Transport": AlertLevel.DANGER,
                "Utilities": AlertLevel.NORMAL,
            },
        )
        for css_class in (
            "text-bg-success",
            "text-bg-warning",
            "text-bg-danger",
            "text-bg-secondary",
        ):
            self.assertContains(response, css_class)

    def test_alert_banners_worst_first(self):
        response = self.get()
        self.assertContains(response, "is over budget by ₹30.00 (115.0% used).")
        self.assertContains(response, "has used 84.0% of its budget, ₹80.00 left.")
        html = response.content.decode()
        self.assertLess(
            html.index("<strong>Transport</strong>"), html.index("<strong>Food</strong>")
        )

    def test_unbudgeted_spending_is_explained(self):
        self.assertContains(self.get(), "Spending in categories without one this month")

    def test_month_navigation(self):
        response = self.get()
        self.assertContains(response, "month=2026-09")
        self.assertContains(response, "month=2026-11")
        self.assertContains(response, "October 2026")

    def test_another_month_has_its_own_numbers(self):
        summary = self.get("2026-09").context["summary"]
        self.assertEqual(summary.total_spent, Decimal("0.00"))
        self.assertEqual(summary.total_budget, Decimal("0.00"))

    def test_defaults_to_the_current_month(self):
        response = self.client.get(reverse("tracker:dashboard"))
        self.assertEqual(response.context["month"], current_month())
        self.assertTrue(response.context["is_current_month"])

    def test_invalid_month_falls_back_to_the_current_month(self):
        self.assertEqual(self.get("not-a-month").context["month"], current_month())

    def test_recent_expenses_are_limited_to_five(self):
        food = self.user.categories.get(name="Food")
        for day in range(10, 15):
            create_expense(self.user, food, "1.00", date(2026, 10, day))
        response = self.get()
        self.assertEqual(len(response.context["recent_expenses"]), 5)

    def test_new_user_sees_an_empty_state(self):
        self.client.force_login(create_user("newbie"))
        response = self.client.get(reverse("tracker:dashboard"))
        self.assertContains(response, "Create your first category")
