from config.config_loader import LocalConfig, load_local_config, save_local_config
from services.sync_service import auto_fill_project_settings

def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default

def main():
    print("=== Настройка локального Python-сервиса интеграции 1С <-> Kaiten ===")

    # Пытаемся загрузить существующий конфиг, чтобы использовать его как дефолт
    try:
        current_config = load_local_config()
    except Exception:
        # Если конфига нет или он битый, создаем пустой/стандартный
        current_config = LocalConfig(
            onec_base_url="http://localhost/ERP/hs/kaiten",
            onec_username="Admin",
            onec_password="",
        )

    config = LocalConfig(
        onec_base_url=ask("URL HTTP-сервиса 1С", current_config.onec_base_url),
        onec_username=ask("Пользователь 1С", current_config.onec_username),
        onec_password=ask("Пароль 1С", current_config.onec_password),
        py_service_host=ask("Хост Python-сервиса", current_config.py_service_host),
        py_service_port=int(ask("Порт Python-сервиса", str(current_config.py_service_port))),
        state_file=ask("Файл состояния", current_config.state_file),
        log_level=ask("Уровень логирования", current_config.log_level),
    )

    save_local_config(config)
    print("\nКонфигурация успешно сохранена в config/local_config.json\n")

    do_fill = ask("Выполнить автоматическое сопоставление проектов 1С и досок Kaiten?", "y")
    if do_fill.lower() in ('y', 'yes', 'да', 'д'):
        print("\nЗапускаем скачивание метаданных из Kaiten...")
        try:
            auto_fill_project_settings()
            print("Готово! Проверь регистр сведений в 1С.")
        except Exception as e:
            print(f"\nПроизошла ошибка при попытке сопоставления: {e}")

if __name__ == "__main__":
    main()