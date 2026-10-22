"""Модели пользователя, валютного кошелька и портфеля."""

import math
from datetime import datetime, timezone
from typing import Mapping

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import InsufficientFundsError
from valutatrade_hub.core.utils import create_password_hash, verify_password
from valutatrade_hub.infra.settings import DEFAULT_BASE_CURRENCY

EXCHANGE_RATES = {
    "EUR_USD": 1.08,
    "GBP_USD": 1.27,
    "JPY_USD": 0.0067,
    "RUB_USD": 0.011,
    "BTC_USD": 65000.0,
    "ETH_USD": 3000.0,
    "SOL_USD": 150.0,
}
FALLBACK_RATES = EXCHANGE_RATES


class User:
    """Представляет зарегистрированного пользователя."""

    def __init__(
        self,
        user_id: int,
        username: str,
        password: str,
        registration_date: datetime | None = None,
    ) -> None:
        self._user_id = user_id
        self._username = ""
        self._hashed_password = ""
        self._salt = ""
        self._registration_date = registration_date or datetime.now(timezone.utc)

        self.username = username
        self.set_password(password)

    @property
    def user_id(self) -> int:
        """Возвращает идентификатор пользователя."""
        return self._user_id

    @property
    def username(self) -> str:
        """Возвращает имя пользователя."""
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым.")
        self._username = value.strip()

    @property
    def registration_date(self) -> datetime:
        """Возвращает дату регистрации."""
        return self._registration_date

    def set_password(self, password: str) -> None:
        """Устанавливает новый пароль, сохраняя только соль и хэш."""
        self._salt, self._hashed_password = create_password_hash(password)

    def change_password(self, new_password: str) -> None:
        """Изменяет пароль пользователя."""
        self.set_password(new_password)

    def verify_password(self, password: str) -> bool:
        """Проверяет введённый пароль."""
        return verify_password(password, self._salt, self._hashed_password)

    def get_user_info(self) -> dict[str, int | str]:
        """Возвращает общедоступные данные пользователя без пароля."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def to_dict(self) -> dict[str, int | str]:
        """Подготавливает данные пользователя для сохранения в JSON."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "User":
        """Восстанавливает пользователя из сохранённых данных."""
        user = cls.__new__(cls)
        user._user_id = int(data["user_id"])
        user._username = str(data["username"])
        user._hashed_password = str(data["hashed_password"])
        user._salt = str(data["salt"])
        user._registration_date = datetime.fromisoformat(str(data["registration_date"]))
        return user


class Wallet:
    """Хранит баланс пользователя в одной валюте."""

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        self.currency_code = currency_code.strip().upper()
        get_currency(self.currency_code)
        self.balance = balance

    @property
    def balance(self) -> float:
        """Возвращает текущий баланс."""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Баланс должен быть числом.")
        if not math.isfinite(value) or value < 0:
            raise ValueError("Баланс должен быть конечным неотрицательным числом.")
        self._balance = float(value)

    def deposit(self, amount: float) -> None:
        """Пополняет кошелёк на положительную сумму."""
        self._validate_amount(amount)
        new_balance = self._balance + amount
        if not math.isfinite(new_balance):
            raise ValueError("Баланс после пополнения должен быть конечным числом.")
        self._balance = new_balance

    def withdraw(self, amount: float) -> None:
        """Списывает средства при достаточном балансе."""
        self._validate_amount(amount)
        if amount > self._balance:
            raise InsufficientFundsError(
                self._balance,
                amount,
                self.currency_code,
            )
        self._balance -= amount

    def get_balance_info(self) -> dict[str, str | float]:
        """Возвращает информацию о балансе."""
        return {
            "currency_code": self.currency_code,
            "balance": self._balance,
        }

    @staticmethod
    def _validate_amount(amount: float) -> None:
        """Проверяет, что сумма положительна и является конечным числом."""
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError("Сумма должна быть числом.")
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Сумма должна быть положительным конечным числом.")

    def to_dict(self) -> dict[str, str | float]:
        """Подготавливает кошелёк для сохранения в JSON."""
        return {
            "currency_code": self.currency_code,
            "balance": self._balance,
        }


class Portfolio:
    """Содержит валютные кошельки одного пользователя."""

    def __init__(
        self,
        user: User | int | None = None,
        user_id: int | None = None,
    ) -> None:
        # Поддерживаем передачу объекта User (предпочтительный вариант),
        # а также старый вызов Portfolio(user_id) для совместимости.
        if isinstance(user, User):
            self._user = user
            self._user_id = user.user_id
        elif isinstance(user, int) and not isinstance(user, bool):
            self._user = None
            self._user_id = user
        else:
            self._user = None
            self._user_id = int(user_id) if user_id is not None else 0
        self._wallets: dict[str, Wallet] = {}

    @property
    def user(self) -> User | None:
        """Возвращает объект пользователя, если он был передан модели."""
        return self._user

    @property
    def user_id(self) -> int:
        """Возвращает идентификатор владельца портфеля."""
        return self._user_id

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Возвращает копию словаря кошельков."""
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> Wallet:
        """Создаёт кошелёк для валюты, если его ещё нет."""
        normalized_code = currency_code.strip().upper()
        get_currency(normalized_code)

        if normalized_code in self._wallets:
            raise ValueError(f"Кошелёк {normalized_code} уже существует.")

        wallet = Wallet(normalized_code)
        self._wallets[normalized_code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet:
        """Возвращает кошелёк по коду валюты."""
        normalized_code = currency_code.strip().upper()
        get_currency(normalized_code)

        if normalized_code not in self._wallets:
            raise ValueError(f"Кошелёк {normalized_code} не найден.")

        return self._wallets[normalized_code]

    def get_total_value(
        self,
        base_currency: str = DEFAULT_BASE_CURRENCY,
        rates: Mapping[str, object] | None = None,
    ) -> float:
        """Рассчитывает стоимость портфеля через USD по переданным курсам."""
        if not isinstance(base_currency, str) or not base_currency.strip():
            raise ValueError("Базовая валюта должна быть указана.")

        base_currency = base_currency.strip().upper()
        get_currency(base_currency)
        rate_map: Mapping[str, object] = rates if rates is not None else EXCHANGE_RATES
        nested_pairs = rate_map.get("pairs")
        if isinstance(nested_pairs, dict):
            rate_map = nested_pairs

        def lookup_usd_rate(code: str) -> float:
            if code == DEFAULT_BASE_CURRENCY:
                return 1.0

            direct = rate_map.get(f"{code}_{DEFAULT_BASE_CURRENCY}")
            if isinstance(direct, dict):
                direct = direct.get("rate")
            if isinstance(direct, (int, float)) and not isinstance(direct, bool):
                if math.isfinite(direct) and direct > 0:
                    return float(direct)

            reverse = rate_map.get(f"{DEFAULT_BASE_CURRENCY}_{code}")
            if isinstance(reverse, dict):
                reverse = reverse.get("rate")
            if isinstance(reverse, (int, float)) and not isinstance(reverse, bool):
                if math.isfinite(reverse) and reverse > 0:
                    return 1.0 / float(reverse)

            raise ValueError(
                f"Курс {code}/USD отсутствует; невозможно рассчитать портфель."
            )

        if not self._wallets:
            return 0.0

        base_usd_rate = lookup_usd_rate(base_currency)
        total = 0.0
        for code, wallet in self._wallets.items():
            currency_usd_rate = lookup_usd_rate(code)
            total += wallet.balance * currency_usd_rate / base_usd_rate
            if not math.isfinite(total):
                raise ValueError(
                    "Общая стоимость портфеля должна быть конечным числом."
                )
        return total

    @staticmethod
    def _validate_rate(rate: object) -> float:
        """Проверяет корректность валютного курса."""
        if (
            isinstance(rate, bool)
            or not isinstance(rate, (int, float))
            or not math.isfinite(rate)
            or rate <= 0
        ):
            raise ValueError("Курс должен быть положительным конечным числом.")
        return float(rate)

    def to_dict(self) -> dict[str, object]:
        """Подготавливает портфель для сохранения в JSON."""
        return {
            "user_id": self._user_id,
            "wallets": {
                code: wallet.to_dict() for code, wallet in self._wallets.items()
            },
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, object],
        user: User | None = None,
    ) -> "Portfolio":
        """Восстанавливает портфель из данных и переданного объекта пользователя."""
        portfolio = cls(user=user, user_id=int(data["user_id"]))
        wallets_data = data["wallets"]

        if not isinstance(wallets_data, dict):
            raise ValueError("Некорректные данные кошельков.")

        for code, wallet_data in wallets_data.items():
            if not isinstance(wallet_data, dict):
                raise ValueError(f"Некорректные данные кошелька {code}.")

            wallet = Wallet(
                str(wallet_data["currency_code"]),
                float(wallet_data["balance"]),
            )
            portfolio._wallets[str(code)] = wallet

        return portfolio
