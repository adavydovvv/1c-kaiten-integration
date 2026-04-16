import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT_DIR / "config" / "local_config.json"
EXAMPLE_CONFIG_PATH = ROOT_DIR / "config" / "local_config.example.json"


@dataclass
class LocalConfig:
    onec_base_url: str
    onec_username: str
    onec_password: str
    py_service_host: str = "127.0.0.1"
    py_service_port: int = 8088
    state_file: str = "state/last_sync.json"
    log_level: str = "INFO"


def _resolve_path(path: str | Path | None = None) -> Path:
    if path is None:
        return DEFAULT_CONFIG_PATH
    return Path(path)


def ensure_parent_dirs(config: LocalConfig):
    state_path = ROOT_DIR / config.state_file
    state_path.parent.mkdir(parents=True, exist_ok=True)
    (ROOT_DIR / "logs").mkdir(parents=True, exist_ok=True)


def ensure_local_config_exists(path: str | Path | None = None) -> Path:
    config_path = _resolve_path(path)

    if config_path.exists():
        return config_path

    config_path.parent.mkdir(parents=True, exist_ok=True)

    if EXAMPLE_CONFIG_PATH.exists():
        shutil.copyfile(EXAMPLE_CONFIG_PATH, config_path)
        return config_path

    default_data = {
        "onec_base_url": "http://localhost/ERP/hs/kaiten",
        "onec_username": "Admin",
        "onec_password": "",
        "py_service_host": "127.0.0.1",
        "py_service_port": 8088,
        "state_file": "state/last_sync.json",
        "log_level": "INFO"
    }

    config_path.write_text(
        json.dumps(default_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return config_path


def load_local_config(path: str | Path | None = None) -> LocalConfig:
    config_path = ensure_local_config_exists(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    config = LocalConfig(**data)
    ensure_parent_dirs(config)
    return config


def save_local_config(config: LocalConfig, path: str | Path | None = None):
    config_path = _resolve_path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    ensure_parent_dirs(config)