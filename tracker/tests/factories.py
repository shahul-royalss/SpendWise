"""Small helpers for building test data."""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model

from tracker.models import Budget, Category, Expense

MONTH = date(2026, 10, 1)


def create_user(username="alice", **extra):
    # No password means an unusable one, which skips the slow hashing step.
    return get_user_model().objects.create_user(username=username, **extra)


def create_category(user, name="Food", description=""):
    return Category.objects.create(user=user, name=name, description=description)


def create_budget(user, category, monthly_limit="100.00", month=MONTH):
    return Budget.objects.create(
        user=user, category=category, monthly_limit=Decimal(monthly_limit), month_year=month
    )


def create_expense(user, category, amount="10.00", on=None, notes=""):
    return Expense.objects.create(
        user=user,
        category=category,
        amount=Decimal(amount),
        date=on or date(2026, 10, 15),
        notes=notes,
    )
