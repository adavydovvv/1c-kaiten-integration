import json
from pathlib import Path


class SyncState:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def get_last_sync(self):
        if not self.file_path.exists():
            return None
        return json.loads(self.file_path.read_text(encoding="utf-8")).get("last_sync")

    def save_last_sync(self, value: str):
        self.file_path.write_text(
            json.dumps({"last_sync": value}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
