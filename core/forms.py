from django import forms


class BootstrapFormMixin:
    """Give each widget its Bootstrap 5 class and mark fields that failed validation.

    Text inputs also get a placeholder, which Bootstrap's floating labels need.
    Keeps styling out of the templates without adding a form-rendering package.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css_class = "form-check-input"
            elif isinstance(widget, forms.Select):
                css_class = "form-select"
            else:
                css_class = "form-control"
                widget.attrs.setdefault("placeholder", field.label or name.replace("_", " "))
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css_class}".strip()

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                widget = self.fields[name].widget
                widget.attrs["class"] = f"{widget.attrs.get('class', '')} is-invalid".strip()
                widget.attrs["aria-invalid"] = "true"
