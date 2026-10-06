from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DeleteView, TemplateView, UpdateView

from tracker.dates import add_months, current_month, parse_month
from tracker.forms import BudgetForm
from tracker.mixins import MonthNavigationMixin, OwnedObjectMixin, UserFormMixin
from tracker.models import Budget
from tracker.services import copy_previous_month_budgets, get_monthly_summary


def budget_list_url(month):
    query = urlencode({"month": month.strftime("%Y-%m")})
    return f"{reverse('tracker:budget_list')}?{query}"


class BudgetListView(LoginRequiredMixin, MonthNavigationMixin, TemplateView):
    template_name = "tracker/budget_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        summary = get_monthly_summary(user, self.month)
        previous_budgets = Budget.objects.for_user(user).for_month(add_months(self.month, -1))
        context["summary"] = summary
        context["can_copy"] = bool(summary.unbudgeted_rows) and previous_budgets.exists()
        return context


class BudgetCreateView(LoginRequiredMixin, UserFormMixin, SuccessMessageMixin, CreateView):
    model = Budget
    form_class = BudgetForm
    success_message = "Budget saved."

    def get_initial(self):
        initial = super().get_initial()
        initial["month_year"] = parse_month(self.request.GET.get("month")) or current_month()
        if category := self.request.GET.get("category"):
            initial["category"] = category
        return initial

    def get_success_url(self):
        return budget_list_url(self.object.month_year)


class BudgetUpdateView(OwnedObjectMixin, UserFormMixin, SuccessMessageMixin, UpdateView):
    queryset = Budget.objects.select_related("category")
    form_class = BudgetForm
    success_message = "Budget updated."

    def get_success_url(self):
        return budget_list_url(self.object.month_year)


class BudgetDeleteView(OwnedObjectMixin, SuccessMessageMixin, DeleteView):
    queryset = Budget.objects.select_related("category")
    success_message = "Budget deleted."

    def get_success_url(self):
        return budget_list_url(self.object.month_year)


class BudgetCopyView(LoginRequiredMixin, View):
    """POST only: copy last month's budgets into the selected month."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        month = parse_month(request.POST.get("month")) or current_month()
        created = copy_previous_month_budgets(request.user, month)
        if created:
            source = add_months(month, -1)
            messages.success(request, f"Copied {created} budget(s) from {source:%B %Y}.")
        else:
            messages.info(request, "Every category already has a budget, so nothing was copied.")
        return redirect(budget_list_url(month))
