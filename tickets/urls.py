from django.urls import path

from . import api

app_name = "tickets"

urlpatterns = [
    # JSON API. "stats" is matched before the <int:ticket_id> route can see it.
    path("tickets", api.tickets_collection, name="api-collection"),
    path("tickets/stats", api.ticket_stats, name="api-stats"),
    path("tickets/<int:ticket_id>", api.ticket_detail, name="api-detail"),
]
