import time
import requests


class KaitenClient:
    def __init__(self, base_url: str, token: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _request(self, method: str, path: str, params: dict | None = None, json_data: dict | None = None,
                 retries: int = 5):
        url = f"{self.base_url}{path}"

        for attempt in range(retries):
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=self.timeout,
            )

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = max(1, int(retry_after))
                    except ValueError:
                        delay = 3
                else:
                    delay = min(2 ** attempt, 10)

                print(f"Rate limit Kaiten, повтор через {delay} сек.")
                time.sleep(delay)
                continue

            if not response.ok:
                raise Exception(
                    f"Kaiten API error: {response.status_code}\n"
                    f"URL: {response.url}\n"
                    f"Response: {response.text}"
                )

            if not response.text:
                return None

            return response.json()

        raise Exception(f"Kaiten API error: 429\nURL: {url}\nResponse: Too many requests, retries exhausted")

    def get(self, path: str, params: dict | None = None):
        return self._request("GET", path, params=params)

    def post(self, path: str, json_data: dict):
        return self._request("POST", path, json_data=json_data)

    def patch(self, path: str, json_data: dict):
        return self._request("PATCH", path, json_data=json_data)

    def get_cards(self, board_id: int | None = None):
        if board_id:
            return self.get("/cards", params={"board_id": board_id})
        return self.get("/cards")

    def create_card(self, payload: dict):
        return self.post("/cards", payload)

    def update_card(self, card_id: int, payload: dict):
        return self.patch(f"/cards/{card_id}", payload)

    def get_spaces(self):
        return self.get("/spaces")

    def get_board_columns(self, board_id: int):
        return self.get(f"/boards/{board_id}/columns")

    def get_custom_properties(self):
        return self.get("/company/custom-properties", params={"limit": 500, "offset": 0})

    def get_metadata_catalog(self):
        spaces = self.get_spaces() or []
        custom_properties = self.get_custom_properties() or []

        boards = []

        for space in spaces:
            for board in space.get("boards", []) or []:
                board_id = board.get("id")
                if not board_id:
                    continue

                time.sleep(0.4)
                columns = self.get_board_columns(int(board_id)) or []

                boards.append({
                    "space_id": space.get("id"),
                    "space_title": space.get("title", ""),
                    "board_id": board.get("id"),
                    "board_title": board.get("title", ""),
                    "board_external_id": board.get("external_id"),
                    "lanes": board.get("lanes", []) or [],
                    "columns": columns,
                })

        return {
            "boards": boards,
            "properties": custom_properties,
        }
