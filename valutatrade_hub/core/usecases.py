"""Бизнес-логика операций с пользователями и валютными портфелями."""

import logging
from typing import Any

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.decorators import log_action, measure_time
from valutatrade_hub.infra.database import DatabaseManager
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
        portfolios.create_portfolio(user.user_id)

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

        return [
            Portfolio.from_dict(record)
            for record in records
            if isinstance(record, dict)
        ]

    def _save_portfolios(self, portfolios: list[Portfolio]) -> None:
        """Сохраняет портфели в JSON."""
        self.database.write_json(
            PORTFOLIOS_PATH,
            [portfolio.to_dict() for portfolio in portfolios],
        )

    def create_portfolio(self, user_id: int) -> Portfolio:
        """Создаёт пустой портфель, если его ещё нет."""
        portfolios = self._load_portfolios()

        for portfolio in portfolios:
            if portfolio.user_id == user_id:
                return portfolio

        portfolio = Portfolio(user_id)
        self._save_portfolios([*portfolios, portfolio])
        return portfolio

    def get_portfolio(self, user_id: int) -> Portfolio:
        """Возвращает портфель пользователя."""
        for portfolio in self._load_portfolios():
            if portfolio.user_id == user_id:
                return portfolio

        raise ValueError("Портфель пользователя не найден.")

    @log_action
    def show_portfolio(self, user_id: int) -> dict[str, Any]:
        """Возвращает данные портфеля для отображения."""
        portfolio = self.get_portfolio(user_id)
        return {
            "user_id": portfolio.user_id,
            "wallets": {
                code: wallet.get_balance_info()
                for code, wallet in portfolio.wallets.items()
            },
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
    ) -> None:
        self.database = database or DatabaseManager()
        self.portfolios = PortfolioUseCases(self.database)
        self.rates_storage = rates_storage or RatesStorage()

    def get_rate(self, from_currency: str, to_currency: str) -> float:
        """Возвращает курс обмена из кэша."""
        source = from_currency.strip().upper()
        target = to_currency.strip().upper()
        get_currency(source)
        get_currency(target)

        if source == target:
            return 1.0

        current = self.rates_storage.get_current_rates()
        pairs = current.get("pairs", {})
        pair = f"{source}_{target}"

        if isinstance(pairs, dict):
            record = pairs.get(pair)
            if isinstance(record, dict):
                rate = record.get("rate")
                if isinstance(rate, (int, float)) and rate > 0:
                    return float(rate)

        reverse_pair = f"{target}_{source}"
        if isinstance(pairs, dict):
            record = pairs.get(reverse_pair)
            if isinstance(record, dict):
                rate = record.get("rate")
                if isinstance(rate, (int, float)) and rate > 0:
                    return 1.0 / float(rate)

        raise ValueError(f"Курс {source}/{target} отсутствует в кэше.")

    @log_action
    @measure_time
    def buy(
        self,
        user_id: int,
        currency_code: str,
        amount: float,
    ) -> None:
        """Покупает валюту за USD."""
        code = currency_code.strip().upper()
        get_currency(code)

        if code == "USD":
            raise ValueError("Покупка USD за USD не имеет смысла.")
        if amount <= 0:
            raise ValueError("Количество валюты должно быть положительным.")

        rate = self.get_rate("USD", code)
        cost = amount / rate

        portfolios = self.portfolios._load_portfolios()
        portfolio = self.portfolios._find_portfolio(portfolios, user_id)
        usd_wallet = portfolio.get_wallet("USD")
        usd_wallet.withdraw(cost)
        self.portfolios._get_or_create_wallet(portfolio, code).deposit(amount)
        self.portfolios._save_portfolios(portfolios)

    @log_action
    @measure_time
    def sell(
        self,
        user_id: int,
        currency_code: str,
        amount: float,
    ) -> None:
        """Продаёт валюту и зачисляет выручку в USD."""
        code = currency_code.strip().upper()
        get_currency(code)

        if code == "USD":
            raise ValueError("Продажа USD за USD не имеет смысла.")
        if amount <= 0:
            raise ValueError("Количество валюты должно быть положительным.")

        rate = self.get_rate(code, "USD")
        proceeds = amount * rate

        portfolios = self.portfolios._load_portfolios()
        portfolio = self.portfolios._find_portfolio(portfolios, user_id)
        wallet = portfolio.get_wallet(code)
        wallet.withdraw(amount)
        self.portfolios._get_or_create_wallet(portfolio, "USD").deposit(proceeds)
        self.portfolios._save_portfolios(portfolios)


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
