"""Пользовательские исключения приложения ValutaTrade Hub."""


class InsufficientFundsError(Exception):
    """Возникает при недостатке средств в кошельке."""

    def __init__(self, available: float, required: float, currency_code: str) -> None:
        self.available = available
        self.required = required
        self.currency_code = currency_code
        super().__init__(
            f"Недостаточно средств: доступно {available} {currency_code}, "
            f"требуется {required} {currency_code}"
        )


class CurrencyNotFoundError(Exception):
    """Возникает, если валюта отсутствует в реестре."""

    def __init__(self, currency_code: str) -> None:
        self.currency_code = currency_code
        super().__init__(f"Неизвестная валюта '{currency_code}'")


class ApiRequestError(Exception):
    """Возникает при ошибке обращения к внешнему API."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
