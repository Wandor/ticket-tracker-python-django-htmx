from django.db import models


class Status(models.TextChoices):
    OPEN = "open", "Open"
    IN_PROGRESS = "in_progress", "In progress"
    CLOSED = "closed", "Closed"


class Priority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"


class Ticket(models.Model):
    Status = Status
    Priority = Priority

    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status, default=Status.OPEN)
    priority = models.CharField(max_length=10, choices=Priority, default=Priority.MEDIUM)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Newest first; id breaks ties so pagination is stable.
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["-created_at", "-id"], name="tickets_created_idx"),
            models.Index(fields=["status", "-created_at", "-id"], name="tickets_status_created_idx"),
        ]
        # Choices are only enforced by forms; the CHECKs keep bad values out of the table itself.
        constraints = [
            models.CheckConstraint(condition=models.Q(status__in=Status.values), name="tickets_status_valid"),
            models.CheckConstraint(
                condition=models.Q(priority__in=Priority.values), name="tickets_priority_valid"
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "created_at": self.created_at.isoformat().replace("+00:00", "Z"),
        }
