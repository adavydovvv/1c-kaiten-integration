from datetime import datetime, timezone

from clients.onec_client import OneCClient
from clients.kaiten_client import KaitenClient
from config.settings import load_settings
from state.sync_state import SyncState


def run_smoke_test():
    settings = load_settings()

    onec = OneCClient(
        base_url=settings.onec_base_url,
        username=settings.onec_username,
        password=settings.onec_password,
    )

    kaiten = KaitenClient(
        base_url=settings.kaiten_base_url,
        token=settings.kaiten_token,
    )

    state = SyncState(settings.state_file)

    tasks = onec.get_changed_tasks()
    print(f"1C OK, получено задач: {len(tasks)}")

    # Пока просто проверяем, что Kaiten отвечает
    cards = kaiten.get_cards()
    if isinstance(cards, list):
        print(f"Kaiten OK, получено карточек: {len(cards)}")
    else:
        print("Kaiten OK, ответ получен")

    state.save_last_sync(datetime.now(timezone.utc).isoformat())
    print("Smoke test завершён")
