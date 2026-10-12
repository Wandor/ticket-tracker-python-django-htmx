"""Smoke tests for the HTMX views: they render, mutate, and signal the page to refresh."""

from django.test import TestCase

from tickets.models import Ticket


class TicketUiTests(TestCase):
    def test_index_lists_tickets_with_status_and_priority(self):
        Ticket.objects.create(title="Laptop will not boot", priority="high")

        response = self.client.get("/")

        self.assertContains(response, "Laptop will not boot")
        self.assertContains(response, 'class="badge priority-high"')

    def test_create_form_shows_errors_and_triggers_refresh_on_success(self):
        invalid = self.client.post("/ui/tickets/new", {"title": ""})
        self.assertContains(invalid, "Title is required")
        self.assertNotIn("HX-Trigger", invalid.headers)

        created = self.client.post("/ui/tickets/new", {"title": "From the form", "priority": "low"})
        self.assertEqual(created.headers["HX-Trigger"], "tickets-changed")
        self.assertTrue(Ticket.objects.filter(title="From the form", priority="low").exists())

    def test_status_change_updates_ticket(self):
        ticket = Ticket.objects.create(title="Printer jam")

        response = self.client.post(f"/ui/tickets/{ticket.id}/status", {"status": "closed"})

        self.assertEqual(response.status_code, 204)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "closed")
