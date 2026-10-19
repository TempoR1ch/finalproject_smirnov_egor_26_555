"""Конфигурация сервиса получения валютных курсов."""

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
