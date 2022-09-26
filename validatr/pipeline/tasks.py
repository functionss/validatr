import os

import validators

from celery import chain, shared_task
from PIL import Image, UnidentifiedImageError

from validatr.utils.webhooks import webhook_post
from validatr.api.models import Asset, IN_PROGRESS, COMPLETE, FAILED
from validatr.api.assets.serializers import (
    GetAssetResponseSerializer,
    GetAssetWithErrorsResponseSerializer,
)


ON_START = "onStart"
ON_SUCCESS = "onSuccess"
ON_FAILURE = "onFailure"


@shared_task
def record_errors(asset_id, errors, caller=None):
    """
    When called, will record the errors into the asset record.
    """

    print(f"record_errors: asset_id: {asset_id} errors: {errors} caller: {caller}")

    # Set the failed state, along with error messages on the asset record.
    asset = Asset.objects.get(id=asset_id)

    # If no errors are recorded yet, then we can just set the errors.
    if asset.errors is None:
        asset.errors = errors
    else:
        prev_errors = asset.errors.copy()
        # If errors are already recorded, then we need to merge the new errors
        for key, value in errors.items():
            if key not in prev_errors:
                prev_errors[key] = value
            else:
                prev_errors[key].extend(value)

    asset.save()


def run_pipeline(asset_id):
    """
    Kicks off the asynchronous validation pipeline for a given asset.
    """

    # The pipeline is an ordered chain of validation asynchronous tasks.
    #
    # If a task succeeds in validation, then the `asset_id` is returned and
    # passed to the next step in the pipeline.
    #
    # If a task fails in validation, the error is recorded to the db record.
    # When all of the pipeline tasks have finished, the `end_pipeline` task will
    # notify the onFailure webhook endpoint.
    pipeline = [
        start_pipeline.s(asset_id),
        validate_webhook_urls.s(),
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
        if validators.url(asset.start_webhook_endpoint):
            webhook_post(asset.start_webhook_endpoint, payload)

    elif hook_name == ON_SUCCESS:
        asset.state = COMPLETE
        asset.save()

        payload = GetAssetResponseSerializer(asset).data

        print(
            f"Asset Validation Complete: id:{asset.id} notify:{asset.success_webhook_endpoint} payload:{payload}"
        )

        if validators.url(asset.success_webhook_endpoint):
            webhook_post(asset.success_webhook_endpoint, payload)

    elif hook_name == ON_FAILURE:
        asset.state = FAILED
        asset.save()

        payload = GetAssetWithErrorsResponseSerializer(asset).data

        print(
            f"Asset Validation Failed: id:{asset.id} notify:{asset.failure_webhook_endpoint} payload:{payload}"
        )
        if validators.url(asset.failure_webhook_endpoint):
            webhook_post(asset.failure_webhook_endpoint, payload)


@shared_task
def start_pipeline(asset_id):
    trigger_hook(asset_id, ON_START)
    return asset_id


@shared_task
def end_pipeline(asset_id):
    asset = Asset.objects.get(id=asset_id)
    if asset.errors:
        return trigger_hook(asset.id, ON_FAILURE)

    trigger_hook(asset.id, ON_SUCCESS)
    return asset.id


@shared_task(bind=True)
def validate_webhook_urls(self, asset_id):
    """Check that the webhook urls are valid."""
    asset = Asset.objects.get(id=asset_id)

    ERR_MSG = "`{}`is not a valid URL"

    errors = {}
    if not validators.url(asset.start_webhook_endpoint):
        errors[ON_START] = [ERR_MSG.format(asset.start_webhook_endpoint)]
    if not validators.url(asset.success_webhook_endpoint):
        errors[ON_SUCCESS] = [ERR_MSG.format(asset.success_webhook_endpoint)]
    if not validators.url(asset.failure_webhook_endpoint):
        errors[ON_FAILURE] = [ERR_MSG.format(asset.failure_webhook_endpoint)]
    if errors:
        record_errors(asset.id, errors, caller="validate_webhook_urls")

    return asset.id


@shared_task(bind=True)
def validate_asset_path(self, asset_id):
    """Ensure the file is reachable by the server."""
    asset = Asset.objects.get(id=asset_id)

    if not os.path.exists(asset.path):
        error = {ON_START: ["Asset path is not reachable."]}
        record_errors(asset.id, error, caller="validate_asset_path")

    return asset.id


@shared_task(bind=True)
def validate_asset_is_image(self, asset_id):
    """Ensure the file is an image."""
    asset = Asset.objects.get(id=asset_id)

    # Check that the asset is indeed an image.
    try:
        with Image.open(asset.path) as img:
            img.verify()
    except UnidentifiedImageError:
        error = {"asset": ["Asset is not an image."]}
        record_errors(asset.id, error, caller="validate_asset_is_image")
    except:
        pass

    return asset.id


@shared_task(bind=True)
def validate_asset_is_jpeg(self, asset_id):
    """Ensure the file is a JPEG."""
    asset = Asset.objects.get(id=asset_id)

    # NOTE(jake): Though it is common to use the file extension to determine the
    # file type, this can be spoofed or incorrect. Instead we open the file and
    # explicitly check the file signature via Pillow.
    try:
        with Image.open(asset.path) as img:
            if img.format != "JPEG":
                error = {
                    "asset": [
                        f"Assets must be a JPEG, the provided image is a {img.format}"
                    ]
                }
                record_errors(asset.id, error, caller="validate_asset_is_jpeg")
    except:
        pass

    return asset.id


@shared_task(bind=True)
def validate_asset_dimensions(self, asset_id):
    asset = Asset.objects.get(id=asset_id)

    MAX_DIMENSION = 1000

    try:
        with Image.open(asset.path) as img:
            if img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
                error = {
                    "asset": [
                        f"Image dimensions must have a width and height smaller than 1000px. The provided image has dimensions of {img.width}x{img.height}px.",
                    ]
                }
                record_errors(asset.id, error, caller="validate_asset_dimensions")
    except:
        pass
    return asset.id
