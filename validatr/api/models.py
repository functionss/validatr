import uuid
from django.db import models

FILE_PROVIDERS = [
    (0, "local"),
    # Not Implemented
    # (1, 's3'),
    # (2, 'gcs'),
    # (3, 'remote'),
]

ASSET_STATES = [
    (1, "queued"),
    (2, "in_progress"),
    (3, "complete"),
    (4, "failed"),
]


class Asset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sha2 = models.CharField(max_length=255, blank=True, null=True)

    path = models.CharField(max_length=32, blank=True, null=True)
    provider = models.PositiveSmallIntegerField(choices=FILE_PROVIDERS, default=0)

    start_webhook_endpoint = models.TextField(blank=True, null=True)
    success_webhook_endpoint = models.TextField(blank=True, null=True)
    failure_webhook_endpoint = models.TextField(blank=True, null=True)

    state = models.PositiveSmallIntegerField(choices=ASSET_STATES, default="queued")

    # FIXME(jake): Someday this could probably morph into a JSONField
    errors = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
