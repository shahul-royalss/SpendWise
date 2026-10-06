from django import forms
from django.core.exceptions import ValidationError

from .dates import MAX_YEAR, MIN_YEAR


class MonthInput(forms.DateInput):
    input_type = "month"

    def __init__(self, attrs=None):
        super().__init__(attrs={"placeholder": "YYYY-MM", **(attrs or {})}, format="%Y-%m")


class MonthField(forms.DateField):
    """A ``YYYY-MM`` field whose cleaned value is the first day of that month."""

    widget = MonthInput
    input_formats = ["%Y-%m", "%Y-%m-%d"]
    default_error_messages = {"invalid": "Enter a valid month in YYYY-MM format."}

    def to_python(self, value):
        result = super().to_python(value)
        if result is None:
            return None
        if not MIN_YEAR <= result.year <= MAX_YEAR:
            raise ValidationError(
                f"Choose a month between {MIN_YEAR} and {MAX_YEAR}.", code="out_of_range"
            )
        return result.replace(day=1)


class CategoryChoiceField(forms.ModelChoiceField):
    """Category picker that accepts either the primary key or the category name.

    The HTML form posts the id from a ``<select>``, while scripted clients can
    send the readable name (``category=Food``). Both lookups only search the
    queryset given to the field, which is always the current user's categories.
    """

    def to_python(self, value):
        try:
            return super().to_python(value)
        except ValidationError:
            category = self.queryset.filter(name__iexact=str(value).strip()).first()
            if category is None:
                raise
            return category
