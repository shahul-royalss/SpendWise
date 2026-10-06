"""Create a demo account filled with sample categories, budgets and expenses.

The data is chosen so the dashboard shows every alert state for the current
month: Normal, Warning (Food, 86%), Danger at exactly 100% (Entertainment),
Danger over the limit (Transport, 115%) and a category without a budget.

    python manage.py seed_demo
    python manage.py seed_demo --username alice --password "a-strong-password"
"""

import secrets
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from tracker.dates import add_months, current_month
from tracker.models import Budget, Category, Expense

# name: (description, monthly limit or None, this month's expenses, last month's expenses)
DEMO_DATA = {
    "Food": (
        "Groceries, eating out and snacks",
        "8000",
        [
            ("2450", "Monthly groceries"),
            ("1850", "Vegetables and fruits"),
            ("1200", "Dinner with friends"),
            ("1400", "Office lunches"),
        ],
        [
            ("2600", "Monthly groceries"),
            ("1900", "Vegetables and fruits"),
            ("700", "Lunch with client"),
        ],
    ),
    "Transport": (
        "Fuel, cabs and public transport",
        "3000",
        [("1500", "Fuel"), ("1200", "Cab rides"), ("750", "Metro card recharge")],
        [("1400", "Fuel"), ("700", "Metro card recharge")],
    ),
    "Utilities": (
        "Electricity, water, phone and internet",
        "4000",
        [("1400", "Electricity bill"), ("700", "Mobile and internet")],
        [("2900", "Electricity bill"), ("700", "Mobile and internet")],
    ),
    "Entertainment": (
        "Movies, events and subscriptions",
        "2000",
        [("1200", "Concert tickets"), ("800", "Streaming subscriptions")],
        [("900", "Movie night")],
    ),
    "Shopping": (
        "Clothes and household items",
        "5000",
        [("1250", "Running shoes")],
        [("2000", "Kitchen supplies")],
    ),
    "Health": (
        "Medicines and doctor visits",
        None,
        [("800", "Pharmacy")],
        [("500", "Pharmacy")],
    ),
}

# Older history for the six-month trend chart: each month's spending as a share
# of last month's, oldest first (five, four, three and two months ago).
HISTORY_FACTORS = (Decimal("0.70"), Decimal("0.92"), Decimal("0.64"), Decimal("1.08"))


class Command(BaseCommand):
    help = "Create a demo user with sample categories, budgets and expenses."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo", help='Defaults to "demo".')
        parser.add_argument(
            "--password",
            help="Password for the new user. A random one is generated and printed if omitted.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        username = options["username"]
        user_model = get_user_model()
        if user_model.objects.filter(username__iexact=username).exists():
            raise CommandError(f'User "{username}" already exists. Choose another --username.')

        password = options["password"] or secrets.token_urlsafe(12)
        user = user_model.objects.create_user(username=username, password=password)

        this_month = current_month()
        last_month = add_months(this_month, -1)
        today = timezone.localdate()

        history = [
            (add_months(this_month, -(len(HISTORY_FACTORS) + 1 - index)), factor)
            for index, factor in enumerate(HISTORY_FACTORS)
        ]

        for name, (description, limit, current, previous) in DEMO_DATA.items():
            category = Category.objects.create(user=user, name=name, description=description)
            if limit:
                for month in [month for month, _ in history] + [last_month, this_month]:
                    Budget.objects.create(
                        user=user, category=category, monthly_limit=Decimal(limit), month_year=month
                    )
            self._add_expenses(user, category, this_month, current, last_day=today.day)
            self._add_expenses(user, category, last_month, previous, last_day=28)
            previous_total = sum(Decimal(amount) for amount, _ in previous)
            for month, factor in history:
                amount = (previous_total * factor).quantize(Decimal("1"))
                self._add_expenses(user, category, month, [(amount, "Monthly spending")], 28)

        self.stdout.write(self.style.SUCCESS(f'Created demo user "{username}" with sample data.'))
        self.stdout.write(f"Password: {password}")

    @staticmethod
    def _add_expenses(user, category, month, items, last_day):
        """Spread the expenses over the month without going past ``last_day``."""
        for index, (amount, notes) in enumerate(items):
            Expense.objects.create(
                user=user,
                category=category,
                amount=Decimal(amount),
                date=month.replace(day=min(1 + index * 7, last_day)),
                notes=notes,
            )
