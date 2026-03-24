import time
import requests


class KaitenClient:
    def __init__(self, base_url: str, token: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def _request(self, method: str, path: str, **kwargs):
        url = f"{self.base_url}{path}"

        for _ in range(3):
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "1"))
                time.sleep(retry_after)
                continue

            response.raise_for_status()
            return response

        raise RuntimeError("Kaiten API request failed after retries")

    def get_cards(self):
        return self._request("GET", "/cards").json()

    def create_card(self, payload: dict):
        return self._request("POST", "/cards", json=payload).json()

    def update_card(self, card_id: int, payload: dict):
        return self._request("PUT", f"/cards/{card_id}", json=payload).json()
