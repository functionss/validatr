from unittest.mock import patch

from django.test import TestCase


from validatr.api.models import Asset
from validatr.pipeline.tasks import (
    validate_asset_path,
    validate_asset_is_image,
    validate_asset_is_jpeg,
    validate_asset_dimensions,
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

    @patch("validatr.pipeline.tasks.webhook_post", autospec=True)
    def test_validate_asset_path(self, mock_webhook_post):

        resp_available = validate_asset_path(self.jpeg_asset.id)
        mock_webhook_post.assert_not_called()
        self.assertEqual(resp_available, self.jpeg_asset.id)

        resp_unavailable = validate_asset_path(self.unreachable_asset.id)
        mock_webhook_post.assert_called_once()
        self.assertIn("not reachable", resp_unavailable)

        self.assertEqual(
            Asset.objects.get(id=self.unreachable_asset.id).state, "failed"
        )

    @patch("validatr.pipeline.tasks.webhook_post", autospec=True)
    def test_validate_asset_is_image(self, mock_webhook_post):
        mock_webhook_post.return_value = True

        resp_image = validate_asset_is_image(self.jpeg_asset.id)
        self.assertEqual(resp_image, self.jpeg_asset.id)
        mock_webhook_post.assert_not_called()

        resp_text = validate_asset_is_image(self.text_asset.id)
        mock_webhook_post.assert_called_once()
        self.assertIn("not an image", resp_text)

        self.assertEqual(Asset.objects.get(id=self.text_asset.id).state, "failed")

    @patch("validatr.pipeline.tasks.webhook_post", autospec=True)
    def test_validate_asset_is_jpeg(self, mock_webhook_post):
        mock_webhook_post.return_value = True

        resp_image = validate_asset_is_jpeg(self.jpeg_asset.id)
        self.assertEqual(resp_image, self.jpeg_asset.id)
        mock_webhook_post.assert_not_called()

        resp_text = validate_asset_is_jpeg(self.png_asset.id)
        mock_webhook_post.assert_called_once()
        self.assertIn("the provided image is a PNG", resp_text)

        self.assertEqual(Asset.objects.get(id=self.png_asset.id).state, "failed")

    @patch("validatr.pipeline.tasks.webhook_post", autospec=True)
    def test_validate_asset_dimensions(self, mock_webhook_post):
        mock_webhook_post.return_value = True

        resp_image = validate_asset_dimensions(self.jpeg_asset.id)
        self.assertEqual(resp_image, self.jpeg_asset.id)
        mock_webhook_post.assert_not_called()

        resp_text = validate_asset_dimensions(self.oversized_asset.id)
        mock_webhook_post.assert_called_once()
        self.assertIn("must have a width and height smaller than 1000px", resp_text)

        self.assertEqual(Asset.objects.get(id=self.oversized_asset.id).state, "failed")
