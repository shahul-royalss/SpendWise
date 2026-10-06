from unittest import mock

from django.contrib.messages import get_messages
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from tracker.dates import current_month
from tracker.models import Budget, Category, Expense

from .factories import create_budget, create_category, create_expense, create_user


class CategoryViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user("alice")
        cls.food = create_category(cls.user, "Food", "Meals and groceries")

    def setUp(self):
        self.client.force_login(self.user)

    def test_list_shows_categories_with_counts(self):
        create_expense(self.user, self.food)
        create_budget(self.user, self.food)
        response = self.client.get(reverse("tracker:category_list"))
        self.assertContains(response, "Food")
        self.assertContains(response, "Meals and groceries")
        category = response.context["categories"][0]
        self.assertEqual((category.expense_count, category.budget_count), (1, 1))

    def test_create_category(self):
        response = self.client.post(
            reverse("tracker:category_create"), {"name": "Transport", "description": "Bus and fuel"}
        )
        self.assertRedirects(response, reverse("tracker:category_list"))
        category = Category.objects.get(name="Transport")
        self.assertEqual(category.user, self.user)

    def test_duplicate_category_returns_200(self):
        response = self.client.post(reverse("tracker:category_create"), {"name": "food"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You already have a category with this name.")
        self.assertEqual(Category.objects.count(), 1)

    def test_detail_shows_this_months_status(self):
        create_budget(self.user, self.food, "100.00", current_month())
        create_expense(self.user, self.food, "90.00", current_month(), "Weekly shop")
        response = self.client.get(self.food.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Weekly shop")
        self.assertContains(response, "bg-warning-subtle")
        self.assertEqual(response.context["status"].percentage, 90)

    def test_update_category(self):
        response = self.client.post(
            reverse("tracker:category_update", args=[self.food.pk]),
            {"name": "Food & drinks", "description": ""},
        )
        self.assertRedirects(response, self.food.get_absolute_url())
        self.food.refresh_from_db()
        self.assertEqual(self.food.name, "Food & drinks")


class CategoryDeleteViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user("alice")

    def setUp(self):
        self.client.force_login(self.user)
        self.food = create_category(self.user, "Food")
        self.groceries = create_category(self.user, "Groceries")
        self.url = reverse("tracker:category_delete", args=[self.food.pk])

    def test_category_without_expenses_is_deleted_with_its_budgets(self):
        create_budget(self.user, self.food)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("tracker:category_list"))
        self.assertFalse(Category.objects.filter(pk=self.food.pk).exists())
        self.assertFalse(Budget.objects.exists())

    def test_confirmation_page_explains_what_happens(self):
        create_expense(self.user, self.food)
        create_expense(self.user, self.food)
        create_budget(self.user, self.food)
        response = self.client.get(self.url)
        self.assertContains(response, "This category has 2 expenses.")
        self.assertContains(response, "Its 1 budget will be deleted as well.")

    def test_category_with_expenses_is_not_deleted_without_a_target(self):
        create_expense(self.user, self.food)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This category still has expenses.")
        self.assertTrue(Category.objects.filter(pk=self.food.pk).exists())

    def test_expenses_are_moved_before_the_category_is_deleted(self):
        first = create_expense(self.user, self.food)
        second = create_expense(self.user, self.food)
        response = self.client.post(self.url, {"move_expenses_to": self.groceries.pk})
        self.assertRedirects(response, reverse("tracker:category_list"))
        self.assertFalse(Category.objects.filter(pk=self.food.pk).exists())
        self.assertEqual(set(Expense.objects.filter(category=self.groceries)), {first, second})
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn('Moved 2 expense(s) to "Groceries" and deleted "Food".', messages)

    def test_get_does_not_delete(self):
        self.client.get(self.url)
        self.assertTrue(Category.objects.filter(pk=self.food.pk).exists())

    def test_expense_added_during_deletion_blocks_it_safely(self):
        # Simulates another request adding an expense between validation and delete.
        with mock.patch.object(Category, "delete", side_effect=ProtectedError("in use", set())):
            response = self.client.post(self.url)
        self.assertRedirects(response, self.food.get_absolute_url())
        self.assertTrue(Category.objects.filter(pk=self.food.pk).exists())
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn('"Food" still has expenses, so it was not deleted.', messages)
