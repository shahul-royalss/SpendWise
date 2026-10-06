from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone

from tracker.models import Budget, Category, Expense

from .factories import MONTH, create_budget, create_category, create_expense, create_user


class CategoryModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user("alice")
        cls.food = create_category(cls.user, "Food")

    def test_str_and_url(self):
        self.assertEqual(str(self.food), "Food")
        self.assertEqual(self.food.get_absolute_url(), f"/categories/{self.food.pk}/")

    def test_name_is_unique_per_user_ignoring_case(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            create_category(self.user, "food")

    def test_two_users_can_use_the_same_name(self):
        other = create_user("bob")
        self.assertEqual(create_category(other, "Food").name, "Food")

    def test_category_with_expenses_cannot_be_deleted(self):
        create_expense(self.user, self.food)
        with self.assertRaises(ProtectedError):
            self.food.delete()

    def test_deleting_a_category_removes_its_budgets(self):
        create_budget(self.user, self.food)
        self.food.delete()
        self.assertFalse(Budget.objects.exists())


class BudgetModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user("alice")
        cls.food = create_category(cls.user, "Food")

    def test_month_is_stored_as_the_first_day(self):
        budget = create_budget(self.user, self.food, month=date(2026, 10, 17))
        budget.refresh_from_db()
        self.assertEqual(budget.month_year, MONTH)

    def test_clean_also_normalises_the_month(self):
        budget = Budget(
            user=self.user,
            category=self.food,
            monthly_limit=Decimal("10"),
            month_year=date(2026, 10, 9),
        )
        budget.full_clean()
        self.assertEqual(budget.month_year, MONTH)

    def test_one_budget_per_category_per_month(self):
        create_budget(self.user, self.food)
        with self.assertRaises(IntegrityError), transaction.atomic():
            create_budget(self.user, self.food, month=date(2026, 10, 20))

    def test_limit_must_be_positive_in_the_database(self):
        for limit in ("0", "-5"):
            with self.subTest(limit=limit), self.assertRaises(IntegrityError), transaction.atomic():
                create_budget(self.user, self.food, monthly_limit=limit)

    def test_validation_rejects_another_users_category(self):
        other_category = create_category(create_user("bob"), "Rent")
        budget = Budget(
            user=self.user, category=other_category, monthly_limit=Decimal("10"), month_year=MONTH
        )
        with self.assertRaises(ValidationError) as caught:
            budget.full_clean()
        self.assertIn("category", caught.exception.message_dict)

    def test_str(self):
        self.assertEqual(str(create_budget(self.user, self.food)), "Food - October 2026")


class ExpenseModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user("alice")
        cls.food = create_category(cls.user, "Food")

    def test_amount_must_be_positive_in_the_database(self):
        for amount in ("0", "-5"):
            with (
                self.subTest(amount=amount),
                self.assertRaises(IntegrityError),
                transaction.atomic(),
            ):
                create_expense(self.user, self.food, amount)

    def test_validation_rejects_zero_amount(self):
        expense = Expense(user=self.user, category=self.food, amount=Decimal("0"), date=MONTH)
        with self.assertRaises(ValidationError) as caught:
            expense.full_clean()
        self.assertIn("amount", caught.exception.message_dict)

    def test_validation_rejects_another_users_category(self):
        other_category = create_category(create_user("bob"), "Rent")
        expense = Expense(user=self.user, category=other_category, amount=Decimal("5"), date=MONTH)
        with self.assertRaises(ValidationError) as caught:
            expense.full_clean()
        self.assertIn("category", caught.exception.message_dict)

    def test_date_defaults_to_today(self):
        expense = Expense.objects.create(user=self.user, category=self.food, amount=Decimal("5"))
        self.assertEqual(expense.date, timezone.localdate())

    def test_newest_expenses_come_first(self):
        older = create_expense(self.user, self.food, on=date(2026, 10, 1))
        newer = create_expense(self.user, self.food, on=date(2026, 10, 2))
        self.assertEqual(list(Expense.objects.all()), [newer, older])

    def test_queryset_helpers(self):
        create_expense(self.user, self.food, "10.50", date(2026, 10, 1))
        create_expense(self.user, self.food, "4.25", date(2026, 10, 31))
        create_expense(self.user, self.food, "99.00", date(2026, 11, 1))
        october = Expense.objects.for_user(self.user).in_month(MONTH)
        self.assertEqual(october.count(), 2)
        self.assertEqual(october.total(), Decimal("14.75"))
        self.assertEqual(Expense.objects.none().total(), Decimal("0.00"))

    def test_str(self):
        expense = create_expense(self.user, self.food, "45.50", date(2023, 10, 15))
        self.assertEqual(str(expense), "45.50 on 2023-10-15 (Food)")

    def test_category_list_is_ordered_by_name(self):
        create_category(self.user, "Bills")
        self.assertEqual(
            list(Category.objects.for_user(self.user).values_list("name", flat=True)),
            ["Bills", "Food"],
        )
