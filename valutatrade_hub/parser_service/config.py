"""Конфигурация сервиса получения валютных курсов."""

from dataclasses import dataclass, field

from valutatrade_hub.core.currencies import CURRENCIES, CryptoCurrency, FiatCurrency
from valutatrade_hub.infra.settings import (
    EXCHANGE_RATES_FILE,
    RATES_FILE,
)

COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"
EXCHANGE_RATE_API_URL = "https://v6.exchangerate-api.com/v6"

API_TIMEOUT = 10
DEFAULT_BASE_CURRENCY = "USD"

FIAT_CURRENCIES = tuple(
    code for code, currency in CURRENCIES.items() if isinstance(currency, FiatCurrency)
)

CRYPTO_CURRENCIES = tuple(
    code
    for code, currency in CURRENCIES.items()
    if isinstance(currency, CryptoCurrency)
)

CRYPTO_ID_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
}

RATES_PATH = RATES_FILE
EXCHANGE_RATES_PATH = EXCHANGE_RATES_FILE


@dataclass(frozen=True)
class ParserConfig:
    """Единая конфигурация парсера на основе реестра валют приложения."""

    fiat_currencies: tuple[str, ...] = FIAT_CURRENCIES
    crypto_currencies: tuple[str, ...] = CRYPTO_CURRENCIES
    crypto_id_map: dict[str, str] = field(default_factory=lambda: CRYPTO_ID_MAP.copy())
    api_timeout: int = API_TIMEOUT
    base_currency: str = DEFAULT_BASE_CURRENCY

    def __post_init__(self) -> None:
        expected_fiat = {
            code
            for code, currency in CURRENCIES.items()
            if isinstance(currency, FiatCurrency)
        }
        if set(self.fiat_currencies) != expected_fiat:
            raise ValueError("Список фиатных валют должен совпадать с реестром валют.")

        expected_crypto = {
            code
            for code, currency in CURRENCIES.items()
            if isinstance(currency, CryptoCurrency)
        }
        if set(self.crypto_currencies) != expected_crypto:
            raise ValueError("Список криптовалют должен совпадать с реестром валют.")

        if set(self.crypto_id_map) != set(self.crypto_currencies):
            raise ValueError("Для каждой криптовалюты должен быть задан API ID.")

        if any(
            not isinstance(api_id, str) or not api_id.strip()
            for api_id in self.crypto_id_map.values()
        ):
            raise ValueError("API ID криптовалют не должны быть пустыми.")

        if self.api_timeout <= 0:
            raise ValueError("Таймаут API должен быть положительным.")

        if self.base_currency not in CURRENCIES:
            raise ValueError(
                f"Базовая валюта {self.base_currency} отсутствует в реестре."
            )
