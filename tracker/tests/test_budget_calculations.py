"""Budget calculations: monthly spending, remaining budget, totals and copying."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from tracker.models import Budget
from tracker.services import (
    AlertLevel,
    copy_previous_month_budgets,
    get_category_spending,
    get_monthly_summary,
)

from .factories import MONTH, create_budget, create_category, create_expense, create_user


class MonthlySummaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user("alice")
        cls.other = create_user("bob")
        cls.food = create_category(cls.user, "Food")
        cls.transport = create_category(cls.user, "Transport")
        cls.health = create_category(cls.user, "Health")

    def summary(self):
        return get_monthly_summary(self.user, MONTH)

    def row(self, category, summary=None):
        summary = summary or self.summary()
        return next(row for row in summary.rows if row.category == category)

    def test_only_expenses_inside_the_month_are_counted(self):
        create_expense(self.user, self.food, "1.00", date(2026, 9, 30))
        create_expense(self.user, self.food, "10.00", date(2026, 10, 1))
        create_expense(self.user, self.food, "20.00", date(2026, 10, 31))
        create_expense(self.user, self.food, "5.00", date(2026, 11, 1))
        self.assertEqual(self.row(self.food).spent, Decimal("30.00"))

    def test_other_users_data_is_ignored(self):
        their_food = create_category(self.other, "Food")
        create_budget(self.other, their_food, "10.00")
        create_expense(self.other, their_food, "999.00")
        summary = self.summary()
        self.assertEqual(
            [row.category for row in summary.rows], [self.food, self.health, self.transport]
        )
        self.assertEqual(summary.total_spent, Decimal("0.00"))
        self.assertEqual(summary.total_budget, Decimal("0.00"))

    def test_remaining_and_percentage_in_the_warning_zone(self):
        create_budget(self.user, self.food, "500.00")
        create_expense(self.user, self.food, "420.00")
        row = self.row(self.food)
        self.assertEqual(row.limit, Decimal("500.00"))
        self.assertEqual(row.spent, Decimal("420.00"))
        self.assertEqual(row.remaining, Decimal("80.00"))
        self.assertEqual(row.overspent, Decimal("0.00"))
        self.assertEqual(row.percentage, Decimal("84.0"))
        self.assertEqual(row.progress, 84)
        self.assertIs(row.alert_level, AlertLevel.WARNING)

    def test_over_budget_category(self):
        create_budget(self.user, self.transport, "200.00")
        create_expense(self.user, self.transport, "150.00", date(2026, 10, 2))
        create_expense(self.user, self.transport, "80.00", date(2026, 10, 9))
        row = self.row(self.transport)
        self.assertEqual(row.spent, Decimal("230.00"))
        self.assertEqual(row.remaining, Decimal("-30.00"))
        self.assertEqual(row.overspent, Decimal("30.00"))
        self.assertEqual(row.percentage, Decimal("115.0"))
        self.assertEqual(row.progress, 100)
        self.assertIs(row.alert_level, AlertLevel.DANGER)

    def test_spending_exactly_the_limit_is_danger(self):
        create_budget(self.user, self.food, "100.00")
        create_expense(self.user, self.food, "60.00")
        create_expense(self.user, self.food, "40.00")
        row = self.row(self.food)
        self.assertEqual(row.remaining, Decimal("0.00"))
        self.assertEqual(row.percentage, Decimal("100.0"))
        self.assertIs(row.alert_level, AlertLevel.DANGER)

    def test_category_without_a_budget(self):
        create_expense(self.user, self.health, "50.00")
        row = self.row(self.health)
        self.assertFalse(row.has_budget)
        self.assertIsNone(row.limit)
        self.assertIsNone(row.remaining)
        self.assertIsNone(row.percentage)
        self.assertEqual(row.progress, 0)
        self.assertIs(row.alert_level, AlertLevel.NO_BUDGET)

    def test_budget_from_another_month_does_not_apply(self):
        create_budget(self.user, self.food, "100.00", date(2026, 9, 1))
        create_expense(self.user, self.food, "90.00")
        self.assertIs(self.row(self.food).alert_level, AlertLevel.NO_BUDGET)

    def test_totals_remaining_budget_and_alert_order(self):
        create_budget(self.user, self.food, "500.00")
        create_budget(self.user, self.transport, "200.00")
        create_expense(self.user, self.food, "420.00")
        create_expense(self.user, self.transport, "230.00")
        create_expense(self.user, self.health, "50.00")

        summary = self.summary()
        self.assertEqual(summary.total_spent, Decimal("700.00"))
        self.assertEqual(summary.total_budget, Decimal("700.00"))
        self.assertEqual(summary.budgeted_spent, Decimal("650.00"))
        self.assertEqual(summary.unbudgeted_spent, Decimal("50.00"))
        self.assertEqual(summary.remaining_budget, Decimal("50.00"))
        self.assertEqual(summary.overall_percentage, Decimal("92.8"))
        self.assertIs(summary.overall_alert_level, AlertLevel.WARNING)
        self.assertEqual(summary.danger_count, 1)
        self.assertEqual(summary.warning_count, 1)
        self.assertEqual([row.category for row in summary.alerts], [self.transport, self.food])
        self.assertEqual([row.category for row in summary.unbudgeted_rows], [self.health])

    def test_share_of_monthly_spending(self):
        create_expense(self.user, self.food, "75.00")
        create_expense(self.user, self.transport, "25.00")
        summary = self.summary()
        self.assertEqual(self.row(self.food, summary).share, Decimal("75.0"))
        self.assertEqual(self.row(self.transport, summary).share, Decimal("25.0"))
        self.assertEqual(self.row(self.health, summary).share, Decimal("0.00"))

    def test_empty_month(self):
        summary = self.summary()
        self.assertEqual(summary.month, MONTH)
        self.assertEqual(summary.total_spent, Decimal("0.00"))
        self.assertEqual(summary.remaining_budget, Decimal("0.00"))
        self.assertIsNone(summary.overall_percentage)
        self.assertIs(summary.overall_alert_level, AlertLevel.NO_BUDGET)
        self.assertEqual(summary.alerts, [])

    def test_many_small_amounts_add_up_exactly(self):
        create_budget(self.user, self.food, "1.00")
        for _ in range(10):
            create_expense(self.user, self.food, "0.10")
        row = self.row(self.food)
        self.assertEqual(row.spent, Decimal("1.00"))
        self.assertIs(row.alert_level, AlertLevel.DANGER)

    def test_summary_uses_a_fixed_number_of_queries(self):
        for category in (self.food, self.transport, self.health):
            create_budget(self.user, category, "100.00")
            create_expense(self.user, category, "10.00")
        with self.assertNumQueries(2):
            summary = self.summary()
            [row.alert_level for row in summary.rows]

    def test_month_argument_can_be_any_day_of_the_month(self):
        create_expense(self.user, self.food, "12.00")
        summary = get_monthly_summary(self.user, date(2026, 10, 20))
        self.assertEqual(summary.month, MONTH)
        self.assertEqual(summary.total_spent, Decimal("12.00"))


class CategorySpendingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user("alice")
        cls.food = create_category(cls.user, "Food")

    def test_status_for_a_single_category(self):
        create_budget(self.user, self.food, "100.00")
        create_expense(self.user, self.food, "85.00", date(2026, 10, 3))
        create_expense(self.user, self.food, "50.00", date(2026, 9, 3))
        status = get_category_spending(self.food, date(2026, 10, 20))
        self.assertEqual(status.spent, Decimal("85.00"))
        self.assertEqual(status.remaining, Decimal("15.00"))
        self.assertIs(status.alert_level, AlertLevel.WARNING)

    def test_status_without_budget(self):
        status = get_category_spending(self.food, MONTH)
        self.assertEqual(status.spent, Decimal("0.00"))
        self.assertIs(status.alert_level, AlertLevel.NO_BUDGET)


class CopyBudgetsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user("alice")
        cls.food = create_category(cls.user, "Food")
        cls.transport = create_category(cls.user, "Transport")
        cls.september = date(2026, 9, 1)

    def test_copies_only_categories_without_a_budget(self):
        create_budget(self.user, self.food, "500.00", self.september)
        create_budget(self.user, self.transport, "200.00", self.september)
        create_budget(self.user, self.transport, "250.00", MONTH)

        self.assertEqual(copy_previous_month_budgets(self.user, MONTH), 1)

        october = {b.category: b.monthly_limit for b in Budget.objects.for_month(MONTH)}
        self.assertEqual(october, {self.food: Decimal("500.00"), self.transport: Decimal("250.00")})

    def test_running_twice_copies_nothing_new(self):
        create_budget(self.user, self.food, "500.00", self.september)
        copy_previous_month_budgets(self.user, MONTH)
        self.assertEqual(copy_previous_month_budgets(self.user, MONTH), 0)
        self.assertEqual(Budget.objects.for_month(MONTH).count(), 1)

    def test_other_users_budgets_are_not_copied(self):
        other = create_user("bob")
        create_budget(other, create_category(other, "Rent"), "9000.00", self.september)
        self.assertEqual(copy_previous_month_budgets(self.user, MONTH), 0)
        self.assertFalse(Budget.objects.for_user(self.user).exists())
