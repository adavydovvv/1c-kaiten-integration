import requests

class OneCClient:
    def __init__(self, base_url: str, username: str, password: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _handle_response(self, response: requests.Response):
        if not response.ok:
            raise Exception(
                f"1C API error: {response.status_code}\n"
                f"URL: {response.url}\n"
                f"Response: {response.text}"
            )

        if not response.text:
            return None

        return response.json()

    def get_changed_tasks(self):
        response = self.session.get(
            f"{self.base_url}/tasks/changed",
            timeout=self.timeout
        )
        return self._handle_response(response)

    def update_task_sync_fields(self, uuid: str, kaiten_id: str, external_status: str, kaiten_card_url: str):
        payload = {
            "uuid": uuid,
            "kaiten_id": kaiten_id,
            "external_status": external_status,
            "kaiten_card_url": kaiten_card_url,
        }
        response = self.session.post(
            f"{self.base_url}/tasks/sync",
            json=payload,
            timeout=self.timeout
        )
        return self._handle_response(response)

    def apply_from_kaiten(
        self,
        kaiten_id: str,
        external_status: str,
        kaiten_card_url: str,
        external_priority: str,
        uuid: str = "",
        title: str = "",
        actual_hours: float = 0,
    ):
        payload = {
            "kaiten_id": kaiten_id,
            "external_status": external_status,
            "kaiten_card_url": kaiten_card_url,
            "external_priority": external_priority,
            "uuid": uuid,
            "title": title,
            "actual_hours": actual_hours,
        }
        response = self.session.post(
            f"{self.base_url}/tasks/from-kaiten",
            json=payload,
            timeout=self.timeout
        )
        return self._handle_response(response)

    # ИЗМЕНЕНО: Было get_service_settings
    def get_project_settings(self):
        response = self.session.get(
            f"{self.base_url}/settings/projects", # ИЗМЕНЕН URL
            timeout=self.timeout
        )
        return self._handle_response(response)

    # ИЗМЕНЕНО: Было update_service_settings
    def update_project_settings(self, settings_list: list):
        response = self.session.post(
            f"{self.base_url}/settings/projects", # ИЗМЕНЕН URL
            json=settings_list,
            timeout=self.timeout
        )
        return self._handle_response(response)

    def get_global_settings(self):
        response = self.session.get(
            f"{self.base_url}/settings/global",
            timeout=self.timeout
        )
        return self._handle_response(response)