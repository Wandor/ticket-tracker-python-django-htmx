"""
JSON REST API for tickets.

Plain Django views rather than Django REST Framework: four endpoints over one model do not
need serializers, viewsets or a browsable API, and the validation rules live in forms.py where
the HTMX UI reuses them.
"""

import json
import math

from django.db.models import Count
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from .forms import TicketCreateForm, TicketListForm, TicketUpdateForm, field_errors
from .models import Ticket

UPDATABLE_FIELDS = {"status", "priority"}


def error_response(status: int, code: str, message: str, fields: dict | None = None) -> JsonResponse:
    body = {"code": code, "message": message}
    if fields:
        body["fields"] = fields
    return JsonResponse({"error": body}, status=status)


def validation_error(fields: dict) -> JsonResponse:
    return error_response(400, "validation_error", "Request validation failed", fields)


def parse_json_object(request: HttpRequest) -> dict | JsonResponse:
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return error_response(400, "invalid_json", "Request body is not valid JSON")
    if not isinstance(data, dict):
        return error_response(400, "invalid_json", "Request body must be a JSON object")
    return data


# The API is token-less JSON consumed by non-browser clients, so CSRF (a cookie-auth defense)
# does not apply. The HTMX UI uses its own CSRF-protected views.
@csrf_exempt
@require_http_methods(["GET", "POST"])
def tickets_collection(request: HttpRequest) -> JsonResponse:
    return list_tickets(request) if request.method == "GET" else create_ticket(request)


def create_ticket(request: HttpRequest) -> JsonResponse:
    data = parse_json_object(request)
    if isinstance(data, JsonResponse):
        return data
    non_strings = {k: "must be a string" for k in ("title", "description", "status", "priority")
                   if data.get(k) is not None and not isinstance(data[k], str)}
    if non_strings:
        return validation_error(non_strings)

    form = TicketCreateForm(data)
    if not form.is_valid():
        return validation_error(field_errors(form))
    return JsonResponse(form.save().to_dict(), status=201)


def list_tickets(request: HttpRequest) -> JsonResponse:
    form = TicketListForm(request.GET)
    if not form.is_valid():
        return validation_error(field_errors(form))
    status, page, limit = form.cleaned_data["status"], form.cleaned_data["page"], form.cleaned_data["limit"]

    queryset = Ticket.objects.all()
    if status:
        queryset = queryset.filter(status=status)
    total = queryset.count()
    offset = (page - 1) * limit
    tickets = queryset[offset : offset + limit]

    return JsonResponse(
        {
            "data": [t.to_dict() for t in tickets],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": math.ceil(total / limit),
            },
        }
    )


@require_GET
def ticket_stats(request: HttpRequest) -> JsonResponse:
    return JsonResponse(count_by_status())


def count_by_status() -> dict[str, int]:
    counts = {status: 0 for status in Ticket.Status.values}
    # order_by() clears Meta.ordering, which would otherwise be added to the GROUP BY.
    for row in Ticket.objects.order_by().values("status").annotate(n=Count("id")):
        counts[row["status"]] = row["n"]
    return counts


@csrf_exempt
@require_http_methods(["PATCH"])
def ticket_detail(request: HttpRequest, ticket_id: int) -> JsonResponse:
    data = parse_json_object(request)
    if isinstance(data, JsonResponse):
        return data

    # Reject other fields outright so a client never believes it renamed a ticket.
    unknown = set(data) - UPDATABLE_FIELDS
    if unknown:
        return validation_error({field: "cannot be updated" for field in sorted(unknown)})

    form = TicketUpdateForm(data)
    if not form.is_valid():
        return validation_error(field_errors(form))

    changes = form.changes()
    updated = Ticket.objects.filter(pk=ticket_id).update(**changes)
    if not updated:
        return error_response(404, "not_found", "Ticket not found")
    return JsonResponse(Ticket.objects.get(pk=ticket_id).to_dict())
