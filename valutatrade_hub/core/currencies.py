"""Модели валют и реестр поддерживаемых валют."""

from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Базовый класс валюты."""

    def __init__(self, name: str, code: str) -> None:
        if not name.strip():
            raise ValueError("Название валюты не может быть пустым.")

        normalized_code = code.strip().upper()
        if not normalized_code.isalpha() or not 2 <= len(normalized_code) <= 5:
            raise ValueError(
                "Код валюты должен содержать от 2 до 5 букв."
            )

        self.name = name.strip()
        self.code = normalized_code

    @abstractmethod
    def get_display_info(self) -> str:
        """Возвращает информацию о валюте для отображения."""


class FiatCurrency(Currency):
    """Модель фиатной валюты."""

    def __init__(self, name: str, code: str, issuing_country: str) -> None:
        super().__init__(name, code)
        if not issuing_country.strip():
            raise ValueError("Страна выпуска не может быть пустой.")
        self.issuing_country = issuing_country.strip()

    def get_display_info(self) -> str:
        """Возвращает информацию о фиатной валюте."""
        return (
            f"[FIAT] {self.code} — {self.name} "
            f"(Страна выпуска: {self.issuing_country})"
        )


class CryptoCurrency(Currency):
    """Модель криптовалюты."""

    def __init__(
        self,
        name: str,
        code: str,
        algorithm: str,
        market_cap: float | None = None,
    ) -> None:
        super().__init__(name, code)

        if not algorithm.strip():
            raise ValueError("Алгоритм криптовалюты не может быть пустым.")
        if market_cap is not None and market_cap < 0:
            raise ValueError("Капитализация не может быть отрицательной.")

        self.algorithm = algorithm.strip()
        self.market_cap = market_cap

    def get_display_info(self) -> str:
        """Возвращает информацию о криптовалюте."""
        info = f"[CRYPTO] {self.code} — {self.name} (Алгоритм: {self.algorithm}"
        if self.market_cap is not None:
            info += f", Капитализация: {self.market_cap:.2e}"
        return f"{info})"


CURRENCIES: dict[str, Currency] = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "European Union"),
    "GBP": FiatCurrency("British Pound", "GBP", "United Kingdom"),
    "JPY": FiatCurrency("Japanese Yen", "JPY", "Japan"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256"),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Ethash"),
    "SOL": CryptoCurrency("Solana", "SOL", "Proof of History"),
}


def get_currency(code: str) -> Currency:
    """Возвращает валюту по коду или вызывает исключение, если её нет."""
    normalized_code = code.strip().upper()
    try:
        return CURRENCIES[normalized_code]
    except KeyError:
        raise CurrencyNotFoundError(normalized_code) from None
