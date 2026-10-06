"""Authentication is required everywhere, and users only ever see their own data."""

from django.test import TestCase
from django.urls import reverse

from tracker.models import Budget, Category, Expense

from .factories import create_budget, create_category, create_expense, create_user


class LoginRequiredTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        owner = create_user("alice")
        cls.category = create_category(owner, "Food")
        cls.budget = create_budget(owner, cls.category)
        cls.expense = create_expense(owner, cls.category)

    def assert_redirects_to_login(self, response, url):
        self.assertRedirects(
            response, f"{reverse('accounts:login')}?next={url}", fetch_redirect_response=False
        )

    def test_list_and_create_pages_redirect_anonymous_users_to_login(self):
        names = [
            "tracker:dashboard",
            "tracker:expense_list",
            "tracker:expense_create",
            "tracker:category_list",
            "tracker:category_create",
            "tracker:budget_list",
            "tracker:budget_create",
        ]
        for name in names:
            url = reverse(name)
            with self.subTest(url=url):
                self.assert_redirects_to_login(self.client.get(url), url)

    def test_object_pages_redirect_anonymous_users_to_login(self):
        urls = [
            reverse("tracker:expense_update", args=[self.expense.pk]),
            reverse("tracker:expense_delete", args=[self.expense.pk]),
            reverse("tracker:category_detail", args=[self.category.pk]),
            reverse("tracker:category_update", args=[self.category.pk]),
            reverse("tracker:category_delete", args=[self.category.pk]),
            reverse("tracker:budget_update", args=[self.budget.pk]),
            reverse("tracker:budget_delete", args=[self.budget.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assert_redirects_to_login(self.client.get(url), url)

    def test_anonymous_post_to_expense_create_saves_nothing(self):
        response = self.client.post(
            "/expenses/create/", {"amount": "45.50", "date": "2023-10-15", "category": "Food"}
        )
        self.assert_redirects_to_login(response, "/expenses/create/")
        self.assertEqual(Expense.objects.count(), 1)

    def test_root_redirects_to_the_dashboard(self):
        self.assertRedirects(
            self.client.get("/"), reverse("tracker:dashboard"), fetch_redirect_response=False
        )


class OwnershipIsolationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = create_user("alice")
        cls.category = create_category(cls.owner, "Secret savings")
        cls.budget = create_budget(cls.owner, cls.category, "777.00")
        cls.expense = create_expense(cls.owner, cls.category, "123.45", notes="Private note")
        cls.intruder = create_user("mallory")
        create_category(cls.intruder, "Mine")

    def setUp(self):
        self.client.force_login(self.intruder)

    def test_other_users_objects_return_404(self):
        detail_url = reverse("tracker:category_detail", args=[self.category.pk])
        self.assertEqual(self.client.get(detail_url).status_code, 404)

        writable_urls = [
            reverse("tracker:category_update", args=[self.category.pk]),
            reverse("tracker:category_delete", args=[self.category.pk]),
            reverse("tracker:budget_update", args=[self.budget.pk]),
            reverse("tracker:budget_delete", args=[self.budget.pk]),
            reverse("tracker:expense_update", args=[self.expense.pk]),
            reverse("tracker:expense_delete", args=[self.expense.pk]),
        ]
        for url in writable_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(
                    self.client.post(url, {"name": "Hacked", "amount": "1"}).status_code, 404
                )

        self.assertTrue(
            Category.objects.filter(pk=self.category.pk, name="Secret savings").exists()
        )
        self.assertTrue(Budget.objects.filter(pk=self.budget.pk).exists())
        self.assertTrue(Expense.objects.filter(pk=self.expense.pk, amount="123.45").exists())

    def test_list_pages_only_show_own_data(self):
        pages = [
            reverse("tracker:dashboard"),
            reverse("tracker:category_list"),
            reverse("tracker:expense_list"),
            reverse("tracker:budget_list"),
        ]
        for url in pages:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "Secret savings")
                self.assertNotContains(response, "Private note")

        self.assertContains(self.client.get(reverse("tracker:category_list")), "Mine")

    def test_cannot_log_an_expense_into_another_users_category(self):
        response = self.client.post(
            "/expenses/create/",
            {"amount": "10.00", "date": "2026-10-01", "category": str(self.category.pk)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("category", response.context["form"].errors)
        self.assertFalse(Expense.objects.filter(user=self.intruder).exists())

    def test_cannot_budget_another_users_category(self):
        response = self.client.post(
            reverse("tracker:budget_create"),
            {"category": str(self.category.pk), "month_year": "2026-10", "monthly_limit": "5"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Budget.objects.filter(user=self.intruder).exists())

    def test_cannot_move_expenses_into_another_users_category(self):
        own = Category.objects.get(user=self.intruder, name="Mine")
        create_expense(self.intruder, own)
        response = self.client.post(
            reverse("tracker:category_delete", args=[own.pk]),
            {"move_expenses_to": str(self.category.pk)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Category.objects.filter(pk=own.pk).exists())
        self.assertEqual(self.category.expenses.count(), 1)
