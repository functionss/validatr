import enum
import uuid
from django.db import models

FILE_PROVIDERS = [
    ("local", "local"),
    # Not Implemented
    # (1, 's3'),
    # (2, 'gcs'),
    # (3, 'remote'),
]


QUEUED = "queued"
IN_PROGRESS = "in_progress"
COMPLETE = "complete"
FAILED = "failed"

ASSET_STATES = [
    (QUEUED, QUEUED),
    (IN_PROGRESS, IN_PROGRESS),
    (COMPLETE, COMPLETE),
    (FAILED, FAILED),
]


class Asset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    path = models.TextField(blank=False, null=False)
    provider = models.CharField(max_length=16, choices=FILE_PROVIDERS, default=0)

    start_webhook_endpoint = models.TextField(blank=True, null=True)
    success_webhook_endpoint = models.TextField(blank=True, null=True)
    failure_webhook_endpoint = models.TextField(blank=True, null=True)

    state = models.CharField(max_length=16, choices=ASSET_STATES, default="queued")

    # FIXME(jake): Someday this could probably morph into a JSONField
    errors = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
