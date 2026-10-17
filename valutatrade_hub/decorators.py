"""Декораторы для логирования операций приложения."""

import logging
from functools import wraps
from time import perf_counter

logger = logging.getLogger(__name__)


def log_action(func):
    """Логирует запуск операции, её результат и ошибки."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info("Начало операции: %s", func.__name__)

        try:
            result = func(*args, **kwargs)
        except Exception:
            logger.exception("Ошибка операции: %s", func.__name__)
            raise

        logger.info("Операция завершена: %s", func.__name__)
        return result

    return wrapper


def measure_time(func):
    """Измеряет время выполнения функции."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = perf_counter()

        try:
            return func(*args, **kwargs)
        finally:
            elapsed = perf_counter() - start
            logger.info(
                "Время выполнения %s: %.4f сек.",
                func.__name__,
                elapsed,
            )

    return wrapper