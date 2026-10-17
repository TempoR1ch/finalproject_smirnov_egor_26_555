"""Клиенты внешних API для получения валютных курсов."""

import os
from abc import ABC, abstractmethod
from typing import Any

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import (
    API_TIMEOUT,
    COINGECKO_API_URL,
    CRYPTO_CURRENCIES,
    CRYPTO_ID_MAP,
    DEFAULT_BASE_CURRENCY,
    EXCHANGE_RATE_API_URL,
    FIAT_CURRENCIES,
)


class BaseApiClient(ABC):
    """Базовый класс клиента API."""

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """Получает курсы в формате ПАРА: курс."""


class CoinGeckoClient(BaseApiClient):
    """Получает курсы криптовалют через CoinGecko."""

    def fetch_rates(self) -> dict[str, float]:
        """Возвращает курсы криптовалют относительно USD."""
        params = {
            "ids": ",".join(CRYPTO_ID_MAP.values()),
            "vs_currencies": DEFAULT_BASE_CURRENCY.lower(),
        }

        try:
            response = requests.get(
                COINGECKO_API_URL,
                params=params,
                timeout=API_TIMEOUT,
            )
            response.raise_for_status()
            data: Any = response.json()
        except requests.RequestException as error:
            raise ApiRequestError(str(error)) from error
        except ValueError as error:
            raise ApiRequestError("API вернул некорректный JSON.") from error

        if not isinstance(data, dict):
            raise ApiRequestError("API вернул данные неожиданного формата.")

        rates: dict[str, float] = {}

        for code in CRYPTO_CURRENCIES:
            coin_id = CRYPTO_ID_MAP[code]
            coin_data = data.get(coin_id)

            if not isinstance(coin_data, dict):
                continue

            rate = coin_data.get(DEFAULT_BASE_CURRENCY.lower())
            if isinstance(rate, (int, float)) and not isinstance(rate, bool):
                if rate > 0:
                    rates[f"{code}_{DEFAULT_BASE_CURRENCY}"] = float(rate)

        if not rates:
            raise ApiRequestError("API не вернул ни одного корректного курса.")

        return rates


class ExchangeRateApiClient(BaseApiClient):
    """Получает курсы фиатных валют через ExchangeRate-API."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("EXCHANGE_RATE_API_KEY")

    def fetch_rates(self) -> dict[str, float]:
        """Возвращает курсы фиатных валют относительно USD."""
        if not self.api_key:
            raise ApiRequestError(
                "Не задан API-ключ ExchangeRate-API."
            )

        url = f"{EXCHANGE_RATE_API_URL}/{self.api_key}/latest/{DEFAULT_BASE_CURRENCY}"

        try:
            response = requests.get(url, timeout=API_TIMEOUT)
            response.raise_for_status()
            data: Any = response.json()
        except requests.RequestException as error:
            raise ApiRequestError(str(error)) from error
        except ValueError as error:
            raise ApiRequestError("API вернул некорректный JSON.") from error

        if not isinstance(data, dict):
            raise ApiRequestError("API вернул данные неожиданного формата.")

        if data.get("result") != "success":
            reason = data.get("error-type", "неизвестная ошибка API")
            raise ApiRequestError(str(reason))

        conversion_rates = data.get("conversion_rates")
        if not isinstance(conversion_rates, dict):
            raise ApiRequestError("В ответе API отсутствуют курсы валют.")

        rates: dict[str, float] = {}

        for code in FIAT_CURRENCIES:
            if code == DEFAULT_BASE_CURRENCY:
                continue

            rate = conversion_rates.get(code)
            if isinstance(rate, (int, float)) and not isinstance(rate, bool):
                if rate > 0:
                    rates[f"{DEFAULT_BASE_CURRENCY}_{code}"] = float(rate)

        if not rates:
            raise ApiRequestError("API не вернул ни одного корректного курса.")

        return rates
