from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from tracker.forms import ExpenseFilterForm, ExpenseForm
from tracker.mixins import OwnedObjectMixin, UserFormMixin
from tracker.models import Expense
from tracker.money import format_currency
from tracker.services import AlertLevel, get_category_spending


def flash_budget_status(request, expense):
    """Confirm the save and warn if the expense pushed its category past a threshold."""
    category = expense.category
    messages.success(request, f"Saved {format_currency(expense.amount)} under {category.name}.")
    status = get_category_spending(category, expense.date)
    month = f"{expense.date:%B %Y}"
    if status.alert_level is AlertLevel.DANGER:
        messages.error(
            request,
            f"{category.name} is at {status.percentage}% of its {month} budget "
            f"({format_currency(status.spent)} of {format_currency(status.limit)}).",
        )
    elif status.alert_level is AlertLevel.WARNING:
        messages.warning(
            request,
            f"{category.name} has used {status.percentage}% of its {month} budget. "
            f"{format_currency(status.remaining)} left.",
        )


class ExpenseListView(LoginRequiredMixin, ListView):
    template_name = "tracker/expense_list.html"
    context_object_name = "expenses"
    paginate_by = 20

    def get_queryset(self):
        self.filter_form = ExpenseFilterForm(self.request.GET or None, user=self.request.user)
        expenses = Expense.objects.for_user(self.request.user).select_related("category")
        return self.filter_form.filter(expenses)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        context["filtered_total"] = self.object_list.total()
        return context


class ExpenseCreateView(LoginRequiredMixin, UserFormMixin, CreateView):
    """Handles ``POST /expenses/create/``: 302 to the dashboard, or 200 with errors."""

    model = Expense
    form_class = ExpenseForm
    success_url = reverse_lazy("tracker:dashboard")

    def get_initial(self):
        initial = super().get_initial()
        if category := self.request.GET.get("category"):
            initial["category"] = category
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        flash_budget_status(self.request, self.object)
        return response


class ExpenseUpdateView(OwnedObjectMixin, UserFormMixin, UpdateView):
    model = Expense
    form_class = ExpenseForm
    success_url = reverse_lazy("tracker:expense_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        flash_budget_status(self.request, self.object)
        return response


class ExpenseDeleteView(OwnedObjectMixin, SuccessMessageMixin, DeleteView):
    queryset = Expense.objects.select_related("category")
    success_url = reverse_lazy("tracker:expense_list")
    success_message = "Expense deleted."
