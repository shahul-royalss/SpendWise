from django.contrib import admin

from .models import Budget, Category, Expense


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "created_at")
    search_fields = ("name", "description", "user__username")
    list_select_related = ("user",)
    raw_id_fields = ("user",)


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("category", "month_year", "monthly_limit", "user")
    list_filter = ("month_year",)
    search_fields = ("category__name", "user__username")
    list_select_related = ("category", "user")
    raw_id_fields = ("user", "category")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("date", "amount", "category", "user")
    list_filter = ("date",)
    search_fields = ("notes", "category__name", "user__username")
    date_hierarchy = "date"
    list_select_related = ("category", "user")
    raw_id_fields = ("user", "category")
