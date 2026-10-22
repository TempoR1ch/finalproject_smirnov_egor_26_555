"""Настройка логирования приложения."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIRECTORY = Path("logs")
LOG_FILE = LOG_DIRECTORY / "valutatrade.log"
PARSER_LOG_FILE = LOG_DIRECTORY / "parser.log"

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

MAX_LOG_SIZE = 1_000_000
BACKUP_COUNT = 3


def _add_rotating_handler(
    logger: logging.Logger,
    file_path: Path,
    level: int,
) -> None:
    """Добавляет файловый обработчик, если он ещё не настроен."""
    resolved_path = str(file_path.resolve())

    for handler in logger.handlers:
        if (
            isinstance(handler, RotatingFileHandler)
            and handler.baseFilename == resolved_path
        ):
            handler.setLevel(level)
            return

    handler = RotatingFileHandler(
        file_path,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            fmt=LOG_FORMAT,
            datefmt=DATE_FORMAT,
        )
    )
    logger.addHandler(handler)


def setup_logging() -> None:
    """Настраивает общие логи и подробное логирование парсера."""
    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    _add_rotating_handler(
        root_logger,
        LOG_FILE,
        logging.INFO,
    )

    if not any(
        getattr(handler, "_valutatrade_console", False)
        for handler in root_logger.handlers
    ):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        console_handler.setFormatter(
            logging.Formatter(
                fmt=LOG_FORMAT,
                datefmt=DATE_FORMAT,
            )
        )
        console_handler._valutatrade_console = True
        root_logger.addHandler(console_handler)

    parser_logger = logging.getLogger("valutatrade_hub.parser_service")
    parser_logger.setLevel(logging.DEBUG)
    parser_logger.propagate = False

    _add_rotating_handler(
        parser_logger,
        PARSER_LOG_FILE,
        logging.DEBUG,
    )
