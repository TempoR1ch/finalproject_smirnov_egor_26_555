"""Бизнес-логика операций с пользователями и валютными портфелями."""

import logging
import math
from datetime import datetime, timezone
from typing import Any

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import ApiRequestError, InsufficientFundsError
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.decorators import log_action, measure_time
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater

logger = logging.getLogger(__name__)

USERS_PATH = "data/users.json"
PORTFOLIOS_PATH = "data/portfolios.json"


class UserUseCases:
    """Выполняет операции регистрации и аутентификации пользователей."""

    def __init__(self, database: DatabaseManager | None = None) -> None:
        self.database = database or DatabaseManager()

    def _load_users(self) -> list[User]:
        """Загружает пользователей из JSON."""
        records = self.database.read_json(USERS_PATH, default=[])
        if not isinstance(records, list):
            raise ValueError("Файл пользователей содержит неверный формат.")

        return [
            User.from_dict(record) for record in records if isinstance(record, dict)
        ]

    def _save_users(self, users: list[User]) -> None:
        """Сохраняет пользователей в JSON."""
        self.database.write_json(
            USERS_PATH,
            [user.to_dict() for user in users],
        )

    @log_action
    def register(self, username: str, password: str) -> User:
        """Регистрирует пользователя и создаёт пустой портфель."""
        normalized_username = username.strip()
        if not normalized_username:
            raise ValueError("Имя пользователя не может быть пустым.")
        if not password:
            raise ValueError("Пароль не может быть пустым.")

        users = self._load_users()
        if any(
            user.username.casefold() == normalized_username.casefold() for user in users
        ):
            raise ValueError("Пользователь с таким именем уже существует.")

        user_id = max((user.user_id for user in users), default=0) + 1
        user = User(user_id, normalized_username, password)
        users.append(user)
        self._save_users(users)

        portfolios = PortfolioUseCases(self.database)
        portfolios.create_portfolio(user)

        logger.info("Зарегистрирован пользователь: %s", user.username)
        return user

    def login(self, username: str, password: str) -> User:
        """Проверяет имя пользователя и пароль."""
        normalized_username = username.strip().casefold()

        for user in self._load_users():
            if user.username.casefold() == normalized_username and user.verify_password(
                password
            ):
                logger.info("Выполнен вход пользователя: %s", user.username)
                return user

        raise ValueError("Неверное имя пользователя или пароль.")


class PortfolioUseCases:
    """Выполняет операции с портфелями и валютными кошельками."""

    def __init__(self, database: DatabaseManager | None = None) -> None:
        self.database = database or DatabaseManager()

    def _load_portfolios(self) -> list[Portfolio]:
        """Загружает портфели из JSON."""
        records = self.database.read_json(PORTFOLIOS_PATH, default=[])
        if not isinstance(records, list):
            raise ValueError("Файл портфелей содержит неверный формат.")

        user_records = self.database.read_json(USERS_PATH, default=[])
        users = {}
        if isinstance(user_records, list):
            for record in user_records:
                if isinstance(record, dict):
                    user = User.from_dict(record)
                    users[user.user_id] = user

        portfolios = []
        for record in records:
            if isinstance(record, dict):
                user_id = int(record["user_id"])
                portfolios.append(Portfolio.from_dict(record, user=users.get(user_id)))
        return portfolios

    def _save_portfolios(self, portfolios: list[Portfolio]) -> None:
        """Сохраняет портфели в JSON."""
        self.database.write_json(
            PORTFOLIOS_PATH,
            [portfolio.to_dict() for portfolio in portfolios],
        )

    def create_portfolio(self, user: User | int) -> Portfolio:
        """Создаёт пустой портфель, если его ещё нет."""
        user_id = user.user_id if isinstance(user, User) else user
        portfolios = self._load_portfolios()

        for portfolio in portfolios:
            if portfolio.user_id == user_id:
                return portfolio

        portfolio = Portfolio(user)
        self._save_portfolios([*portfolios, portfolio])
        return portfolio

    def get_portfolio(self, user_id: int) -> Portfolio:
        """Возвращает портфель пользователя."""
        for portfolio in self._load_portfolios():
            if portfolio.user_id == user_id:
                return portfolio

        raise ValueError("Портфель пользователя не найден.")

    @log_action
    def show_portfolio(
        self,
        user_id: int,
        base_currency: str = "USD",
    ) -> dict[str, Any]:
        """Готовит данные портфеля и итоговую стоимость для CLI."""
        base_currency = base_currency.strip().upper()
        get_currency(base_currency)
        portfolio = self.get_portfolio(user_id)
        rates_data = RatesStorage(database=self.database).get_current_rates()
        rates = rates_data if rates_data.get("pairs") else None
        total = portfolio.get_total_value(base_currency, rates)
        return {
            "user_id": portfolio.user_id,
            "wallets": {
                code: wallet.get_balance_info()
                for code, wallet in portfolio.wallets.items()
            },
            "base_currency": base_currency,
            "total_value": total,
        }

    @log_action
    def add_currency(self, user_id: int, currency_code: str) -> None:
        """Создаёт валютный кошелёк в портфеле."""
        portfolios = self._load_portfolios()
        portfolio = self._find_portfolio(portfolios, user_id)
        portfolio.add_currency(currency_code)
        self._save_portfolios(portfolios)

    @log_action
    def deposit(
        self,
        user_id: int,
        currency_code: str,
        amount: float,
    ) -> None:
        """Пополняет кошелёк пользователя."""
        portfolios = self._load_portfolios()
        portfolio = self._find_portfolio(portfolios, user_id)
        wallet = self._get_or_create_wallet(portfolio, currency_code)
        wallet.deposit(amount)
        self._save_portfolios(portfolios)

    @log_action
    def withdraw(
        self,
        user_id: int,
        currency_code: str,
        amount: float,
    ) -> None:
        """Списывает средства с кошелька пользователя."""
        portfolios = self._load_portfolios()
        portfolio = self._find_portfolio(portfolios, user_id)
        wallet = portfolio.get_wallet(currency_code)
        wallet.withdraw(amount)
        self._save_portfolios(portfolios)

    @staticmethod
    def _find_portfolio(
        portfolios: list[Portfolio],
        user_id: int,
    ) -> Portfolio:
        """Находит портфель в списке."""
        for portfolio in portfolios:
            if portfolio.user_id == user_id:
                return portfolio
        raise ValueError("Портфель пользователя не найден.")

    @staticmethod
    def _get_or_create_wallet(
        portfolio: Portfolio,
        currency_code: str,
    ):
        """Возвращает кошелёк, создавая его при необходимости."""
        normalized_code = currency_code.strip().upper()
        get_currency(normalized_code)

        if normalized_code not in portfolio.wallets:
            return portfolio.add_currency(normalized_code)

        return portfolio.get_wallet(normalized_code)


class ExchangeUseCases:
    """Выполняет обмен валют по сохранённым курсам."""

    def __init__(
        self,
        database: DatabaseManager | None = None,
        rates_storage: RatesStorage | None = None,
        updater: RatesUpdater | None = None,
    ) -> None:
        self.database = database or DatabaseManager()
        self.portfolios = PortfolioUseCases(self.database)
        self.rates_storage = rates_storage or RatesStorage()
        self.updater = updater or RatesUpdater(storage=self.rates_storage)

    def get_rate(self, from_currency: str, to_currency: str) -> float:
        """Возвращает курс из свежего кэша, обновляя только при необходимости."""
        source = from_currency.strip().upper()
        target = to_currency.strip().upper()
        get_currency(source)
        get_currency(target)
        if source == target:
            return 1.0

        def read_pairs() -> dict[str, Any]:
            current = self.rates_storage.get_current_rates()
            pairs = current.get("pairs", {})
            if not isinstance(pairs, dict):
                raise ValueError("Некорректный формат кэша валютных курсов.")
            return pairs

        ttl = SettingsLoader().get_rates_ttl()

        def valid_rate(pairs: dict[str, Any], pair: str) -> float | None:
            record = pairs.get(pair)
            value = record.get("rate") if isinstance(record, dict) else None
            if (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                and value > 0
            ):
                return float(value)
            return None

        def pair_is_fresh(pairs: dict[str, Any], pair: str) -> bool:
            record = pairs.get(pair)
            updated_at = record.get("updated_at") if isinstance(record, dict) else None
            if not isinstance(updated_at, str):
                return False
            try:
                timestamp = datetime.fromisoformat(updated_at)
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
            except ValueError:
                return False
            age = (datetime.now(timezone.utc) - timestamp).total_seconds()
            return -60 <= age <= ttl

        def choose_usd_rate(
            pairs: dict[str, Any], code: str
        ) -> tuple[float | None, str | None]:
            direct_pair = f"{code}_USD"
            reverse_pair = f"USD_{code}"
            direct = valid_rate(pairs, direct_pair)
            reverse = valid_rate(pairs, reverse_pair)

            if direct is not None and pair_is_fresh(pairs, direct_pair):
                return direct, direct_pair
            if reverse is not None and pair_is_fresh(pairs, reverse_pair):
                return 1.0 / reverse, reverse_pair
            if direct is not None:
                return direct, direct_pair
            if reverse is not None:
                return 1.0 / reverse, reverse_pair
            return None, None

        def resolve(pairs: dict[str, Any]) -> tuple[float | None, list[str]]:
            direct_pair = f"{source}_{target}"
            reverse_pair = f"{target}_{source}"
            direct = valid_rate(pairs, direct_pair)
            reverse = valid_rate(pairs, reverse_pair)

            if direct is not None and pair_is_fresh(pairs, direct_pair):
                return direct, [direct_pair]
            if reverse is not None and pair_is_fresh(pairs, reverse_pair):
                return 1.0 / reverse, [reverse_pair]
            if direct is not None:
                return direct, [direct_pair]
            if reverse is not None:
                return 1.0 / reverse, [reverse_pair]

            if source != "USD" and target != "USD":
                source_usd, source_pair = choose_usd_rate(pairs, source)
                target_usd, target_pair = choose_usd_rate(pairs, target)
                if source_usd is not None and target_usd is not None:
                    return source_usd / target_usd, [source_pair, target_pair]
            return None, []

        def is_fresh(pairs: dict[str, Any], used_pairs: list[str]) -> bool:
            return bool(used_pairs) and all(
                pair_is_fresh(pairs, pair) for pair in used_pairs
            )

        pairs = read_pairs()
        rate, used_pairs = resolve(pairs)
        if rate is None or not is_fresh(pairs, used_pairs):
            try:
                self.updater.run_update()
            except ApiRequestError as error:
                raise ApiRequestError(
                    f"Курс {source}/{target} отсутствует или устарел; "
                    "обновить данные не удалось. Повторите update-rates позже. "
                    f"Подробности: {error}"
                ) from error
            pairs = read_pairs()
            rate, used_pairs = resolve(pairs)
            if rate is None or not is_fresh(pairs, used_pairs):
                raise ApiRequestError(
                    f"Курс {source}/{target} отсутствует или неактуален "
                    "после обновления."
                )

        return rate

    @log_action
    @measure_time
    def buy(
        self,
        user_id: int,
        currency_code: str,
        amount: float,
    ) -> None:
        """Упрощённая покупка: создаёт кошелёк и увеличивает его баланс."""
        code = currency_code.strip().upper()
        get_currency(code)
        self._validate_amount(amount)
        if code == "USD":
            raise ValueError("Покупка USD за USD не имеет смысла.")

        portfolios = self.portfolios._load_portfolios()
        portfolio = self.portfolios._find_portfolio(portfolios, user_id)
        wallet = self.portfolios._get_or_create_wallet(portfolio, code)
        wallet.deposit(amount)
        self.portfolios._save_portfolios(portfolios)

    @log_action
    @measure_time
    def sell(
        self,
        user_id: int,
        currency_code: str,
        amount: float,
    ) -> float:
        """Упрощённая продажа: уменьшает баланс и возвращает оценку выручки USD."""
        code = currency_code.strip().upper()
        get_currency(code)
        self._validate_amount(amount)
        if code == "USD":
            raise ValueError("Продажа USD за USD не имеет смысла.")

        portfolios = self.portfolios._load_portfolios()
        portfolio = self.portfolios._find_portfolio(portfolios, user_id)
        wallet = portfolio.get_wallet(code)
        if amount > wallet.balance:
            raise InsufficientFundsError(wallet.balance, amount, code)

        rate = self.get_rate(code, "USD")
        proceeds = amount * rate
        if not math.isfinite(proceeds):
            raise ValueError("Оценочная выручка должна быть конечным числом.")

        wallet.withdraw(amount)
        self.portfolios._save_portfolios(portfolios)
        return proceeds

    @staticmethod
    def _validate_amount(amount: float) -> None:
        """Проверяет, что сумма является положительным конечным числом."""
        if not isinstance(amount, (int, float)) or isinstance(amount, bool):
            raise ValueError("Количество валюты должно быть числом.")

        if not math.isfinite(amount) or amount <= 0:
            raise ValueError(
                "Количество валюты должно быть положительным конечным числом."
            )


class RatesUseCases:
    """Предоставляет операции получения и обновления курсов."""

    def __init__(
        self,
        updater: RatesUpdater | None = None,
        storage: RatesStorage | None = None,
    ) -> None:
        self.updater = updater or RatesUpdater()
        self.storage = storage or RatesStorage()

    def get_rate(self, from_currency: str, to_currency: str) -> float:
        """Возвращает сохранённый курс валютной пары."""
        return ExchangeUseCases(rates_storage=self.storage).get_rate(
            from_currency,
            to_currency,
        )

    def show_rates(self) -> dict[str, Any]:
        """Возвращает все сохранённые курсы."""
        return self.storage.get_current_rates()

    @log_action
    @measure_time
    def update_rates(self, source: str | None = None) -> dict[str, Any]:
        """Получает курсы и возвращает результат обновления."""
        try:
            return self.updater.run_update(source=source)
        except ApiRequestError:
            logger.exception("Не удалось обновить валютные курсы.")
            raise
