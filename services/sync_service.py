import json
from datetime import datetime, timezone

from clients.onec_client import OneCClient
from clients.kaiten_client import KaitenClient
from config.settings import load_settings
from state.sync_state import SyncState
import re



def normalize_text(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.startswith("<Объект не найден>"):
        return ""
    return text


def normalize_name(value) -> str:
    text = normalize_text(value).lower()

    replacements = {
        "№": "n",
        "no.": "n",
        "no": "n",
        "-": "",
        "_": "",
        " ": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[^a-zа-я0-9n]+", "", text)
    return text

def build_title(task: dict) -> str:
    title = normalize_text(task.get("title"))
    if title:
        return title

    description = normalize_text(task.get("description"))
    if description:
        return description[:120]

    uuid_value = normalize_text(task.get("uuid"))
    return f"Задача {uuid_value[:8]}" if uuid_value else "Задача без названия"


def build_description(task: dict) -> str:
    uuid_value = normalize_text(task.get("uuid"))
    description = normalize_text(task.get("description"))

    service = normalize_text(task.get("service")) or "Не указан"
    assignee = normalize_text(task.get("assignee")) or "Не указан"
    status = normalize_text(task.get("status")) or "Не указан"
    priority = normalize_text(task.get("priority")) or "Не указан"
    planned_hours = task.get("planned_hours", 0)
    actual_hours = task.get("actual_hours", 0)
    start_date = normalize_text(task.get("start_date"))
    end_date = normalize_text(task.get("end_date"))

    parts = []

    if description:
        parts.append(description)
        parts.append("")

    parts.extend([
        f"1C UUID: {uuid_value}",
        f"Сервис: {service}",
        f"Исполнитель: {assignee}",
        f"Статус 1С: {status}",
        f"Приоритет: {priority}",
        f"План, ч: {planned_hours}",
        f"Факт, ч: {actual_hours}",
        f"Начало: {start_date}",
        f"Окончание: {end_date}",
    ])

    return "\n".join(parts).strip()


def extract_uuid_from_description(description: str) -> str:
    text = normalize_text(description)
    marker = "1C UUID:"

    if marker not in text:
        return ""

    for line in text.splitlines():
        line = line.strip()
        if line.startswith(marker):
            return line.replace(marker, "", 1).strip()

    return ""


def get_active_service_settings(onec: OneCClient) -> list:
    items = onec.get_service_settings() or []

    result = []
    for item in items:
        board_id = int(item.get("board_id", 0) or 0)
        if item.get("active") and board_id > 0:
            result.append(item)

    return result


def get_active_board_ids(service_settings: list) -> set[int]:
    result = set()

    for item in service_settings:
        board_id = int(item.get("board_id", 0) or 0)
        if board_id > 0:
            result.add(board_id)

    return result


def find_service_setting_for_task(task: dict, service_settings: list) -> dict | None:
    task_service_ref = normalize_text(task.get("service_ref"))
    task_service_name = normalize_name(task.get("service"))

    if task_service_ref:
        for item in service_settings:
            if normalize_text(item.get("service_ref")) == task_service_ref:
                return item

    if task_service_name:
        for item in service_settings:
            if normalize_name(item.get("service_name")) == task_service_name:
                return item

    return None


def resolve_column_id(task: dict, service_setting: dict) -> int:
    status = normalize_name(task.get("status"))
    columns = service_setting.get("columns") or {}

    queue_id = int(columns.get("queue", 0) or 0)
    in_progress_id = int(columns.get("in_progress", 0) or 0)
    review_id = int(columns.get("review", 0) or 0)
    done_id = int(columns.get("done", 0) or 0)
    canceled_id = int(columns.get("canceled", 0) or 0)

    if status in {"в работе", "вработе"} and in_progress_id:
        return in_progress_id

    if status in {"на проверке", "напроверке"} and review_id:
        return review_id

    if status in {"завершена", "готово"} and done_id:
        return done_id

    if status in {"отменена", "отменено"} and canceled_id:
        return canceled_id

    if queue_id:
        return queue_id

    for value in (in_progress_id, review_id, done_id, canceled_id):
        if value:
            return value

    raise ValueError("Не удалось определить column_id для сервиса")


def build_kaiten_payload(task: dict, service_setting: dict) -> dict:
    board_id = int(service_setting.get("board_id", 0) or 0)
    lane_id = int(service_setting.get("lane_id", 0) or 0)

    if board_id <= 0:
        raise ValueError("Для сервиса не настроен board_id")

    payload = {
        "title": build_title(task),
        "description": build_description(task),
        "board_id": board_id,
        "column_id": resolve_column_id(task, service_setting),
        "lane_id": lane_id if lane_id > 0 else None,
    }

    if payload["lane_id"] is None:
        payload.pop("lane_id")

    return payload


def build_existing_card_map(cards: list, allowed_board_ids: set[int]) -> dict:
    result = {}

    for card in cards:
        try:
            board_id = int(card.get("board_id", 0) or 0)
        except (TypeError, ValueError):
            continue

        if allowed_board_ids and board_id not in allowed_board_ids:
            continue

        uuid_value = extract_uuid_from_description(card.get("description", ""))
        if not uuid_value:
            continue

        result[uuid_value] = card

    return result


def export_1c_to_kaiten(onec: OneCClient, kaiten: KaitenClient, settings, service_settings: list):
    tasks = onec.get_changed_tasks() or []
    print(f"Получено задач из 1С: {len(tasks)}")

    allowed_board_ids = get_active_board_ids(service_settings)
    all_cards = kaiten.get_cards() or []
    existing_cards_by_uuid = build_existing_card_map(all_cards, allowed_board_ids)

    seen_uuids = set()
    created_or_updated = 0
    errors = 0

    for task in tasks:
        uuid_value = normalize_text(task.get("uuid"))
        if not uuid_value:
            print("Пропущена строка без UUID")
            continue

        if uuid_value in seen_uuids:
            print(f"Пропущен дубликат UUID в одной выгрузке: {uuid_value}")
            continue

        seen_uuids.add(uuid_value)

        try:
            service_setting = find_service_setting_for_task(task, service_settings)
            if not service_setting:
                errors += 1
                print(f"Не найдены настройки Kaiten для сервиса '{normalize_text(task.get('service'))}'")
                continue

            payload = build_kaiten_payload(task, service_setting)
            kaiten_id = normalize_text(task.get("kaiten_id"))
            existing_card = existing_cards_by_uuid.get(uuid_value)

            print(
                f"Экспорт UUID={uuid_value}, "
                f"service={normalize_text(task.get('service'))}, "
                f"status={normalize_text(task.get('status'))}, "
                f"board_id={payload['board_id']}, "
                f"column_id={payload['column_id']}"
            )

            if kaiten_id:
                card = kaiten.update_card(int(kaiten_id), payload)
                final_kaiten_id = str(card["id"])
            elif existing_card:
                final_kaiten_id = str(existing_card["id"])
                card = kaiten.update_card(int(final_kaiten_id), payload)
            else:
                card = kaiten.create_card(payload)
                final_kaiten_id = str(card["id"])

            card_url = f"{settings.kaiten_site_url}/card/{final_kaiten_id}"
            external_status = (
                normalize_text((card.get("column") or {}).get("title"))
                or normalize_text(task.get("status"))
            )

            onec.update_task_sync_fields(
                uuid=uuid_value,
                kaiten_id=final_kaiten_id,
                external_status=external_status,
                kaiten_card_url=card_url,
            )

            created_or_updated += 1
            print(f"Синхронизирована строка {uuid_value} -> карточка {final_kaiten_id}")

        except Exception as exc:
            errors += 1
            print(f"Ошибка экспорта строки {uuid_value}: {exc}")

    print(f"Экспорт завершён: успешно={created_or_updated}, ошибок={errors}")


def import_kaiten_to_1c(onec: OneCClient, kaiten: KaitenClient, settings, service_settings: list):
    cards = kaiten.get_cards() or []
    allowed_board_ids = get_active_board_ids(service_settings)

    processed = 0
    ignored = 0
    errors = 0

    for card in cards:
        try:
            board_id = int(card.get("board_id", 0) or 0)
            if allowed_board_ids and board_id not in allowed_board_ids:
                continue

            kaiten_id = str(card.get("id", "")).strip()
            if not kaiten_id:
                continue

            column = card.get("column") or {}
            external_status = normalize_text(column.get("title")) or str(card.get("column_id", ""))
            card_url = f"{settings.kaiten_site_url}/card/{kaiten_id}"
            uuid_value = extract_uuid_from_description(card.get("description", ""))
            title = normalize_text(card.get("title"))

            result = onec.apply_from_kaiten(
                kaiten_id=kaiten_id,
                external_status=external_status,
                kaiten_card_url=card_url,
                uuid=uuid_value,
                title=title,
            )

            if isinstance(result, dict) and result.get("ignored"):
                ignored += 1
                print(f"Kaiten карточка {kaiten_id} не связана с 1С, пропущена")
                continue

            processed += 1
            print(f"Обновлена из Kaiten карточка {kaiten_id}: {title}")

        except Exception as exc:
            errors += 1
            print(f"Ошибка импорта карточки {card.get('id')}: {exc}")

    print(f"Импорт завершён: обновлено={processed}, пропущено={ignored}, ошибок={errors}")


def find_column_id(columns: list, target_title: str) -> int:
    target = normalize_name(target_title)
    for column in columns or []:
        if normalize_name(column.get("title")) == target:
            return int(column.get("id", 0) or 0)
    return 0


def find_board_for_service(metadata: dict, service_name: str) -> dict | None:
    target = normalize_name(service_name)

    exact_space_matches = []
    exact_board_matches = []
    partial_matches = []

    for board in metadata.get("boards", []):
        space_title_raw = normalize_text(board.get("space_title"))
        board_title_raw = normalize_text(board.get("board_title"))

        space_title = normalize_name(space_title_raw)
        board_title = normalize_name(board_title_raw)

        if space_title == target:
            exact_space_matches.append(board)
            continue

        if board_title == target:
            exact_board_matches.append(board)
            continue

        if target and (target in space_title or target in board_title):
            partial_matches.append(board)

    for candidates in (exact_space_matches, exact_board_matches, partial_matches):
        if candidates:
            for board in candidates:
                if board.get("columns"):
                    return board
            return candidates[0]

    return None

def build_property_map(properties: list) -> dict:
    result = {
        "priority": 0,
        "plan_hours": 0,
        "fact_hours": 0,
        "service": 0,
        "start_date": 0,
        "end_date": 0,
    }

    for prop in properties or []:
        title = normalize_name(prop.get("title"))
        prop_id = int(prop.get("id", 0) or 0)

        if not prop_id:
            continue

        if title in {"приоритет", "priority"}:
            result["priority"] = prop_id
        elif title in {"план, ч", "план", "plan hours", "planned hours"}:
            result["plan_hours"] = prop_id
        elif title in {"факт, ч", "факт", "actual hours", "fact hours"}:
            result["fact_hours"] = prop_id
        elif title in {"it-сервис", "ит-сервис", "сервис", "service"}:
            result["service"] = prop_id
        elif title in {"дата начала", "start date", "planned start"}:
            result["start_date"] = prop_id
        elif title in {"дата окончания", "срок", "end date", "due date"}:
            result["end_date"] = prop_id

    return result


def merge_property_maps(current_map: dict | None, detected_map: dict) -> dict:
    current_map = current_map or {}

    return {
        "priority": int(current_map.get("priority", 0) or detected_map.get("priority", 0) or 0),
        "plan_hours": int(current_map.get("plan_hours", 0) or detected_map.get("plan_hours", 0) or 0),
        "fact_hours": int(current_map.get("fact_hours", 0) or detected_map.get("fact_hours", 0) or 0),
        "service": int(current_map.get("service", 0) or detected_map.get("service", 0) or 0),
        "start_date": int(current_map.get("start_date", 0) or detected_map.get("start_date", 0) or 0),
        "end_date": int(current_map.get("end_date", 0) or detected_map.get("end_date", 0) or 0),
    }


def auto_fill_service_settings():
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

    service_settings = onec.get_service_settings() or []
    print("service_settings:", service_settings)
    print("service_settings count:", len(service_settings))

    metadata = kaiten.get_metadata_catalog()
    detected_property_map = build_property_map(metadata.get("properties", []))

    updated_settings = []

    for item in service_settings:
        service_name = normalize_text(item.get("service_name"))
        service_ref = normalize_text(item.get("service_ref"))

        if not service_ref or not service_name:
            continue

        matched_board = find_board_for_service(metadata, service_name)

        if not matched_board:
            print(f"Не найдена доска Kaiten для сервиса: {service_name}")
            updated_settings.append(item)
            continue

        columns = matched_board.get("columns", []) or []
        current_properties = item.get("properties") or {}

        item["active"] = True
        item["board_id"] = int(matched_board.get("board_id", 0) or 0)
        item["lane_id"] = 0
        item["columns"] = {
            "queue": find_column_id(columns, "Очередь"),
            "in_progress": find_column_id(columns, "В работе"),
            "review": find_column_id(columns, "На проверке"),
            "done": find_column_id(columns, "Готово"),
            "canceled": find_column_id(columns, "Отменено"),
        }
        item["properties"] = merge_property_maps(current_properties, detected_property_map)

        updated_settings.append(item)

        print(
            f"Сервис '{service_name}' -> доска "
            f"{matched_board.get('space_title')} / {matched_board.get('board_title')} "
            f"({matched_board.get('board_id')})"
        )

    result = onec.update_service_settings(updated_settings)
    print("Настройки сервисов обновлены:", result)


def dump_kaiten_metadata():
    settings = load_settings()

    kaiten = KaitenClient(
        base_url=settings.kaiten_base_url,
        token=settings.kaiten_token,
    )

    metadata = kaiten.get_metadata_catalog()

    with open("kaiten_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(
        f"Сохранено метаданных: "
        f"досок={len(metadata.get('boards', []))}, "
        f"свойств={len(metadata.get('properties', []))}"
    )


def run_full_sync():
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
    service_settings = get_active_service_settings(onec)

    export_1c_to_kaiten(onec, kaiten, settings, service_settings)
    import_kaiten_to_1c(onec, kaiten, settings, service_settings)

    state.save_last_sync(datetime.now(timezone.utc).isoformat())
    print("Полная синхронизация завершена")
