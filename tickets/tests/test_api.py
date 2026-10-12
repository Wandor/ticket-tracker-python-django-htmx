"""
Integration tests for the JSON API. They run against Postgres (Django creates a throwaway
test database) because the CHECK constraints, ordering and GROUP BY are part of the behavior.
"""

from django.test import TestCase

from tickets.models import Ticket


class TicketApiTestCase(TestCase):
    def create(self, **body):
        response = self.client.post("/tickets", body, content_type="application/json")
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def patch(self, ticket_id, body):
        return self.client.patch(f"/tickets/{ticket_id}", body, content_type="application/json")


class CreateTicketTests(TicketApiTestCase):
    def test_applies_defaults_trims_and_persists(self):
        ticket = self.create(title="  VPN drops every hour  ", description="")

        self.assertEqual(ticket["title"], "VPN drops every hour")
        self.assertIsNone(ticket["description"])
        self.assertEqual(ticket["status"], "open")
        self.assertEqual(ticket["priority"], "medium")
        self.assertTrue(ticket["created_at"].endswith("Z"))
        self.assertTrue(Ticket.objects.filter(pk=ticket["id"], title="VPN drops every hour").exists())

    def test_rejects_invalid_input_without_writing(self):
        response = self.client.post(
            "/tickets", {"title": "   ", "priority": "urgent"}, content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        error = response.json()["error"]
        self.assertEqual(error["code"], "validation_error")
        self.assertEqual(error["fields"]["title"], "is required")
        self.assertEqual(error["fields"]["priority"], "must be one of low, medium, high")
        self.assertEqual(Ticket.objects.count(), 0)


class ListTicketsTests(TicketApiTestCase):
    def test_filters_by_status_and_paginates_newest_first(self):
        for title, status in [("a", "open"), ("b", "closed"), ("c", "open"), ("d", "open")]:
            self.create(title=title, status=status)

        page1 = self.client.get("/tickets", {"status": "open", "limit": 2, "page": 1}).json()
        page2 = self.client.get("/tickets", {"status": "open", "limit": 2, "page": 2}).json()

        self.assertEqual([t["title"] for t in page1["data"]], ["d", "c"])
        self.assertEqual(page1["pagination"], {"page": 1, "limit": 2, "total": 3, "total_pages": 2})
        self.assertEqual([t["title"] for t in page2["data"]], ["a"])

    def test_rejects_unknown_status_and_out_of_range_limit(self):
        response = self.client.get("/tickets", {"status": "pending", "limit": 101})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()["error"]["fields"]), {"status", "limit"})


class UpdateTicketTests(TicketApiTestCase):
    def test_updates_only_the_given_field(self):
        ticket = self.create(title="Reset password", priority="high")

        response = self.patch(ticket["id"], {"status": "in_progress"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "in_progress")
        self.assertEqual(response.json()["priority"], "high")

    def test_rejects_non_updatable_fields_and_unknown_ids(self):
        ticket = self.create(title="Original")

        self.assertEqual(self.patch(ticket["id"], {"title": "Renamed"}).status_code, 400)
        self.assertEqual(self.patch(9999, {"status": "closed"}).status_code, 404)
        self.assertEqual(Ticket.objects.get(pk=ticket["id"]).title, "Original")


class StatsTests(TicketApiTestCase):
    def test_returns_zero_filled_counts_grouped_by_status(self):
        self.assertEqual(
            self.client.get("/tickets/stats").json(), {"open": 0, "in_progress": 0, "closed": 0}
        )

        self.create(title="one")
        self.create(title="two")
        third = self.create(title="three")
        self.patch(third["id"], {"status": "closed"})

        response = self.client.get("/tickets/stats")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"open": 2, "in_progress": 0, "closed": 1})
