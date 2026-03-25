from config.config_loader import LocalConfig, save_local_config


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def main():
    print("=== Настройка локального Python-сервиса интеграции 1С <-> Kaiten ===")

    config = LocalConfig(
        onec_base_url=ask("URL HTTP-сервиса 1С", "http://localhost/ERP/hs/kaiten"),
        onec_username=ask("Пользователь 1С", "Admin"),
        onec_password=ask("Пароль 1С", ""),
        py_service_host=ask("Хост Python-сервиса", "127.0.0.1"),
        py_service_port=int(ask("Порт Python-сервиса", "8088")),
        state_file=ask("Файл состояния", "state/last_sync.json"),
        log_level=ask("Уровень логирования", "INFO"),
    )

    save_local_config(config)
    print("Конфигурация сохранена в config/local_config.json")


if __name__ == "__main__":
    main()
