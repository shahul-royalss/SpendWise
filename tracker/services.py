"""Budget calculations and alert rules.

All arithmetic uses ``Decimal`` so the 80% and 100% thresholds are compared
exactly; there is no float rounding at the boundaries.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_DOWN, Decimal
from enum import Enum

from django.db import transaction
from django.db.models import Q, Sum

from .dates import add_months, first_day_of_month, month_bounds
from .models import Budget, Category, Expense
from .money import ZERO, to_money

WARNING_THRESHOLD = Decimal("80")
DANGER_THRESHOLD = Decimal("100")
ONE_DECIMAL = Decimal("0.1")


class AlertLevel(str, Enum):
    NO_BUDGET = "no_budget"
    NORMAL = "normal"
    WARNING = "warning"
    DANGER = "danger"

    def __str__(self):
        return self.value

    @property
    def label(self) -> str:
        return ALERT_STYLES[self][0]

    @property
    def css_class(self) -> str:
        """Bootstrap contextual colour used for badges, progress bars and alerts."""
        return ALERT_STYLES[self][1]

    @property
    def icon(self) -> str:
        """Bootstrap Icons name."""
        return ALERT_STYLES[self][2]


ALERT_STYLES = {
    AlertLevel.NO_BUDGET: ("No budget", "secondary", "dash-circle"),
    AlertLevel.NORMAL: ("Normal", "success", "check-circle-fill"),
    AlertLevel.WARNING: ("Warning", "warning", "exclamation-triangle-fill"),
    AlertLevel.DANGER: ("Danger", "danger", "x-octagon-fill"),
}


def usage_percentage(spent: Decimal, limit: Decimal) -> Decimal:
    """Return ``spent`` as a percentage of ``limit``, rounded down to one decimal.

    Rounding down keeps the displayed figure honest: 79.99% shows as 79.9%, so
    the number never claims a threshold that has not been reached.
    """
    if limit <= 0:
        raise ValueError("The budget limit must be greater than zero.")
    return (spent * 100 / limit).quantize(ONE_DECIMAL, rounding=ROUND_DOWN)


def get_alert_level(spent: Decimal, limit: Decimal | None) -> AlertLevel:
    """Classify a month's spending against its limit.

    * no limit           -> NO_BUDGET
    * below 80%          -> NORMAL
    * 80% up to < 100%   -> WARNING
    * 100% or more       -> DANGER
    """
    if limit is None or limit <= 0:
        return AlertLevel.NO_BUDGET
    percentage = spent * 100 / limit
    if percentage >= DANGER_THRESHOLD:
        return AlertLevel.DANGER
    if percentage >= WARNING_THRESHOLD:
        return AlertLevel.WARNING
    return AlertLevel.NORMAL


@dataclass(frozen=True)
class CategorySpending:
    """One category's spending for one month, measured against its budget."""

    category: Category
    spent: Decimal
    budget: Budget | None = None
    share: Decimal = ZERO  # percentage of the month's total spending

    @property
    def limit(self) -> Decimal | None:
        return self.budget.monthly_limit if self.budget else None

    @property
    def has_budget(self) -> bool:
        return self.budget is not None

    @property
    def remaining(self) -> Decimal | None:
        """Limit minus spent; negative when the category is over budget."""
        if self.limit is None:
            return None
        return self.limit - self.spent

    @property
    def overspent(self) -> Decimal:
        if self.remaining is None or self.remaining >= 0:
            return ZERO
        return -self.remaining

    @property
    def percentage(self) -> Decimal | None:
        if self.limit is None:
            return None
        return usage_percentage(self.spent, self.limit)

    @property
    def progress(self) -> int:
        """Progress bar width, capped at 100."""
        if self.percentage is None:
            return 0
        return int(min(self.percentage, DANGER_THRESHOLD))

    @property
    def alert_level(self) -> AlertLevel:
        return get_alert_level(self.spent, self.limit)


@dataclass(frozen=True)
class MonthlySummary:
    """Everything the dashboard needs for one user and one month."""

    month: date
    rows: tuple[CategorySpending, ...]

    @property
    def total_spent(self) -> Decimal:
        return sum((row.spent for row in self.rows), ZERO)

    @property
    def budgeted_rows(self) -> list[CategorySpending]:
        return [row for row in self.rows if row.has_budget]

    @property
    def unbudgeted_rows(self) -> list[CategorySpending]:
        return [row for row in self.rows if not row.has_budget]

    @property
    def total_budget(self) -> Decimal:
        return sum((row.limit for row in self.budgeted_rows), ZERO)

    @property
    def budgeted_spent(self) -> Decimal:
        return sum((row.spent for row in self.budgeted_rows), ZERO)

    @property
    def unbudgeted_spent(self) -> Decimal:
        return self.total_spent - self.budgeted_spent

    @property
    def remaining_budget(self) -> Decimal:
        """Total of all limits minus what was spent in budgeted categories."""
        return self.total_budget - self.budgeted_spent

    @property
    def overall_percentage(self) -> Decimal | None:
        if not self.total_budget:
            return None
        return usage_percentage(self.budgeted_spent, self.total_budget)

    @property
    def overall_alert_level(self) -> AlertLevel:
        return get_alert_level(self.budgeted_spent, self.total_budget or None)

    @property
    def alerts(self) -> list[CategorySpending]:
        """Categories at Warning or Danger, highest usage first."""
        flagged = [
            row for row in self.rows if row.alert_level in (AlertLevel.WARNING, AlertLevel.DANGER)
        ]
        return sorted(flagged, key=lambda row: row.percentage, reverse=True)

    @property
    def danger_count(self) -> int:
        return sum(1 for row in self.rows if row.alert_level is AlertLevel.DANGER)

    @property
    def warning_count(self) -> int:
        return sum(1 for row in self.rows if row.alert_level is AlertLevel.WARNING)


def _share(spent: Decimal, total: Decimal) -> Decimal:
    if not total:
        return ZERO
    return (spent * 100 / total).quantize(ONE_DECIMAL, rounding=ROUND_DOWN)


def get_monthly_summary(user, month: date) -> MonthlySummary:
    """Build the monthly summary for ``user`` with two queries in total."""
    start, end = month_bounds(month)
    in_month = Q(expenses__user=user, expenses__date__gte=start, expenses__date__lt=end)
    # Meta.ordering is not applied to aggregate queries, so order explicitly.
    categories = (
        Category.objects.for_user(user)
        .annotate(spent=Sum("expenses__amount", filter=in_month))
        .order_by("name")
    )
    budgets = {
        budget.category_id: budget for budget in Budget.objects.for_user(user).for_month(start)
    }

    spending = [(category, to_money(category.spent)) for category in categories]
    total = sum((spent for _, spent in spending), ZERO)
    rows = tuple(
        CategorySpending(
            category=category,
            spent=spent,
            budget=budgets.get(category.pk),
            share=_share(spent, total),
        )
        for category, spent in spending
    )
    return MonthlySummary(month=start, rows=rows)


def get_category_spending(category: Category, month: date) -> CategorySpending:
    """Spending and budget status of a single category for ``month``."""
    expenses = Expense.objects.filter(user_id=category.user_id, category=category)
    budget = Budget.objects.filter(user_id=category.user_id, category=category).for_month(month)
    return CategorySpending(
        category=category,
        spent=expenses.in_month(month).total(),
        budget=budget.first(),
    )


def copy_previous_month_budgets(user, month: date) -> int:
    """Copy last month's limits into ``month`` for categories without a budget yet.

    Returns the number of budgets created.
    """
    target = first_day_of_month(month)
    source = add_months(target, -1)
    budgets = Budget.objects.for_user(user)
    already_set = set(budgets.for_month(target).values_list("category_id", flat=True))
    new_budgets = [
        Budget(
            user=user,
            category_id=budget.category_id,
            monthly_limit=budget.monthly_limit,
            month_year=target,
        )
        for budget in budgets.for_month(source)
        if budget.category_id not in already_set
    ]
    with transaction.atomic():
        Budget.objects.bulk_create(new_budgets, ignore_conflicts=True)
    return len(new_budgets)
