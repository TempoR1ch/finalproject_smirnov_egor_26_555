"""Настройка логирования приложения."""

import logging
from pathlib import Path

LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_FILE = LOGS_DIR / "valutatrade_hub.log"


def setup_logging() -> None:
    """Настраивает запись логов в файл и вывод ошибок в консоль."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
