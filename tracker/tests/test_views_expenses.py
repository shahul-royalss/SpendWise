from datetime import date
from decimal import Decimal

from django.contrib.messages import get_messages
from django.test import TestCase, override_settings
from django.urls import reverse

from tracker.models import Expense

from .factories import create_budget, create_category, create_expense, create_user

CREATE_URL = "/expenses/create/"


def message_texts(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


@override_settings(CURRENCY_SYMBOL="₹")
class ExpenseCreateViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user("alice")
        cls.food = create_category(cls.user, "Food")

    def setUp(self):
        self.client.force_login(self.user)

    def post(self, **overrides):
        data = {
            "amount": "45.50",
            "date": "2023-10-15",
            "category": "Food",
            "notes": "Lunch with client",
        }
        data.update(overrides)
        return self.client.post(CREATE_URL, data)

    def test_url_matches_the_spec(self):
        self.assertEqual(reverse("tracker:expense_create"), CREATE_URL)

    def test_get_shows_the_form(self):
        response = self.client.get(CREATE_URL)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tracker/expense_form.html")
        self.assertContains(response, 'name="amount"')

    def test_spec_example_redirects_to_dashboard_with_302(self):
        response = self.post()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("tracker:dashboard"))

        expense = Expense.objects.get()
        self.assertEqual(expense.user, self.user)
        self.assertEqual(expense.amount, Decimal("45.50"))
        self.assertEqual(expense.date, date(2023, 10, 15))
        self.assertEqual(expense.category, self.food)
        self.assertEqual(expense.notes, "Lunch with client")
        self.assertIn("Saved ₹45.50 under Food.", message_texts(response))

    def test_category_id_works_too(self):
        response = self.post(category=str(self.food.pk), notes="")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Expense.objects.get().notes, "")

    def test_negative_amount_returns_200_with_errors(self):
        response = self.post(amount="-5")
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "amount", "Amount must be greater than zero."
        )
        self.assertContains(response, "Amount must be greater than zero.")
        self.assertFalse(Expense.objects.exists())

    def test_zero_amount_returns_200_with_errors(self):
        response = self.post(amount="0")
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "amount", "Amount must be greater than zero."
        )
        self.assertFalse(Expense.objects.exists())

    def test_missing_fields_return_200_with_errors(self):
        response = self.client.post(CREATE_URL, {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context["form"].errors), {"amount", "date", "category"})

    def test_unknown_category_returns_200(self):
        response = self.post(category="Travel")
        self.assertEqual(response.status_code, 200)
        self.assertIn("category", response.context["form"].errors)

    def test_warning_message_at_80_percent(self):
        create_budget(self.user, self.food, "100.00", date(2023, 10, 1))
        response = self.post(amount="85.00")
        self.assertIn(
            "Food has used 85.0% of its October 2023 budget. ₹15.00 left.", message_texts(response)
        )

    def test_danger_message_at_100_percent_or_more(self):
        create_budget(self.user, self.food, "50.00", date(2023, 10, 1))
        response = self.post(amount="60.00")
        self.assertIn(
            "Food is at 120.0% of its October 2023 budget (₹60.00 of ₹50.00).",
            message_texts(response),
        )

    def test_no_alert_below_80_percent(self):
        create_budget(self.user, self.food, "100.00", date(2023, 10, 1))
        response = self.post(amount="10.00")
        self.assertEqual(message_texts(response), ["Saved ₹10.00 under Food."])

    def test_category_can_be_preselected(self):
        response = self.client.get(CREATE_URL, {"category": self.food.pk})
        self.assertEqual(response.context["form"].initial["category"], str(self.food.pk))

    def test_user_without_categories_is_told_to_create_one(self):
        self.client.force_login(create_user("newbie"))
        response = self.client.get(CREATE_URL)
        self.assertContains(response, "Create a category")


@override_settings(CURRENCY_SYMBOL="₹")
class ExpenseListViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user("alice")
        cls.food = create_category(cls.user, "Food")
        cls.transport = create_category(cls.user, "Transport")
        cls.groceries = create_expense(cls.user, cls.food, "100.00", date(2026, 10, 5), "Groceries")
        cls.taxi = create_expense(cls.user, cls.transport, "40.00", date(2026, 10, 6), "Taxi home")
        cls.snacks = create_expense(cls.user, cls.food, "15.00", date(2026, 9, 3), "Snacks")

    def setUp(self):
        self.client.force_login(self.user)

    def get(self, **params):
        return self.client.get(reverse("tracker:expense_list"), params)

    def test_lists_expenses_newest_first_with_total(self):
        response = self.get()
        self.assertEqual(
            list(response.context["expenses"]), [self.taxi, self.groceries, self.snacks]
        )
        self.assertEqual(response.context["filtered_total"], Decimal("155.00"))
        self.assertContains(response, "Total: ₹155.00")

    def test_filters_by_month_and_category(self):
        response = self.get(month="2026-10", category=self.food.pk)
        self.assertEqual(list(response.context["expenses"]), [self.groceries])
        self.assertEqual(response.context["filtered_total"], Decimal("100.00"))

    def test_searches_notes(self):
        response = self.get(q="taxi")
        self.assertEqual(list(response.context["expenses"]), [self.taxi])

    def test_invalid_filter_is_reported_and_ignored(self):
        response = self.get(month="garbage")
        self.assertContains(response, "Some filters were invalid")
        self.assertEqual(len(response.context["expenses"]), 3)

    def test_paginates_and_keeps_filters(self):
        for day in range(1, 26):
            create_expense(self.user, self.food, "1.00", date(2026, 8, day))
        response = self.get(month="2026-08")
        self.assertEqual(response.context["paginator"].num_pages, 2)
        self.assertEqual(len(response.context["expenses"]), 20)
        self.assertContains(response, "?month=2026-08&amp;page=2")
        self.assertEqual(len(self.get(month="2026-08", page=2).context["expenses"]), 5)


class ExpenseUpdateDeleteViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user("alice")
        cls.food = create_category(cls.user, "Food")

    def setUp(self):
        self.client.force_login(self.user)
        self.expense = create_expense(self.user, self.food, "20.00", date(2026, 10, 2), "Lunch")
        self.update_url = reverse("tracker:expense_update", args=[self.expense.pk])
        self.delete_url = reverse("tracker:expense_delete", args=[self.expense.pk])

    def test_update_saves_changes_and_returns_to_the_list(self):
        response = self.client.post(
            self.update_url,
            {"amount": "25.00", "date": "2026-10-03", "category": self.food.pk, "notes": "Dinner"},
        )
        self.assertRedirects(response, reverse("tracker:expense_list"))
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.amount, Decimal("25.00"))
        self.assertEqual(self.expense.notes, "Dinner")

    def test_update_rejects_negative_amount(self):
        response = self.client.post(
            self.update_url, {"amount": "-1", "date": "2026-10-03", "category": self.food.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.amount, Decimal("20.00"))

    def test_delete_asks_for_confirmation_first(self):
        response = self.client.get(self.delete_url)
        self.assertContains(response, "Delete this expense?")
        self.assertTrue(Expense.objects.filter(pk=self.expense.pk).exists())

    def test_delete_removes_the_expense(self):
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, reverse("tracker:expense_list"))
        self.assertFalse(Expense.objects.filter(pk=self.expense.pk).exists())
        self.assertIn("Expense deleted.", message_texts(response))
