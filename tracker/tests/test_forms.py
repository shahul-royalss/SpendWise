from datetime import date
from decimal import Decimal

from django.test import TestCase

from tracker.forms import (
    BudgetForm,
    CategoryDeleteForm,
    CategoryForm,
    ExpenseFilterForm,
    ExpenseForm,
)
from tracker.models import Expense

from .factories import MONTH, create_budget, create_category, create_expense, create_user


class ExpenseFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user("alice")
        cls.other = create_user("bob")
        cls.food = create_category(cls.user, "Food")
        cls.others_food = create_category(cls.other, "Food")
        cls.others_travel = create_category(cls.other, "Travel")

    def form(self, **overrides):
        data = {
            "amount": "45.50",
            "date": "2023-10-15",
            "category": str(self.food.pk),
            "notes": "Lunch with client",
        }
        data.update(overrides)
        return ExpenseForm(data=data, user=self.user)

    def test_valid_data_saves_an_expense_for_the_user(self):
        form = self.form()
        self.assertTrue(form.is_valid(), form.errors)
        expense = form.save()
        self.assertEqual(expense.user, self.user)
        self.assertEqual(expense.amount, Decimal("45.50"))
        self.assertEqual(expense.date, date(2023, 10, 15))
        self.assertEqual(expense.category, self.food)
        self.assertEqual(expense.notes, "Lunch with client")

    def test_negative_amount_is_rejected(self):
        form = self.form(amount="-10")
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["amount"], ["Amount must be greater than zero."])

    def test_zero_amount_is_rejected(self):
        for amount in ("0", "0.00"):
            with self.subTest(amount=amount):
                form = self.form(amount=amount)
                self.assertFalse(form.is_valid())
                self.assertIn("amount", form.errors)

    def test_malformed_amounts_are_rejected(self):
        for amount in ("abc", "1.234", "NaN", "Infinity", "", "1234567890123"):
            with self.subTest(amount=amount):
                self.assertIn("amount", self.form(amount=amount).errors)

    def test_category_can_be_given_by_name(self):
        form = self.form(category="food")
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["category"], self.food)

    def test_another_users_category_id_is_rejected(self):
        self.assertIn("category", self.form(category=str(self.others_food.pk)).errors)

    def test_name_lookup_never_finds_another_users_category(self):
        self.assertIn("category", self.form(category="Travel").errors)

    def test_category_choices_are_limited_to_the_user(self):
        self.assertEqual(list(self.form().fields["category"].queryset), [self.food])

    def test_notes_are_optional(self):
        self.assertTrue(self.form(notes="").is_valid())

    def test_date_is_required(self):
        self.assertIn("date", self.form(date="").errors)

    def test_invalid_fields_get_bootstrap_error_class(self):
        form = self.form(amount="-1")
        form.is_valid()
        self.assertIn("is-invalid", form.fields["amount"].widget.attrs["class"])
        self.assertEqual(form.fields["amount"].widget.attrs["aria-invalid"], "true")

    def test_submitted_user_field_is_ignored(self):
        form = self.form(user=str(self.other.pk))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().user, self.user)
        self.assertFalse(Expense.objects.filter(user=self.other).exists())


class CategoryFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user("alice")
        cls.food = create_category(cls.user, "Food")

    def test_duplicate_name_is_rejected_ignoring_case_and_spaces(self):
        form = CategoryForm(data={"name": "  food "}, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["name"], ["You already have a category with this name."])

    def test_same_name_is_fine_for_another_user(self):
        form = CategoryForm(data={"name": "Food"}, user=create_user("bob"))
        self.assertTrue(form.is_valid(), form.errors)

    def test_editing_a_category_keeps_its_own_name(self):
        form = CategoryForm(
            data={"name": "Food", "description": "Meals"}, instance=self.food, user=self.user
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_inner_whitespace_is_collapsed_and_owner_is_set(self):
        form = CategoryForm(data={"name": "Eating   out"}, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        category = form.save()
        self.assertEqual(category.name, "Eating out")
        self.assertEqual(category.user, self.user)


class BudgetFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user("alice")
        cls.food = create_category(cls.user, "Food")

    def form(self, instance=None, **overrides):
        data = {"category": str(self.food.pk), "month_year": "2026-10", "monthly_limit": "500.00"}
        data.update(overrides)
        return BudgetForm(data=data, instance=instance, user=self.user)

    def test_month_is_stored_as_the_first_day(self):
        form = self.form()
        self.assertTrue(form.is_valid(), form.errors)
        budget = form.save()
        self.assertEqual(budget.month_year, MONTH)
        self.assertEqual(budget.user, self.user)

    def test_a_full_date_is_accepted_as_its_month(self):
        form = self.form(month_year="2026-10-17")
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["month_year"], MONTH)

    def test_invalid_months_are_rejected(self):
        for value in ("October", "2026-13", "", "1800-01"):
            with self.subTest(value=value):
                self.assertIn("month_year", self.form(month_year=value).errors)

    def test_limit_must_be_positive(self):
        for limit in ("0", "-5"):
            with self.subTest(limit=limit):
                form = self.form(monthly_limit=limit)
                self.assertEqual(
                    form.errors["monthly_limit"], ["The monthly limit must be greater than zero."]
                )

    def test_second_budget_for_the_same_month_is_rejected(self):
        create_budget(self.user, self.food, "300.00")
        form = self.form()
        self.assertFalse(form.is_valid())
        self.assertIn("already has a budget for October 2026", form.non_field_errors()[0])

    def test_updating_a_budget_is_not_a_duplicate(self):
        budget = create_budget(self.user, self.food, "300.00")
        form = self.form(instance=budget, monthly_limit="600.00")
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().monthly_limit, Decimal("600.00"))

    def test_category_by_name_and_other_users_category(self):
        self.assertTrue(self.form(category="FOOD").is_valid())
        other_category = create_category(create_user("bob"), "Rent")
        self.assertIn("category", self.form(category=str(other_category.pk)).errors)


class ExpenseFilterFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user("alice")
        cls.food = create_category(cls.user, "Food")
        cls.transport = create_category(cls.user, "Transport")
        cls.groceries = create_expense(cls.user, cls.food, on=date(2026, 10, 5), notes="Groceries")
        cls.taxi = create_expense(cls.user, cls.transport, on=date(2026, 10, 6), notes="Taxi")
        cls.snacks = create_expense(cls.user, cls.food, on=date(2026, 9, 3), notes="Snacks")

    def filtered(self, data):
        form = ExpenseFilterForm(data, user=self.user)
        return set(form.filter(Expense.objects.for_user(self.user))), form

    def test_no_filters_returns_everything(self):
        expenses, form = self.filtered(None)
        self.assertEqual(expenses, {self.groceries, self.taxi, self.snacks})
        self.assertFalse(form.is_active)

    def test_filter_by_month_category_and_notes(self):
        self.assertEqual(self.filtered({"month": "2026-10"})[0], {self.groceries, self.taxi})
        self.assertEqual(
            self.filtered({"category": str(self.food.pk)})[0], {self.groceries, self.snacks}
        )
        expenses, form = self.filtered({"q": "TAXI"})
        self.assertEqual(expenses, {self.taxi})
        self.assertTrue(form.is_active)

    def test_invalid_filters_are_ignored(self):
        expenses, form = self.filtered({"month": "not-a-month"})
        self.assertEqual(len(expenses), 3)
        self.assertFalse(form.is_active)


class CategoryDeleteFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user("alice")
        cls.food = create_category(cls.user, "Food")
        cls.groceries = create_category(cls.user, "Groceries")
        cls.others = create_category(create_user("bob"), "Elsewhere")

    def test_target_is_required_when_the_category_has_expenses(self):
        create_expense(self.user, self.food)
        form = CategoryDeleteForm(data={}, category=self.food)
        self.assertFalse(form.is_valid())
        self.assertIn("still has expenses", form.non_field_errors()[0])

    def test_no_target_needed_without_expenses(self):
        self.assertTrue(CategoryDeleteForm(data={}, category=self.food).is_valid())

    def test_targets_exclude_the_category_itself_and_other_users(self):
        form = CategoryDeleteForm(data={}, category=self.food)
        self.assertEqual(list(form.fields["move_expenses_to"].queryset), [self.groceries])
