from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Count, ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from tracker.dates import current_month
from tracker.forms import CategoryDeleteForm, CategoryForm
from tracker.mixins import OwnedObjectMixin, UserFormMixin
from tracker.models import Category
from tracker.services import get_category_spending


class CategoryListView(OwnedObjectMixin, ListView):
    model = Category
    context_object_name = "categories"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(
                expense_count=Count("expenses", distinct=True),
                budget_count=Count("budgets", distinct=True),
            )
            .order_by("name")
        )


class CategoryDetailView(OwnedObjectMixin, DetailView):
    model = Category
    context_object_name = "category"
    recent_expense_count = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.object
        month = current_month()
        context["month"] = month
        context["status"] = get_category_spending(category, month)
        context["budgets"] = category.budgets.all()[:12]
        context["expense_count"] = category.expenses.count()
        context["recent_expenses"] = category.expenses.all()[: self.recent_expense_count]
        return context


class CategoryCreateView(LoginRequiredMixin, UserFormMixin, SuccessMessageMixin, CreateView):
    model = Category
    form_class = CategoryForm
    success_url = reverse_lazy("tracker:category_list")
    success_message = 'Category "%(name)s" created.'


class CategoryUpdateView(OwnedObjectMixin, UserFormMixin, SuccessMessageMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    success_message = 'Category "%(name)s" updated.'


class CategoryDeleteView(OwnedObjectMixin, DeleteView):
    """Delete a category without ever orphaning or silently losing expenses.

    Budgets go with the category. Expenses must first be moved to another of
    the user's categories; the move and the delete share one transaction.
    """

    model = Category
    form_class = CategoryDeleteForm
    success_url = reverse_lazy("tracker:category_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["category"] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["budget_count"] = self.object.budgets.count()
        return context

    def form_valid(self, form):
        category = self.object
        target = form.cleaned_data.get("move_expenses_to")
        try:
            with transaction.atomic():
                moved = 0
                if target:
                    moved = category.expenses.update(category=target, updated_at=timezone.now())
                category.delete()
        except ProtectedError:
            messages.error(
                self.request, f'"{category.name}" still has expenses, so it was not deleted.'
            )
            return redirect(category)

        if moved:
            messages.success(
                self.request,
                f'Moved {moved} expense(s) to "{target.name}" and deleted "{category.name}".',
            )
        else:
            messages.success(self.request, f'Category "{category.name}" deleted.')
        return redirect(self.success_url)
