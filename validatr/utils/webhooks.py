import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def webhook_post(url, body, timeout=10, retries=5, retry_backoff=1.5):
    """
    Send a webhook POST request, with exponential backoff retry
    """

    retry = Retry(
        total=retries,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)

    req = requests.Session()
    req.mount("https://", adapter)
    req.mount("http://", adapter)

    response = req.post(url, json=body, timeout=timeout)

    return response
