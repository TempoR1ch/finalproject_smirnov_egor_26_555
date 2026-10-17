"""Настройки и пути к данным приложения."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"

USERS_FILE = DATA_DIR / "users.json"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"
RATES_FILE = DATA_DIR / "rates.json"
EXCHANGE_RATES_FILE = DATA_DIR / "exchange_rates.json"


class SettingsLoader:
    """Загружает настройки приложения из переменных окружения."""

    DEFAULT_RATES_TTL_SECONDS = 300

    @staticmethod
    def get_rates_ttl() -> int:
        """Возвращает срок актуальности курса в секундах."""
        raw_value = os.getenv(
            "RATES_TTL_SECONDS",
            str(SettingsLoader.DEFAULT_RATES_TTL_SECONDS),
        )

        try:
            ttl = int(raw_value)
        except ValueError as error:
            raise ValueError(
                "RATES_TTL_SECONDS должен быть целым числом."
            ) from error

        if ttl <= 0:
            raise ValueError("RATES_TTL_SECONDS должен быть больше нуля.")

        return ttl
