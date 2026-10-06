from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.functional import cached_property

from .dates import add_months, current_month, parse_month


class OwnedObjectMixin(LoginRequiredMixin):
    """Limit a model view to rows owned by the logged-in user.

    Another user's object is simply not in the queryset, so it produces a 404
    instead of revealing that it exists.
    """

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class UserFormMixin:
    """Pass the logged-in user to forms that scope their choices per user."""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class MonthNavigationMixin:
    """Read ``?month=YYYY-MM`` (default: the current month) and add navigation links."""

    @cached_property
    def month(self):
        return parse_month(self.request.GET.get("month")) or current_month()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            month=self.month,
            previous_month=add_months(self.month, -1),
            next_month=add_months(self.month, 1),
            is_current_month=self.month == current_month(),
        )
        return context
