from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    onec_base_url: str
    onec_username: str
    onec_password: str
    kaiten_site_url: str
    kaiten_base_url: str
    kaiten_token: str
    kaiten_board_id: int
    kaiten_lane_id: int
    kaiten_default_column_id: int
    kaiten_column_queue_id: int
    kaiten_column_in_progress_id: int
    state_file: str
    log_level: str


def load_settings() -> Settings:
    return Settings(
        onec_base_url=os.getenv("ONEC_BASE_URL", "").rstrip("/"),
        onec_username=os.getenv("ONEC_USERNAME", ""),
        onec_password=os.getenv("ONEC_PASSWORD", ""),
        kaiten_site_url=os.getenv("KAITEN_SITE_URL", "").rstrip("/"),
        kaiten_base_url=os.getenv("KAITEN_BASE_URL", "").rstrip("/"),
        kaiten_token=os.getenv("KAITEN_TOKEN", ""),
        kaiten_board_id=int(os.getenv("KAITEN_BOARD_ID", "0")),
        kaiten_lane_id=int(os.getenv("KAITEN_LANE_ID", "0")),
        kaiten_default_column_id=int(os.getenv("KAITEN_DEFAULT_COLUMN_ID", "0")),
        kaiten_column_queue_id=int(os.getenv("KAITEN_COLUMN_QUEUE_ID", "0")),
        kaiten_column_in_progress_id=int(os.getenv("KAITEN_COLUMN_IN_PROGRESS_ID", "0")),
        state_file=os.getenv("STATE_FILE", "state/last_sync.json"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
