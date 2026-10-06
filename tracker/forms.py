from django import forms
from django.core.exceptions import ValidationError

from core.forms import BootstrapFormMixin

from .fields import CategoryChoiceField, MonthField
from .models import Budget, Category, Expense

AMOUNT_WIDGET_ATTRS = {"step": "0.01", "min": "0.01", "inputmode": "decimal", "placeholder": "0.00"}


class OwnedModelForm(BootstrapFormMixin, forms.ModelForm):
    """Model form bound to the logged-in user.

    The owner always comes from the request, never from submitted data, and any
    ``category`` field only offers that user's categories.
    """

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.instance.user = user
        if "category" in self.fields:
            self.fields["category"].queryset = Category.objects.for_user(user)


class CategoryForm(OwnedModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Food"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        duplicates = (
            Category.objects.for_user(self.user)
            .filter(name__iexact=name)
            .exclude(pk=self.instance.pk)
        )
        if duplicates.exists():
            raise ValidationError("You already have a category with this name.", code="duplicate")
        return name


class BudgetForm(OwnedModelForm):
    category = CategoryChoiceField(
        queryset=Category.objects.none(), empty_label="Select a category"
    )
    month_year = MonthField(label="Month")

    class Meta:
        model = Budget
        fields = ["category", "month_year", "monthly_limit"]
        labels = {"monthly_limit": "Monthly limit"}
        widgets = {"monthly_limit": forms.NumberInput(attrs=AMOUNT_WIDGET_ATTRS)}

    def clean_monthly_limit(self):
        limit = self.cleaned_data["monthly_limit"]
        if limit is not None and limit <= 0:
            raise ValidationError("The monthly limit must be greater than zero.", code="min_value")
        return limit

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        month = cleaned_data.get("month_year")
        if category and month:
            clash = (
                Budget.objects.for_user(self.user)
                .filter(category=category, month_year=month)
                .exclude(pk=self.instance.pk)
            )
            if clash.exists():
                raise ValidationError(
                    f"{category.name} already has a budget for {month:%B %Y}. "
                    "Edit that budget instead.",
                    code="duplicate",
                )
        return cleaned_data


class ExpenseForm(OwnedModelForm):
    category = CategoryChoiceField(
        queryset=Category.objects.none(), empty_label="Select a category"
    )

    class Meta:
        model = Expense
        fields = ["amount", "date", "category", "notes"]
        widgets = {
            "amount": forms.NumberInput(attrs=AMOUNT_WIDGET_ATTRS),
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional"}),
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount is not None and amount <= 0:
            raise ValidationError("Amount must be greater than zero.", code="min_value")
        return amount


class ExpenseFilterForm(BootstrapFormMixin, forms.Form):
    month = MonthField(required=False)
    category = forms.ModelChoiceField(
        queryset=Category.objects.none(), required=False, empty_label="All categories"
    )
    q = forms.CharField(
        required=False,
        max_length=100,
        label="Search notes",
        widget=forms.TextInput(attrs={"type": "search", "placeholder": "Search notes"}),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.for_user(user)

    @property
    def is_active(self):
        return self.is_valid() and any(self.cleaned_data.values())

    def filter(self, queryset):
        """Apply the valid filters to ``queryset``; invalid input is ignored."""
        if not self.is_valid():
            return queryset
        month = self.cleaned_data["month"]
        category = self.cleaned_data["category"]
        search = self.cleaned_data["q"]
        if month:
            queryset = queryset.in_month(month)
        if category:
            queryset = queryset.filter(category=category)
        if search:
            queryset = queryset.filter(notes__icontains=search)
        return queryset


class CategoryDeleteForm(BootstrapFormMixin, forms.Form):
    """Confirms a category deletion and, when needed, where its expenses go."""

    move_expenses_to = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        required=False,
        empty_label="Choose a category",
        label="Move its expenses to",
    )

    def __init__(self, *args, category, **kwargs):
        super().__init__(*args, **kwargs)
        self.category = category
        self.expense_count = (
            Expense.objects.for_user(category.user_id).filter(category=category).count()
        )
        self.fields["move_expenses_to"].queryset = Category.objects.for_user(
            category.user_id
        ).exclude(pk=category.pk)

    def clean(self):
        cleaned_data = super().clean()
        if (
            self.expense_count
            and "move_expenses_to" not in self.errors
            and not cleaned_data.get("move_expenses_to")
        ):
            raise ValidationError(
                "This category still has expenses. Choose another category to move them to "
                "before deleting it.",
                code="has_expenses",
            )
        return cleaned_data
