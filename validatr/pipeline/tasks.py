import os
import enum

from celery import chain, shared_task


from PIL import Image, UnidentifiedImageError

from validatr.utils.webhooks import webhook_post
from validatr.api.models import Asset, IN_PROGRESS, COMPLETE, FAILED

from validatr.api.assets.serializers import (
    CreateAssetRequestSerializer,
    GetAssetResponseSerializer,
    GetAssetWithErrorsResponseSerializer,
)


ON_START = "onStart"
ON_SUCCESS = "onSuccess"
ON_FAILURE = "onFailure"


def report_failure(task, asset_id, message, error_key="asset"):
    """
    When called, this function will halt the pipeline from further steps, and
    report the error to the failure webhook endpoint.
    """

    # Halt the rest of the pipeline from execution.
    task.request.chain = None

    # Set the failed state, along with error messages on the asset record.
    asset = Asset.objects.get(id=asset_id)
    asset.state = FAILED
    asset.errors = {f"{error_key}": [message]}
    asset.save()

    # Prepare and send the webhook payload
    payload = GetAssetWithErrorsResponseSerializer(asset).data
    webhook_post(asset.failure_webhook_endpoint, payload)
    # Print to stdout
    error_msg = f"Asset Validation Failed: id:{asset.id}  notify:{asset.start_webhook_endpoint} payload:{payload}"
    print(error_msg)

    return error_msg


def run_pipeline(asset_id):
    """
    Kicks off the asynchronous validation pipeline for a given asset.
    """

    # The pipeline is an ordered chain of validation asynchronous tasks.
    #
    # If a task succeeds in validation, then the `asset_id` is returned and
    # passed to the next step in the pipeline.
    #
    # If a task fails in validation, then a `FailedValidationException` is
    # raised, which will halt the pipeline, and report the error.
    pipeline = [
        start_pipeline.s(asset_id),
        validate_asset_path.s(),
        validate_asset_is_image.s(),
        validate_asset_is_jpeg.s(),
        validate_asset_dimensions.s(),
        end_pipeline.s(),
    ]
    return chain(pipeline).apply_async()


def trigger_hook(asset_id, hook_name):
    """
    Update the asset record with the new state, then send the webhook notification.
    """
    asset = Asset.objects.get(id=asset_id)

    if hook_name == ON_START:
        asset.state = IN_PROGRESS
        asset.save()

        payload = GetAssetResponseSerializer(asset).data

        print(
            f"Asset Validation Started: id:{asset.id} notify:{asset.start_webhook_endpoint} payload:{payload}"
        )

        webhook_post(asset.start_webhook_endpoint, payload)
    elif hook_name == ON_SUCCESS:
        asset.state = COMPLETE
        asset.save()

        payload = GetAssetResponseSerializer(asset).data

        print(
            f"Asset Validation Complete: id:{asset.id} notify:{asset.success_webhook_endpoint} payload:{payload}"
        )

        webhook_post(asset.success_webhook_endpoint, payload)


@shared_task
def start_pipeline(asset_id):
    trigger_hook(asset_id, ON_START)
    return asset_id


@shared_task
def end_pipeline(asset_id):
    trigger_hook(asset_id, ON_SUCCESS)
    return asset_id


@shared_task(bind=True)
def validate_asset_path(self, asset_id):
    """Ensure the file is reachable by the server."""
    asset = Asset.objects.get(id=asset_id)

    if not os.path.exists(asset.path):
        return report_failure(
            self, asset.id, "Asset path is not reachable.", error_key=ON_START
        )

    return asset.id


@shared_task(bind=True)
def validate_asset_is_image(self, asset_id):
    """Ensure the file is an image."""
    asset = Asset.objects.get(id=asset_id)

    # Check that the asset is indeed an image.
    try:
        with Image.open(asset.path) as img:
            img.verify()
            return asset.id
    except UnidentifiedImageError:
        return report_failure(self, asset.id, "Asset is not an image.")


@shared_task(bind=True)
def validate_asset_is_jpeg(self, asset_id):
    """Ensure the file is a JPEG."""
    asset = Asset.objects.get(id=asset_id)

    # NOTE(jake): Though it is common to use the file extension to determine the
    # file type, this can be spoofed or incorrect. Instead we open the file and
    # explicitly check the file signature via Pillow.
    with Image.open(asset.path) as img:
        if img.format != "JPEG":
            return report_failure(
                self,
                asset.id,
                f"Assets must be a JPEG, the provided image is a {img.format}",
            )

    return asset.id


@shared_task(bind=True)
def validate_asset_dimensions(self, asset_id):
    asset = Asset.objects.get(id=asset_id)

    MAX_DIMENSION = 1000

    # from celery.contrib import rdb

    # rdb.set_trace()
    with Image.open(asset.path) as img:
        if img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
            return report_failure(
                self,
                asset.id,
                f"Image dimensions must have a width and height smaller than 1000px. The provided image has dimensions of {img.width}x{img.height}px.",
            )
    return asset.id
