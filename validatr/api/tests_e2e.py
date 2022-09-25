import time

from django.test import TestCase

import requests

CREATE_ASSET_URL = "http://localhost:8000/assets/image/"
FETCH_ASSET_URL = "http://localhost:8000/assets/{id}/"


def _asset_payload(path):
    return {
        "assetPath": {
            "location": "local",
            "path": path,
        },
        "notifications": {
            "onStart": "http://localhost:8000/echo/post/?onStart",
            "onSuccess": "http://localhost:8000/echo/post/?onSuccess",
            "onFailure": "http://localhost:8000/echo/post/?onFailure",
        },
    }


class ValidatorsTestCase(TestCase):
    def setUp(self):
        self.text_asset = _asset_payload("./assets/not-an-image.txt")
        self.jpeg_asset = _asset_payload("./assets/200-ok.jpg")
        self.oversized_asset = _asset_payload("./assets/yuge.jpg")
        self.png_asset = _asset_payload("./assets/png-screenshot.png")
        self.unreachable_asset = _asset_payload("./path/to/nowhere.jpg")

    def test_validate_asset_path(self):
        jpeg_asset = requests.post(CREATE_ASSET_URL, json=self.jpeg_asset)
        unreachable_asset = requests.post(CREATE_ASSET_URL, json=self.unreachable_asset)

        jpeg_asset_id = jpeg_asset.json()["id"]
        unreachable_asset_id = unreachable_asset.json()["id"]

        self.assertEqual(jpeg_asset.status_code, 202)
        self.assertEqual(unreachable_asset.status_code, 202)
        self.assertEqual("queued", jpeg_asset.json()["state"])
        self.assertEqual("queued", unreachable_asset.json()["state"])

        # Images have been queued, now we need to wait a few seconds for the processing to complete.
        time.sleep(3)

        jpeg_final_state = requests.get(
            FETCH_ASSET_URL.format(id=jpeg_asset_id)
        ).json()["state"]
        self.assertEqual("complete", jpeg_final_state)

        unreachable_final_resp = requests.get(
            FETCH_ASSET_URL.format(id=unreachable_asset_id)
        ).json()

        self.assertEqual("failed", unreachable_final_resp["state"])
        self.assertEqual(
            ["Asset path is not reachable."],
            unreachable_final_resp["errors"]["onStart"],
        )
