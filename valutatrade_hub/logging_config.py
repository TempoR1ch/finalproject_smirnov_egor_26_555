"""Настройка логирования приложения."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIRECTORY = Path("logs")
LOG_FILE = LOG_DIRECTORY / "valutatrade.log"

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

MAX_LOG_SIZE = 1_000_000
BACKUP_COUNT = 3


def setup_logging() -> None:
    """Настраивает запись логов в файл и вывод ошибок в консоль."""
    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=DATE_FORMAT,
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Не добавляем обработчики повторно при повторном вызове.
    if root_logger.handlers:
        return

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
