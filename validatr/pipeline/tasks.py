import os
import enum

from celery import chain, shared_task
from PIL import Image

from validatr.utils.webhooks import webhook_post
from validatr.api.models import Asset, IN_PROGRESS, COMPLETE, FAILED

from validatr.api.assets.image.serializers import (
    CreateAssetRequestSerializer,
    GetAssetResponseSerializer,
    GetAssetWithErrorsResponseSerializer,
)


ON_START = "onStart"
ON_SUCCESS = "onSuccess"
ON_FAILURE = "onFailure"


def run_pipeline(asset_id):
    # the result of the first add job will be
    # the first argument of the second add job
    pipeline = [
        start_pipeline.s(asset_id),
        validate_asset_path.s(),
        validate_asset_is_image.s(),
        validate_asset_is_jpeg.s(),
        validate_asset_dimensions.s(),
        end_pipeline.s(),
    ]
    return chain(pipeline).apply_async()


@shared_task
def trigger_hook(asset_id, hook_name, error_key=None, error=None):
    """
    Update the asset record with the new state, then send the webhook notification.
    """
    asset = Asset.objects.get(id=asset_id)
    if hook_name == ON_START:
        asset.state = IN_PROGRESS
        asset.save()

        json_body = GetAssetResponseSerializer(asset).data

        webhook_post(asset.start_webhook_endpoint, json_body)
    elif hook_name == ON_SUCCESS:
        asset.state = COMPLETE
        asset.save()

        json_body = GetAssetResponseSerializer(asset).data
        webhook_post(asset.success_webhook_endpoint, json_body)


@shared_task
def report_failure(asset_id, error_key, error):
    """
    Update the asset record, then send the onFailure webhook update
    """
    asset = Asset.objects.get(id=asset_id)
    asset.state = FAILED

    errors = asset.errors

    if asset.errors is None:
        asset.errors = {f"{error_key}": [error]}
    else:
        if error_key in errors:
            errors[error_key] = errors[error_key].push(error)
            asset.errors = errors

    asset.save()

    json_body = GetAssetWithErrorsResponseSerializer(asset).data

    webhook_post(asset.failure_webhook_endpoint, json_body)

    # Throwing an exception will print the error to stdout, as well as cancel the
    # rest of the pipeline.
    raise Exception(f"Asset Validation Failed: id:{asset_id}, error:{error}")


@shared_task
def start_pipeline(asset_id):
    trigger_hook(asset_id, ON_START)
    return asset_id


@shared_task
def end_pipeline(asset_id):
    trigger_hook(asset_id, ON_SUCCESS)
    return asset_id


@shared_task
def validate_asset_path(asset_id):
    """Ensure the file is reachable by the server."""
    asset = Asset.objects.get(id=asset_id)

    # check that asset.path is reachable
    if os.path.exists(asset.path):
        return asset.id

    report_failure(asset.id, "asset", "Asset path is not reachable")
    return False


@shared_task
def validate_asset_is_image(asset_id):
    """Ensure the file is an image."""
    asset = Asset.objects.get(id=asset_id)

    # Check that the asset is indeed an image.
    with Image.open(asset.path) as img:
        try:
            img.verify()
            return asset.id
        except Exception as e:
            report_failure(asset.id, "asset", "Asset is not an image.")
            return False


@shared_task
def validate_asset_is_jpeg(asset_id):
    """Ensure the file is a JPEG."""
    asset = Asset.objects.get(id=asset_id)

    # NOTE(jake): Though it is common to use the file extension to determine the
    # file type, this can be spoofed or incorrect. Instead we open the file and
    # explicitly check the file signature via Pillow.
    with Image.open(asset.path) as img:
        if img.format != "JPEG":
            report_failure(
                asset.id,
                "asset",
                f"Assets must be a JPEG, the provided image is a {img.format}",
            )
            return False

    return asset.id


@shared_task
def validate_asset_dimensions(asset_id):
    asset = Asset.objects.get(id=asset_id)

    MAX_DIMENSION = 1000

    with Image.open(asset.path) as img:
        if img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
            report_failure(
                asset.id,
                "asset",
                f"Image dimensions must have a width and height smaller than 1000px. The provided image has dimensions of {img.width}x{img.height}px.",
            )
            return False
    return asset.id
