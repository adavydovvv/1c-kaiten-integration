from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    onec_base_url: str
    onec_username: str
    onec_password: str
    kaiten_base_url: str
    kaiten_token: str
    state_file: str
    log_level: str


def load_settings() -> Settings:
    return Settings(
        onec_base_url=os.getenv("ONEC_BASE_URL", "").rstrip("/"),
        onec_username=os.getenv("ONEC_USERNAME", ""),
        onec_password=os.getenv("ONEC_PASSWORD", ""),
        kaiten_base_url=os.getenv("KAITEN_BASE_URL", "").rstrip("/"),
        kaiten_token=os.getenv("KAITEN_TOKEN", ""),
        state_file=os.getenv("STATE_FILE", "state/last_sync.json"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
