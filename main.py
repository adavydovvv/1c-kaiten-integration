from services.sync_service import auto_fill_service_settings, run_full_sync


def main():
    print("=== Шаг 1. Сборка и обновление настроек сервисов ===")
    auto_fill_service_settings()

    print("=== Шаг 2. Полная синхронизация 1С <-> Kaiten ===")
    run_full_sync()


if __name__ == "__main__":
    main()
