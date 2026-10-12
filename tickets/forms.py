"""
Validation for ticket input, shared by the JSON API and the HTMX UI so both enforce exactly
the same rules.
"""

from django import forms

from .models import Ticket

STATUS_MESSAGE = "must be one of open, in_progress, closed"
PRIORITY_MESSAGE = "must be one of low, medium, high"
DEFAULT_LIMIT = 20
MAX_LIMIT = 100


class TicketCreateForm(forms.ModelForm):
    # Optional here so omitted values fall back to the model defaults in clean_*.
    status = forms.ChoiceField(
        choices=Ticket.Status.choices, required=False, error_messages={"invalid_choice": STATUS_MESSAGE}
    )
    priority = forms.ChoiceField(
        choices=Ticket.Priority.choices, required=False, error_messages={"invalid_choice": PRIORITY_MESSAGE}
    )

    class Meta:
        model = Ticket
        fields = ["title", "description", "status", "priority"]
        error_messages = {
            "title": {
                "required": "is required",
                "max_length": "must be at most 200 characters",
            },
        }

    def clean_description(self):
        # Store a blank description as NULL so clients can always send the field.
        return self.cleaned_data.get("description") or None

    def clean_status(self):
        return self.cleaned_data.get("status") or Ticket.Status.OPEN

    def clean_priority(self):
        return self.cleaned_data.get("priority") or Ticket.Priority.MEDIUM


class TicketUpdateForm(forms.Form):
    status = forms.ChoiceField(
        choices=Ticket.Status.choices, required=False, error_messages={"invalid_choice": STATUS_MESSAGE}
    )
    priority = forms.ChoiceField(
        choices=Ticket.Priority.choices, required=False, error_messages={"invalid_choice": PRIORITY_MESSAGE}
    )

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("status") and not cleaned.get("priority") and not self.errors:
            raise forms.ValidationError("provide status and/or priority")
        return cleaned

    def changes(self) -> dict:
        return {k: v for k, v in self.cleaned_data.items() if v}


class TicketListForm(forms.Form):
    status = forms.ChoiceField(
        choices=Ticket.Status.choices, required=False, error_messages={"invalid_choice": STATUS_MESSAGE}
    )
    page = forms.IntegerField(
        required=False,
        min_value=1,
        error_messages={"invalid": "must be a positive integer", "min_value": "must be a positive integer"},
    )
    limit = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=MAX_LIMIT,
        error_messages={
            "invalid": f"must be an integer between 1 and {MAX_LIMIT}",
            "min_value": f"must be an integer between 1 and {MAX_LIMIT}",
            "max_value": f"must be an integer between 1 and {MAX_LIMIT}",
        },
    )

    def clean_page(self):
        return self.cleaned_data.get("page") or 1

    def clean_limit(self):
        return self.cleaned_data.get("limit") or DEFAULT_LIMIT


def field_errors(form: forms.Form) -> dict[str, str]:
    """Flatten Django's error lists into the API's {field: message} shape."""
    return {
        ("body" if field == "__all__" else field): errors[0]["message"]
        for field, errors in form.errors.get_json_data().items()
    }
