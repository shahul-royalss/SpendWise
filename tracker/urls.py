from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "tracker"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="tracker:dashboard"), name="home"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    # Expenses
    path("expenses/", views.ExpenseListView.as_view(), name="expense_list"),
    path("expenses/create/", views.ExpenseCreateView.as_view(), name="expense_create"),
    path("expenses/<int:pk>/update/", views.ExpenseUpdateView.as_view(), name="expense_update"),
    path("expenses/<int:pk>/delete/", views.ExpenseDeleteView.as_view(), name="expense_delete"),
    # Categories
    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/create/", views.CategoryCreateView.as_view(), name="category_create"),
    path("categories/<int:pk>/", views.CategoryDetailView.as_view(), name="category_detail"),
    path(
        "categories/<int:pk>/update/",
        views.CategoryUpdateView.as_view(),
        name="category_update",
    ),
    path(
        "categories/<int:pk>/delete/",
        views.CategoryDeleteView.as_view(),
        name="category_delete",
    ),
    # Budgets
    path("budgets/", views.BudgetListView.as_view(), name="budget_list"),
    path("budgets/create/", views.BudgetCreateView.as_view(), name="budget_create"),
    path("budgets/copy/", views.BudgetCopyView.as_view(), name="budget_copy"),
    path("budgets/<int:pk>/update/", views.BudgetUpdateView.as_view(), name="budget_update"),
    path("budgets/<int:pk>/delete/", views.BudgetDeleteView.as_view(), name="budget_delete"),
]
