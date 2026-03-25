import json
import re
from datetime import datetime, timezone

from clients.onec_client import OneCClient
from clients.kaiten_client import KaitenClient
from config.settings import load_settings
from state.sync_state import SyncState


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


def to_int(value, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def to_number(value, default=0):
    try:
        if value is None or value == "":
            return default
        return value
    except (TypeError, ValueError):
        return default


def minutes_to_hours(value) -> float:
    minutes = to_int(value, 0)
    return round(minutes / 60, 2)


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
        board_id = to_int(item.get("board_id", 0))
        if item.get("active") and board_id > 0:
            result.append(item)

    return result


def get_active_board_ids(service_settings: list) -> set[int]:
    result = set()

    for item in service_settings:
        board_id = to_int(item.get("board_id", 0))
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


def find_column_id(columns: list, target_title: str) -> int:
    target = normalize_name(target_title)
    for column in columns or []:
        if normalize_name(column.get("title")) == target:
            return to_int(column.get("id", 0))
    return 0


def find_column_id_by_titles(columns: list, titles: list[str]) -> int:
    for title in titles:
        column_id = find_column_id(columns, title)
        if column_id > 0:
            return column_id
    return 0


def find_lane_id(lanes: list, target_title: str) -> int:
    target = normalize_name(target_title)
    for lane in lanes or []:
        if normalize_name(lane.get("title")) == target:
            return to_int(lane.get("id", 0))
    return 0


def build_lane_map(lanes: list) -> dict:
    return {
        "low": find_lane_id(lanes, "Низкий"),
        "medium": find_lane_id(lanes, "Средний"),
        "high": find_lane_id(lanes, "Высокий"),
        "critical": find_lane_id(lanes, "Критический"),
    }


def enrich_service_settings_with_metadata(service_settings: list, metadata: dict):
    boards_by_id = {}

    for board in metadata.get("boards", []):
        board_id = to_int(board.get("board_id", 0))
        if board_id > 0:
            boards_by_id[board_id] = board

    for item in service_settings:
        board_id = to_int(item.get("board_id", 0))
        matched_board = boards_by_id.get(board_id)

        if not matched_board:
            item["lanes"] = {}
            continue

        lanes = matched_board.get("lanes") or []
        item["lanes"] = build_lane_map(lanes)


def resolve_column_id(task: dict, service_setting: dict) -> int:
    status_raw = normalize_text(task.get("status"))
    status = normalize_name(status_raw)
    columns = service_setting.get("columns") or {}

    queue_id = to_int(columns.get("queue", 0))
    in_progress_id = to_int(columns.get("in_progress", 0))
    review_id = to_int(columns.get("review", 0))
    done_id = to_int(columns.get("done", 0))
    canceled_id = to_int(columns.get("canceled", 0))

    if status in {"новая", "новое", "квыполнению", "создана", "открыта"} and queue_id:
        return queue_id

    if status in {"вработе", "выполняется", "исполняется"} and in_progress_id:
        return in_progress_id

    if status in {"напроверке", "проверка", "тестирование"} and review_id:
        return review_id

    if status in {"завершена", "завершено", "готово", "выполнена", "выполнено", "закрыта", "закрыто"} and done_id:
        return done_id

    if status in {"отменена", "отменено", "отклонена", "отклонено"} and canceled_id:
        return canceled_id

    print(f"Неизвестный статус 1С '{status_raw}', используем queue")
    if queue_id:
        return queue_id

    for value in (in_progress_id, review_id, done_id, canceled_id):
        if value:
            return value

    raise ValueError("Не удалось определить column_id для сервиса")


def resolve_lane_id(task: dict, service_setting: dict) -> int:
    priority_raw = normalize_text(task.get("priority"))
    priority = normalize_name(priority_raw)
    lanes = service_setting.get("lanes") or {}

    low_id = to_int(lanes.get("low", 0))
    medium_id = to_int(lanes.get("medium", 0))
    high_id = to_int(lanes.get("high", 0))
    critical_id = to_int(lanes.get("critical", 0))

    if priority in {"низкий", "low"} and low_id:
        return low_id

    if priority in {"средний", "medium"} and medium_id:
        return medium_id

    if priority in {"высокий", "high"} and high_id:
        return high_id

    if priority in {"критический", "critical"} and critical_id:
        return critical_id

    fallback_lane_id = to_int(service_setting.get("lane_id", 0))
    return fallback_lane_id if fallback_lane_id > 0 else 0


def build_kaiten_payload(task: dict, service_setting: dict) -> dict:
    board_id = to_int(service_setting.get("board_id", 0))

    if board_id <= 0:
        raise ValueError("Для сервиса не настроен board_id")

    payload = {
        "title": build_title(task),
        "description": build_description(task),
        "board_id": board_id,
        "column_id": resolve_column_id(task, service_setting),
        "planned_start": normalize_text(task.get("start_date")) or None,
        "planned_end": normalize_text(task.get("end_date")) or None,
        "estimate_workload": task.get("planned_hours", 0) or 0,
    }

    lane_id = resolve_lane_id(task, service_setting)
    if lane_id > 0:
        payload["lane_id"] = lane_id

    if payload["planned_start"] is None:
        payload.pop("planned_start")

    if payload["planned_end"] is None:
        payload.pop("planned_end")

    return payload


def is_card_archived(card: dict) -> bool:
    return bool(
        card.get("archived")
        or card.get("is_archived")
        or card.get("deleted")
        or card.get("is_deleted")
    )


def is_better_card(candidate: dict, current: dict) -> bool:
    candidate_archived = is_card_archived(candidate)
    current_archived = is_card_archived(current)

    if candidate_archived != current_archived:
        return not candidate_archived and current_archived

    candidate_id = to_int(candidate.get("id", 0))
    current_id = to_int(current.get("id", 0))

    return candidate_id > current_id


def build_existing_card_map(cards: list, allowed_board_ids: set[int]) -> dict:
    result = {}

    for card in cards:
        board_id = to_int(card.get("board_id", 0))
        if allowed_board_ids and board_id not in allowed_board_ids:
            continue

        uuid_value = extract_uuid_from_description(card.get("description", ""))
        if not uuid_value:
            continue

        current = result.get(uuid_value)
        if current is None or is_better_card(card, current):
            result[uuid_value] = card

    return result


def build_cards_for_import(cards: list, allowed_board_ids: set[int]) -> list:
    cards_with_uuid_map = build_existing_card_map(cards, allowed_board_ids)
    cards_to_process = []
    seen_ids = set()

    for preferred_card in cards_with_uuid_map.values():
        card_id = to_int(preferred_card.get("id", 0))
        if card_id > 0 and card_id not in seen_ids:
            cards_to_process.append(preferred_card)
            seen_ids.add(card_id)

    for card in cards:
        board_id = to_int(card.get("board_id", 0))
        if allowed_board_ids and board_id not in allowed_board_ids:
            continue

        uuid_value = extract_uuid_from_description(card.get("description", ""))
        if uuid_value:
            continue

        card_id = to_int(card.get("id", 0))
        if card_id <= 0 or card_id in seen_ids:
            continue

        cards_to_process.append(card)
        seen_ids.add(card_id)

    cards_to_process.sort(key=lambda item: to_int(item.get("id", 0)))
    return cards_to_process


def is_kaiten_missing_or_forbidden_error(exc: Exception) -> bool:
    text = str(exc)
    return "Kaiten API error: 403" in text or "Kaiten API error: 404" in text


def upsert_card_with_recreate(
    kaiten: KaitenClient,
    task: dict,
    payload: dict,
    existing_card: dict | None,
):
    uuid_value = normalize_text(task.get("uuid"))
    kaiten_id = normalize_text(task.get("kaiten_id"))

    existing_card_id = ""
    if existing_card:
        existing_card_id = normalize_text(existing_card.get("id"))

    if existing_card_id:
        if kaiten_id and kaiten_id != existing_card_id:
            print(
                f"Для UUID={uuid_value} в 1С хранится старый KaitenID={kaiten_id}, "
                f"используем актуальную карточку {existing_card_id}, найденную по UUID"
            )

        try:
            card = kaiten.update_card(to_int(existing_card_id), payload)
            return card, str(card["id"])
        except Exception as exc:
            if not is_kaiten_missing_or_forbidden_error(exc):
                raise
            print(
                f"Карточка {existing_card_id}, найденная по UUID={uuid_value}, недоступна, "
                f"попробуем fallback по KaitenID"
            )

    if kaiten_id and kaiten_id != existing_card_id:
        try:
            card = kaiten.update_card(to_int(kaiten_id), payload)
            return card, str(card["id"])
        except Exception as exc:
            if not is_kaiten_missing_or_forbidden_error(exc):
                raise
            print(f"Карточка Kaiten {kaiten_id} недоступна и по UUID ничего не подошло, создаем новую")

    card = kaiten.create_card(payload)
    return card, str(card["id"])


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
            existing_card = existing_cards_by_uuid.get(uuid_value)

            print(
                f"Экспорт UUID={uuid_value}, "
                f"service={normalize_text(task.get('service'))}, "
                f"status={normalize_text(task.get('status'))}, "
                f"priority={normalize_text(task.get('priority'))}, "
                f"board_id={payload['board_id']}, "
                f"column_id={payload['column_id']}, "
                f"lane_id={payload.get('lane_id')}, "
                f"planned_start={payload.get('planned_start')}, "
                f"planned_end={payload.get('planned_end')}, "
                f"estimate_workload={payload.get('estimate_workload')}"
            )

            card, final_kaiten_id = upsert_card_with_recreate(
                kaiten=kaiten,
                task=task,
                payload=payload,
                existing_card=existing_card,
            )

            existing_cards_by_uuid[uuid_value] = card

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
    cards_to_process = build_cards_for_import(cards, allowed_board_ids)

    processed = 0
    ignored = 0
    errors = 0

    total_with_uuid = 0
    for card in cards:
        board_id = to_int(card.get("board_id", 0))
        if allowed_board_ids and board_id not in allowed_board_ids:
            continue
        if extract_uuid_from_description(card.get("description", "")):
            total_with_uuid += 1

    unique_with_uuid = len(build_existing_card_map(cards, allowed_board_ids))
    skipped_duplicates = max(0, total_with_uuid - unique_with_uuid)
    if skipped_duplicates:
        print(f"Пропущено дублей карточек Kaiten по UUID: {skipped_duplicates}")

    for card in cards_to_process:
        try:
            board_id = to_int(card.get("board_id", 0))
            if allowed_board_ids and board_id not in allowed_board_ids:
                continue

            kaiten_id = normalize_text(card.get("id"))
            if not kaiten_id:
                continue

            column = card.get("column") or {}
            external_status = normalize_text(column.get("title")) or str(card.get("column_id", ""))
            card_url = f"{settings.kaiten_site_url}/card/{kaiten_id}"
            uuid_value = extract_uuid_from_description(card.get("description", ""))
            title = normalize_text(card.get("title"))
            actual_hours = minutes_to_hours(card.get("time_spent_sum", 0))

            result = onec.apply_from_kaiten(
                kaiten_id=kaiten_id,
                external_status=external_status,
                kaiten_card_url=card_url,
                uuid=uuid_value,
                title=title,
                actual_hours=actual_hours,
            )

            if isinstance(result, dict) and result.get("ignored"):
                ignored += 1
                print(f"Kaiten карточка {kaiten_id} не связана с 1С, пропущена")
                continue

            processed += 1
            print(f"Обновлена из Kaiten карточка {kaiten_id}: {title}, факт={actual_hours} ч")

        except Exception as exc:
            errors += 1
            print(f"Ошибка импорта карточки {card.get('id')}: {exc}")

    print(f"Импорт завершён: обновлено={processed}, пропущено={ignored}, ошибок={errors}")


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
        prop_id = to_int(prop.get("id", 0))

        if not prop_id:
            continue

        if title in {"приоритет", "priority"}:
            result["priority"] = prop_id
        elif title in {"план,ч", "план", "planhours", "plannedhours"}:
            result["plan_hours"] = prop_id
        elif title in {"факт,ч", "факт", "actualhours", "facthours"}:
            result["fact_hours"] = prop_id
        elif title in {"itсервис", "итсервис", "сервис", "service"}:
            result["service"] = prop_id
        elif title in {"датаначала", "startdate", "plannedstart"}:
            result["start_date"] = prop_id
        elif title in {"датаокончания", "срок", "enddate", "duedate"}:
            result["end_date"] = prop_id

    return result


def merge_property_maps(current_map: dict | None, detected_map: dict) -> dict:
    current_map = current_map or {}

    return {
        "priority": to_int(current_map.get("priority", 0) or detected_map.get("priority", 0) or 0),
        "plan_hours": to_int(current_map.get("plan_hours", 0) or detected_map.get("plan_hours", 0) or 0),
        "fact_hours": to_int(current_map.get("fact_hours", 0) or detected_map.get("fact_hours", 0) or 0),
        "service": to_int(current_map.get("service", 0) or detected_map.get("service", 0) or 0),
        "start_date": to_int(current_map.get("start_date", 0) or detected_map.get("start_date", 0) or 0),
        "end_date": to_int(current_map.get("end_date", 0) or detected_map.get("end_date", 0) or 0),
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
        lanes = matched_board.get("lanes", []) or []
        current_properties = item.get("properties") or {}

        item["active"] = True
        item["board_id"] = to_int(matched_board.get("board_id", 0))
        item["lane_id"] = 0
        item["lanes"] = build_lane_map(lanes)
        item["columns"] = {
            "queue": find_column_id_by_titles(columns, ["Очередь", "Новая"]),
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
            f"({matched_board.get('board_id')}), "
            f"lanes={item.get('lanes')}, columns={item.get('columns')}"
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

    metadata = kaiten.get_metadata_catalog()
    enrich_service_settings_with_metadata(service_settings, metadata)

    for item in service_settings:
        print(
            f"Активный сервис: {item.get('service_name')} "
            f"board_id={item.get('board_id')} lanes={item.get('lanes')}"
        )

    export_1c_to_kaiten(onec, kaiten, settings, service_settings)
    import_kaiten_to_1c(onec, kaiten, settings, service_settings)

    state.save_last_sync(datetime.now(timezone.utc).isoformat())
    print("Полная синхронизация завершена")
