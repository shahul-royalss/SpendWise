from datetime import date
from decimal import Decimal

from django.contrib.messages import get_messages
from django.test import TestCase, override_settings
from django.urls import reverse

from tracker.dates import current_month
from tracker.models import Budget, Expense

from .factories import MONTH, create_budget, create_category, create_expense, create_user

SEPTEMBER = date(2026, 9, 1)


@override_settings(CURRENCY_SYMBOL="₹")
class BudgetViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user("alice")
        cls.food = create_category(cls.user, "Food")
        cls.transport = create_category(cls.user, "Transport")

    def setUp(self):
        self.client.force_login(self.user)

    def test_list_shows_the_selected_month_only(self):
        create_budget(self.user, self.food, "500.00", MONTH)
        create_budget(self.user, self.food, "321.00", SEPTEMBER)
        create_expense(self.user, self.food, "420.00", date(2026, 10, 3))
        response = self.client.get(reverse("tracker:budget_list"), {"month": "2026-10"})
        self.assertContains(response, "October 2026")
        self.assertContains(response, "₹500.00")
        self.assertContains(response, "₹80.00")
        self.assertNotContains(response, "₹321.00")
        self.assertContains(response, "text-bg-warning")
        self.assertEqual(
            [row.category for row in response.context["summary"].unbudgeted_rows], [self.transport]
        )

    def test_list_defaults_to_the_current_month(self):
        create_budget(self.user, self.food, "654.00", current_month())
        response = self.client.get(reverse("tracker:budget_list"))
        self.assertEqual(response.context["month"], current_month())
        self.assertContains(response, "₹654.00")

    def test_create_form_is_prefilled_from_the_query_string(self):
        response = self.client.get(
            reverse("tracker:budget_create"), {"month": "2026-10", "category": self.food.pk}
        )
        initial = response.context["form"].initial
        self.assertEqual(initial["month_year"], MONTH)
        self.assertEqual(initial["category"], str(self.food.pk))

    def test_create_budget_redirects_to_its_month(self):
        response = self.client.post(
            reverse("tracker:budget_create"),
            {"category": self.food.pk, "month_year": "2026-10", "monthly_limit": "500.00"},
        )
        self.assertRedirects(response, "/budgets/?month=2026-10")
        budget = Budget.objects.get()
        self.assertEqual((budget.user, budget.month_year), (self.user, MONTH))

    def test_duplicate_budget_returns_200(self):
        create_budget(self.user, self.food, "500.00", MONTH)
        response = self.client.post(
            reverse("tracker:budget_create"),
            {"category": self.food.pk, "month_year": "2026-10", "monthly_limit": "100.00"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already has a budget for October 2026")
        self.assertEqual(Budget.objects.count(), 1)

    def test_update_budget_limit(self):
        budget = create_budget(self.user, self.food, "500.00", MONTH)
        response = self.client.post(
            reverse("tracker:budget_update", args=[budget.pk]),
            {"category": self.food.pk, "month_year": "2026-10", "monthly_limit": "750.00"},
        )
        self.assertRedirects(response, "/budgets/?month=2026-10")
        budget.refresh_from_db()
        self.assertEqual(budget.monthly_limit, Decimal("750.00"))

    def test_delete_budget_keeps_expenses(self):
        budget = create_budget(self.user, self.food, "500.00", MONTH)
        create_expense(self.user, self.food)
        response = self.client.post(reverse("tracker:budget_delete", args=[budget.pk]))
        self.assertRedirects(response, "/budgets/?month=2026-10")
        self.assertFalse(Budget.objects.exists())
        self.assertEqual(Expense.objects.count(), 1)

    def test_copy_from_previous_month(self):
        create_budget(self.user, self.food, "500.00", SEPTEMBER)
        create_budget(self.user, self.transport, "200.00", SEPTEMBER)
        list_page = self.client.get(reverse("tracker:budget_list"), {"month": "2026-10"})
        self.assertContains(list_page, "Copy budgets from September 2026")

        response = self.client.post(reverse("tracker:budget_copy"), {"month": "2026-10"})
        self.assertRedirects(response, "/budgets/?month=2026-10")
        self.assertEqual(Budget.objects.for_month(MONTH).count(), 2)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Copied 2 budget(s) from September 2026.", messages)

    def test_copy_with_nothing_to_copy(self):
        response = self.client.post(reverse("tracker:budget_copy"), {"month": "2026-10"})
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Every category already has a budget, so nothing was copied.", messages)

    def test_copy_only_accepts_post(self):
        self.assertEqual(self.client.get(reverse("tracker:budget_copy")).status_code, 405)
