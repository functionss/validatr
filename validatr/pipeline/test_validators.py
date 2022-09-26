from unittest.mock import patch

from django.test import TestCase


from validatr.api.models import Asset
from validatr.pipeline.tasks import (
    validate_asset_path,
    validate_asset_is_image,
    validate_asset_is_jpeg,
    validate_asset_dimensions,
    validate_webhook_urls,
)


def _create_asset(path):
    return Asset.objects.create(
        path=path,
        start_webhook_endpoint="http://fake-start-endpoint.com/",
        success_webhook_endpoint="http://fake-success-endpoint.com/",
        failure_webhook_endpoint="http://fake-failure-endpoint.com/",
    )


class ValidatorsTestCase(TestCase):
    def setUp(self):
        self.text_asset = _create_asset("./assets/not-an-image.txt")
        self.jpeg_asset = _create_asset("./assets/200-ok.jpg")
        self.oversized_asset = _create_asset("./assets/yuge.jpg")
        self.png_asset = _create_asset("./assets/png-screenshot.png")
        self.unreachable_asset = _create_asset("./path/to/nowhere.jpg")

    def test_validate_webhook_urls(self):

        asset_with_invalid_hooks = Asset.objects.create(
            path="./assets/200-ok.jpg",
            start_webhook_endpoint="wat",
            success_webhook_endpoint="wat",
            failure_webhook_endpoint="wat",
        )
        resp = validate_webhook_urls(asset_with_invalid_hooks.id)

        post_validation_asset = Asset.objects.get(id=asset_with_invalid_hooks.id)

        exp_err_msg = "`wat`is not a valid URL"
        self.assertEqual(post_validation_asset.errors["onStart"], [exp_err_msg])
        self.assertEqual(post_validation_asset.errors["onSuccess"], [exp_err_msg])
        self.assertEqual(post_validation_asset.errors["onFailure"], [exp_err_msg])

    def test_validate_asset_path(self):
        validate_asset_path(self.jpeg_asset.id)
        jpeg_asset = Asset.objects.get(id=self.jpeg_asset.id)
        self.assertEqual(jpeg_asset.errors, None)

        validate_asset_path(self.unreachable_asset.id)
        unreachable_asset = Asset.objects.get(id=self.unreachable_asset.id)
        self.assertEqual(
            unreachable_asset.errors, {"onStart": ["Asset path is not reachable."]}
        )

    def test_validate_asset_is_image(self):

        validate_asset_is_image(self.jpeg_asset.id)
        jpeg_asset = Asset.objects.get(id=self.jpeg_asset.id)
        self.assertEqual(jpeg_asset.errors, None)

        validate_asset_is_image(self.text_asset.id)
        unreachable_asset = Asset.objects.get(id=self.text_asset.id)
        self.assertEqual(
            unreachable_asset.errors, {"asset": ["Asset is not an image."]}
        )

    def test_validate_asset_is_jpeg(self):

        validate_asset_is_jpeg(self.jpeg_asset.id)
        jpeg_asset = Asset.objects.get(id=self.jpeg_asset.id)
        self.assertEqual(jpeg_asset.errors, None)

        validate_asset_is_jpeg(self.png_asset.id)
        unreachable_asset = Asset.objects.get(id=self.png_asset.id)
        self.assertEqual(
            unreachable_asset.errors,
            {"asset": ["Assets must be a JPEG, the provided image is a PNG"]},
        )

    def test_validate_asset_dimensions(self):

        validate_asset_dimensions(self.jpeg_asset.id)
        jpeg_asset = Asset.objects.get(id=self.jpeg_asset.id)
        self.assertEqual(jpeg_asset.errors, None)

        validate_asset_dimensions(self.oversized_asset.id)
        unreachable_asset = Asset.objects.get(id=self.oversized_asset.id)
        self.assertIn(
            "Image dimensions must have a width and height smaller than 1000px.",
            unreachable_asset.errors["asset"][0],
        )
