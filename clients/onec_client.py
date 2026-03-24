import requests


class OneCClient:
    def __init__(self, base_url: str, username: str, password: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def get_changed_tasks(self):
        response = self.session.get(f"{self.base_url}/tasks/changed", timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def update_task_sync_fields(self, uuid: str, kaiten_id: str, external_status: str, kaiten_card_url: str):
        payload = {
            "uuid": uuid,
            "kaiten_id": kaiten_id,
            "external_status": external_status,
            "kaiten_card_url": kaiten_card_url,
        }
        response = self.session.post(f"{self.base_url}/tasks/sync", json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def create_or_update_from_kaiten(self, payload: dict):
        response = self.session.post(f"{self.base_url}/tasks/from-kaiten", json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
