from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, Sum
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils import timezone

from .dates import first_day_of_month, month_bounds
from .money import to_money

MIN_AMOUNT = Decimal("0.01")


class OwnedQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(user=user)


class BudgetQuerySet(OwnedQuerySet):
    def for_month(self, month):
        return self.filter(month_year=first_day_of_month(month))


class ExpenseQuerySet(OwnedQuerySet):
    def in_month(self, month):
        start, end = month_bounds(month)
        return self.filter(date__gte=start, date__lt=end)

    def total(self):
        return to_money(self.aggregate(total=Sum("amount"))["total"])


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


def validate_same_owner(instance):
    """Reject a category that belongs to someone other than the record's owner."""
    if instance.user_id and instance.category_id and instance.category.user_id != instance.user_id:
        raise ValidationError({"category": "Select one of your own categories."})


class Category(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="categories"
    )
    name = models.CharField(max_length=50)
    description = models.TextField(max_length=255, blank=True)

    objects = OwnedQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"
        constraints = [
            models.UniqueConstraint(
                "user",
                Lower("name"),
                name="unique_category_name_per_user",
                violation_error_message="You already have a category with this name.",
            ),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("tracker:category_detail", args=[self.pk])


class Budget(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="budgets"
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="budgets")
    monthly_limit = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(MIN_AMOUNT)]
    )
    month_year = models.DateField(help_text="Stored as the first day of the budget month.")

    objects = BudgetQuerySet.as_manager()

    class Meta:
        ordering = ["-month_year", "category__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "category", "month_year"],
                name="unique_budget_per_category_month",
                violation_error_message="This category already has a budget for that month.",
            ),
            models.CheckConstraint(
                condition=Q(monthly_limit__gt=0), name="budget_monthly_limit_positive"
            ),
        ]

    def __str__(self):
        return f"{self.category} - {self.month_year:%B %Y}"

    def save(self, *args, **kwargs):
        if self.month_year:
            self.month_year = first_day_of_month(self.month_year)
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.month_year:
            self.month_year = first_day_of_month(self.month_year)
        validate_same_owner(self)


class Expense(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="expenses"
    )
    # PROTECT: a category that still has expenses can't be deleted by accident.
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="expenses")
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(MIN_AMOUNT)]
    )
    date = models.DateField(default=timezone.localdate)
    notes = models.TextField(max_length=500, blank=True)

    objects = ExpenseQuerySet.as_manager()

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["user", "date"], name="expense_user_date_idx")]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="expense_amount_positive"),
        ]

    def __str__(self):
        return f"{self.amount} on {self.date:%Y-%m-%d} ({self.category})"

    def clean(self):
        super().clean()
        validate_same_owner(self)
