"""
Server-rendered UI. HTMX swaps partials in place, so the page works as a single page without
a JavaScript build step. Every mutation responds with an `HX-Trigger: tickets-changed` header;
the list and stats panels listen for it and refresh themselves.
"""

from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from .api import count_by_status
from .forms import TicketCreateForm, TicketUpdateForm
from .models import Ticket

PAGE_SIZE = 10
CHANGED = "tickets-changed"


def list_context(request: HttpRequest) -> dict:
    """Read filter and page from the query string, falling back to defaults for bad input."""
    status = request.GET.get("status")
    if status not in Ticket.Status.values:
        status = None

    queryset = Ticket.objects.filter(status=status) if status else Ticket.objects.all()
    page = Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))

    def query(page_number: int) -> str:
        params = {"status": status} if status else {}
        params["page"] = page_number
        return urlencode(params)

    return {
        "page": page,
        "current_status": status,
        "statuses": Ticket.Status.choices,
        "current_query": query(page.number),
        "previous_query": query(page.previous_page_number()) if page.has_previous() else None,
        "next_query": query(page.next_page_number()) if page.has_next() else None,
    }


@require_GET
def index(request: HttpRequest) -> HttpResponse:
    context = list_context(request)
    context.update(form=TicketCreateForm(), stats=count_by_status())
    return render(request, "tickets/index.html", context)


@require_GET
def ticket_list(request: HttpRequest) -> HttpResponse:
    return render(request, "tickets/partials/ticket_list.html", list_context(request))


@require_GET
def stats(request: HttpRequest) -> HttpResponse:
    return render(request, "tickets/partials/stats.html", {"stats": count_by_status()})


@require_POST
def create_ticket(request: HttpRequest) -> HttpResponse:
    form = TicketCreateForm(request.POST)
    if not form.is_valid():
        # 200 rather than 4xx so HTMX swaps the form back in with its errors.
        return render(request, "tickets/partials/ticket_form.html", {"form": form})
    form.save()
    response = render(request, "tickets/partials/ticket_form.html", {"form": TicketCreateForm()})
    response["HX-Trigger"] = CHANGED
    return response


@require_POST
def update_status(request: HttpRequest, ticket_id: int) -> HttpResponse:
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    form = TicketUpdateForm({"status": request.POST.get("status")})
    if form.is_valid():
        ticket.status = form.cleaned_data["status"]
        ticket.save(update_fields=["status"])
    response = HttpResponse(status=204)
    response["HX-Trigger"] = CHANGED
    return response
