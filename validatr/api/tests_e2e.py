from pathlib import Path

import time

from django.test import TestCase

import requests


def is_docker():
    cgroup = Path("/proc/self/cgroup")
    return (
        Path("/.dockerenv").is_file()
        or cgroup.is_file()
        and cgroup.read_text().find("docker") > -1
    )


BASE_URL = "http://localhost:8000"
if is_docker():
    BASE_URL = "http://app:8000"

CREATE_ASSET_URL = f"{BASE_URL}/assets/image/"
FETCH_ASSET_URL = BASE_URL + "/assets/{id}/"


def _asset_payload(path):

    return {
        "assetPath": {
            "location": "local",
            "path": path,
        },
        "notifications": {
            "onStart": "https://requestbin.io/wtn344wt",
            "onSuccess": "https://requestbin.io/tvn363tv",
            "onFailure": "https://requestbin.io/11fq7f41",
        },
    }


class ValidatorsTestCase(TestCase):
    def setUp(self):

        self.BASE_ASSET_PATH = "./assets"
        if is_docker():
            self.BASE_ASSET_PATH = "/app/assets"

        self.text_asset = _asset_payload(f"{self.BASE_ASSET_PATH}/not-an-image.txt")
        self.jpeg_asset = _asset_payload(f"{self.BASE_ASSET_PATH}/200-ok.jpg")
        self.oversized_asset = _asset_payload(f"{self.BASE_ASSET_PATH}/yuge.jpg")
        self.png_asset = _asset_payload(f"{self.BASE_ASSET_PATH}/png-screenshot.png")
        self.unreachable_asset = _asset_payload(
            f"{self.BASE_ASSET_PATH}/to/nowhere.jpg"
        )

    def test_invalid_webhook_urls(self):
        payload = {
            "assetPath": {
                "location": "local",
                "path": f"{self.BASE_ASSET_PATH}/200-ok.jpg",
            },
            "notifications": {
                "onStart": "wat",
                "onSuccess": "wat",
                "onFailure": "wat",
            },
        }

        jpeg_asset = requests.post(CREATE_ASSET_URL, json=payload)

        jpeg_asset_id = jpeg_asset.json()["id"]

        self.assertEqual(jpeg_asset.status_code, 202)
        self.assertEqual("queued", jpeg_asset.json()["state"])

        time.sleep(3)

        jpeg_final = requests.get(FETCH_ASSET_URL.format(id=jpeg_asset_id)).json()
        jpeg_final_state = jpeg_final["state"]

        exp_err_msg = "`wat`is not a valid URL"
        self.assertEqual(exp_err_msg, jpeg_final["errors"]["onStart"][0])
        self.assertEqual(exp_err_msg, jpeg_final["errors"]["onSuccess"][0])
        self.assertEqual(exp_err_msg, jpeg_final["errors"]["onFailure"][0])
        self.assertEqual("failed", jpeg_final_state)

    def test_valid_jpeg(self):
        jpeg_asset = requests.post(CREATE_ASSET_URL, json=self.jpeg_asset)

        jpeg_asset_id = jpeg_asset.json()["id"]

        self.assertEqual(jpeg_asset.status_code, 202)
        self.assertEqual("queued", jpeg_asset.json()["state"])

        # Image has been queued, now we need to wait a few seconds for the processing to complete.
        time.sleep(3)

        jpeg_final_state = requests.get(
            FETCH_ASSET_URL.format(id=jpeg_asset_id)
        ).json()["state"]
        self.assertEqual("complete", jpeg_final_state)

    def test_validate_asset_path(self):
        unreachable_asset = requests.post(CREATE_ASSET_URL, json=self.unreachable_asset)

        unreachable_asset_id = unreachable_asset.json()["id"]

        self.assertEqual(unreachable_asset.status_code, 202)
        self.assertEqual("queued", unreachable_asset.json()["state"])

        # Image has been queued, now we need to wait a few seconds for the processing to complete.
        time.sleep(3)

        unreachable_final_resp = requests.get(
            FETCH_ASSET_URL.format(id=unreachable_asset_id)
        ).json()

        self.assertEqual("failed", unreachable_final_resp["state"])
        self.assertEqual(
            ["Asset path is not reachable."],
            unreachable_final_resp["errors"]["onStart"],
        )

    def test_validate_asset_is_image(self):
        text_asset = requests.post(CREATE_ASSET_URL, json=self.text_asset)

        text_asset_id = text_asset.json()["id"]

        self.assertEqual(text_asset.status_code, 202)
        self.assertEqual("queued", text_asset.json()["state"])

        # Image has been queued, now we need to wait a few seconds for the processing to complete.
        time.sleep(3)

        text_final_resp = requests.get(FETCH_ASSET_URL.format(id=text_asset_id)).json()

        self.assertEqual("failed", text_final_resp["state"])
        self.assertEqual(
            ["Asset is not an image."],
            text_final_resp["errors"]["asset"],
        )

    def test_validate_asset_is_jpeg(self):
        png_asset = requests.post(CREATE_ASSET_URL, json=self.png_asset)

        png_asset_id = png_asset.json()["id"]

        self.assertEqual(png_asset.status_code, 202)
        self.assertEqual("queued", png_asset.json()["state"])

        # Image has been queued, now we need to wait a few seconds for the processing to complete.
        time.sleep(3)

        png_final_resp = requests.get(FETCH_ASSET_URL.format(id=png_asset_id)).json()

        self.assertEqual("failed", png_final_resp["state"])
        self.assertEqual(
            ["Assets must be a JPEG, the provided image is a PNG"],
            png_final_resp["errors"]["asset"],
        )

    def test_validate_asset_dimensions(self):
        oversized_asset = requests.post(CREATE_ASSET_URL, json=self.oversized_asset)

        oversized_asset_id = oversized_asset.json()["id"]

        self.assertEqual(oversized_asset.status_code, 202)
        self.assertEqual("queued", oversized_asset.json()["state"])

        # Image has been queued, now we need to wait a few seconds for the processing to complete.
        time.sleep(3)

        oversized_final_resp = requests.get(
            FETCH_ASSET_URL.format(id=oversized_asset_id)
        ).json()

        self.assertEqual("failed", oversized_final_resp["state"])
        self.assertIn(
            "Image dimensions must have a width and height smaller than 1000px.",
            oversized_final_resp["errors"]["asset"][0],
        )
