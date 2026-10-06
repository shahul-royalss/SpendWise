from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView

from tracker.mixins import MonthNavigationMixin
from tracker.models import Expense
from tracker.services import get_monthly_summary, get_spending_trend


def greeting_for(hour):
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


class DashboardView(LoginRequiredMixin, MonthNavigationMixin, TemplateView):
    template_name = "tracker/dashboard.html"
    recent_expense_count = 5
    trend_months = 6

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        month_expenses = Expense.objects.for_user(user).in_month(self.month)
        context["greeting"] = greeting_for(timezone.localtime().hour)
        context["summary"] = get_monthly_summary(user, self.month)
        context["trend"] = get_spending_trend(user, self.month, self.trend_months)
        context["expense_count"] = month_expenses.count()
        context["recent_expenses"] = month_expenses.select_related("category")[
            : self.recent_expense_count
        ]
        return context
