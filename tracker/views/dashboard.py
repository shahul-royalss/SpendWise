from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from tracker.mixins import MonthNavigationMixin
from tracker.models import Expense
from tracker.services import get_monthly_summary


class DashboardView(LoginRequiredMixin, MonthNavigationMixin, TemplateView):
    template_name = "tracker/dashboard.html"
    recent_expense_count = 5

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        month_expenses = Expense.objects.for_user(user).in_month(self.month)
        context["summary"] = get_monthly_summary(user, self.month)
        context["expense_count"] = month_expenses.count()
        context["recent_expenses"] = month_expenses.select_related("category")[
            : self.recent_expense_count
        ]
        return context
