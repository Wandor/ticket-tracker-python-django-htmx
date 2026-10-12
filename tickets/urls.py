from django.urls import path

from . import api, views

app_name = "tickets"

urlpatterns = [
    # JSON API. "stats" is matched before the <int:ticket_id> route can see it.
    path("tickets", api.tickets_collection, name="api-collection"),
    path("tickets/stats", api.ticket_stats, name="api-stats"),
    path("tickets/<int:ticket_id>", api.ticket_detail, name="api-detail"),
    # HTMX UI.
    path("", views.index, name="index"),
    path("ui/tickets", views.ticket_list, name="ui-list"),
    path("ui/tickets/new", views.create_ticket, name="ui-create"),
    path("ui/tickets/<int:ticket_id>/status", views.update_status, name="ui-status"),
    path("ui/stats", views.stats, name="ui-stats"),
]
