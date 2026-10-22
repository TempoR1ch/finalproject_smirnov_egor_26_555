"""Интерфейс командной строки ValutaTrade Hub."""

import logging
import math
import shlex

from prettytable import PrettyTable

from valutatrade_hub.core.currencies import (
    CURRENCIES,
    CryptoCurrency,
    get_currency,
)
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.usecases import (
    ExchangeUseCases,
    PortfolioUseCases,
    RatesUseCases,
    UserUseCases,
)

logger = logging.getLogger(__name__)


class ConsoleInterface:
    """Обрабатывает команды пользователя."""

    def __init__(self) -> None:
        self.users = UserUseCases()
        self.portfolios = PortfolioUseCases()
        self.exchange = ExchangeUseCases()
        self.rates = RatesUseCases()
        self.current_user = None
        self.running = True

    def run(self) -> None:
        """Запускает интерактивный цикл команд."""
        self.show_help()

        while self.running:
            try:
                command = input("valutatrade> ").strip()
                if not command:
                    continue
                self.execute(command)
            except (ValueError, TypeError) as error:
                print(f"Ошибка: {error}")
            except (KeyboardInterrupt, EOFError):
                print()
                self.exit([])
            except Exception:
                logger.exception("Необработанная ошибка в цикле CLI")
                print("Произошла внутренняя ошибка. Подробности записаны в лог.")

    def execute(self, command: str) -> None:
        """Разбирает команду и вызывает соответствующий обработчик."""
        try:
            parts = shlex.split(command)
        except ValueError as error:
            print(f"Ошибка разбора команды: {error}")
            return

        if not parts:
            return

        command_name = parts[0].lower()
        args = parts[1:]

        handlers = {
            "help": self.show_help,
            "register": self.register,
            "login": self.login,
            "show-portfolio": self.show_portfolio,
            "add-currency": self.add_currency,
            "deposit": self.deposit,
            "buy": self.buy,
            "sell": self.sell,
            "get-rate": self.get_rate,
            "update-rates": self.update_rates,
            "show-rates": self.show_rates,
            "exit": self.exit,
        }

        handler = handlers.get(command_name)
        if handler is None:
            print(f"Неизвестная команда: {command_name}. Введите help.")
            return

        try:
            handler(args)
        except InsufficientFundsError as error:
            print(error)
        except CurrencyNotFoundError as error:
            supported = ", ".join(sorted(CURRENCIES))
            print(error)
            print(f"Поддерживаемые коды валют: {supported}")
            print("Для просмотра курса используйте команду get-rate.")
        except ApiRequestError as error:
            print(error)
            print("Проверьте подключение к интернету и повторите попытку.")
        except (ValueError, TypeError) as error:
            print(f"Ошибка: {error}")
        except Exception:
            logger.exception("Ошибка выполнения команды %s", command_name)
            print("Не удалось выполнить команду. Подробности записаны в лог.")

    @staticmethod
    def _parse_options(
        args: list[str],
        required: set[str],
        optional: set[str] | None = None,
    ) -> dict[str, str]:
        """Разбирает именованные аргументы вида --name value."""
        optional = optional or set()
        allowed = required | optional
        options: dict[str, str] = {}
        index = 0

        while index < len(args):
            argument = args[index]

            if not argument.startswith("--"):
                raise ValueError(f"Ожидался именованный аргумент, получено: {argument}")

            name = argument[2:]
            if name not in allowed:
                raise ValueError(f"Неизвестный аргумент: {argument}")

            if name in options:
                raise ValueError(f"Аргумент {argument} указан повторно.")

            if index + 1 >= len(args) or args[index + 1].startswith("--"):
                raise ValueError(
                    f"Для аргумента {argument} необходимо указать значение."
                )

            options[name] = args[index + 1]
            index += 2

        missing = required - options.keys()
        if missing:
            raise ValueError(
                "Не указаны обязательные аргументы: "
                + ", ".join(f"--{name}" for name in sorted(missing))
            )

        return options

    @staticmethod
    def _parse_amount(value: str) -> float:
        """Проверяет положительную конечную сумму."""
        try:
            amount = float(value)
        except ValueError as error:
            raise ValueError("Сумма должна быть числом.") from error

        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Сумма должна быть конечным числом больше нуля.")

        return amount

    def _require_login(self) -> bool:
        """Проверяет, авторизован ли пользователь."""
        if self.current_user is None:
            print("Сначала выполните login.")
            return False
        return True

    def show_help(self, args: list[str] | None = None) -> None:
        """Показывает список доступных команд."""
        if args:
            raise ValueError("Использование: help")

        table = PrettyTable()
        table.field_names = ["Команда", "Аргументы", "Описание"]
        table.add_rows(
            [
                ["register", "--username --password", "Регистрация пользователя"],
                ["login", "--username --password", "Вход в аккаунт"],
                ["show-portfolio", "[--base USD]", "Просмотр портфеля"],
                ["add-currency", "--currency", "Добавление кошелька"],
                ["deposit", "--currency --amount", "Пополнение кошелька"],
                ["buy", "--currency --amount", "Покупка валюты за USD"],
                ["sell", "--currency --amount", "Продажа валюты за USD"],
                ["get-rate", "--from --to", "Получение курса валют"],
                [
                    "update-rates",
                    "[--source coingecko|exchangerate]",
                    "Обновление курсов",
                ],
                [
                    "show-rates",
                    "[--currency CODE] [--top N] [--base CODE]",
                    "Просмотр курсов",
                ],
                ["help", "", "Список команд"],
                ["exit", "", "Выход из приложения"],
            ]
        )
        print(table)

    def register(self, args: list[str]) -> None:
        """Регистрирует пользователя."""
        options = self._parse_options(args, {"username", "password"})
        user = self.users.register(options["username"], options["password"])
        print(f"Пользователь {user.username} зарегистрирован.")

    def login(self, args: list[str]) -> None:
        """Выполняет вход пользователя."""
        options = self._parse_options(args, {"username", "password"})
        user = self.users.login(options["username"], options["password"])
        self.current_user = user
        print(f"Вы вошли как {user.username}.")

    def show_portfolio(self, args: list[str]) -> None:
        """Показывает портфель в выбранной базовой валюте."""
        if not self._require_login():
            return

        options = self._parse_options(args, set(), {"base"})
        base_currency = options.get("base", "USD").upper()
        get_currency(base_currency)

        data = self.portfolios.show_portfolio(
            self.current_user.user_id,
            base_currency,
        )
        wallets = data["wallets"]

        if not wallets:
            print("Портфель пока пуст.")
            print(f"Общая стоимость в {base_currency}: 0.00")
            return

        table = PrettyTable()
        table.field_names = ["Валюта", "Баланс"]

        for code, wallet in wallets.items():
            table.add_row([code, f"{wallet['balance']:.8g}"])

        print(table)
        print(f"Общая стоимость в {base_currency}: {data['total_value']:.2f}")

    def add_currency(self, args: list[str]) -> None:
        """Добавляет валютный кошелёк."""
        options = self._parse_options(args, {"currency"})
        if not self._require_login():
            return

        code = options["currency"].upper()
        self.portfolios.add_currency(self.current_user.user_id, code)
        print(f"Кошелёк {code} добавлен.")

    def deposit(self, args: list[str]) -> None:
        """Пополняет валютный кошелёк."""
        options = self._parse_options(args, {"currency", "amount"})
        if not self._require_login():
            return

        code = options["currency"].upper()
        amount = self._parse_amount(options["amount"])
        self.portfolios.deposit(self.current_user.user_id, code, amount)
        print(f"Баланс {code} пополнен на {amount:.8g}.")

    def buy(self, args: list[str]) -> None:
        """Покупает указанное количество валюты за USD."""
        options = self._parse_options(args, {"currency", "amount"})
        if not self._require_login():
            return

        code = options["currency"].upper()
        amount = self._parse_amount(options["amount"])
        self.exchange.buy(self.current_user.user_id, code, amount)
        print(f"Куплено {amount:.8g} {code}.")

    def sell(self, args: list[str]) -> None:
        """Продаёт валюту и показывает оценочную выручку в USD."""
        options = self._parse_options(args, {"currency", "amount"})
        if not self._require_login():
            return

        code = options["currency"].upper()
        amount = self._parse_amount(options["amount"])
        proceeds = self.exchange.sell(self.current_user.user_id, code, amount)
        print(f"Продано {amount:.8g} {code}. Выручка: {proceeds:.2f} USD.")

    def get_rate(self, args: list[str]) -> None:
        """Показывает курс одной валюты к другой."""
        options = self._parse_options(args, {"from", "to"})
        source = options["from"].upper()
        target = options["to"].upper()

        rate = self.rates.get_rate(source, target)
        print(f"1 {source} = {rate:.8g} {target}")

    def update_rates(self, args: list[str]) -> None:
        """Обновляет курсы через выбранный источник."""
        options = self._parse_options(args, set(), {"source"})
        source = options.get("source")

        if source is not None:
            source = source.lower()
            if source not in {"coingecko", "exchangerate"}:
                raise ValueError("--source должен быть coingecko или exchangerate.")

        parser_logger = logging.getLogger("valutatrade_hub.parser_service")
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        parser_logger.addHandler(console_handler)

        try:
            result = self.rates.update_rates(source=source)
        finally:
            parser_logger.removeHandler(console_handler)
            console_handler.close()

        updated_count = result["updated_count"]
        print(f"Обновление завершено. Получено пар: {updated_count}.")

        if result.get("last_refresh"):
            print(f"Последнее обновление: {result['last_refresh']}")

        errors = result.get("errors", [])
        if errors:
            print(
                "Обновление завершено с ошибками некоторых источников. "
                "Подробности: logs/parser.log"
            )
            for error in errors:
                print(f"Предупреждение: {error}")

    def show_rates(self, args: list[str]) -> None:
        """Показывает сохранённые курсы с фильтрами и выбранной базой."""
        options = self._parse_options(
            args,
            set(),
            {"currency", "top", "base"},
        )
        data = self.rates.show_rates()
        pairs = data.get("pairs", {})

        if not pairs:
            print("Сохранённых курсов нет. Выполните update-rates.")
            return

        currency = options.get("currency")
        if currency:
            currency = currency.upper()
            get_currency(currency)

        base_currency = options.get("base", "USD").upper()
        get_currency(base_currency)

        records = []
        for pair, record in pairs.items():
            if not isinstance(pair, str) or not isinstance(record, dict):
                continue
            if "_" not in pair:
                continue

            source_code, target_code = pair.split("_", maxsplit=1)
            if currency and source_code != currency:
                continue
            if target_code != "USD":
                continue

            rate = record.get("rate")
            if (
                isinstance(rate, bool)
                or not isinstance(rate, (int, float))
                or not math.isfinite(rate)
                or rate <= 0
            ):
                continue

            records.append((pair, record))

        if "top" in options:
            try:
                top = int(options["top"])
            except ValueError as error:
                raise ValueError("--top должен быть целым числом.") from error

            if top <= 0:
                raise ValueError("--top должен быть больше нуля.")

            records = [
                (pair, record)
                for pair, record in records
                if isinstance(
                    CURRENCIES.get(pair.split("_")[0]),
                    CryptoCurrency,
                )
            ]
            records.sort(
                key=lambda item: item[1]["rate"],
                reverse=True,
            )
            records = records[:top]
        else:
            records.sort(key=lambda item: item[0])

        table = PrettyTable()
        table.field_names = [
            "Пара",
            f"Курс ({base_currency})",
            "Источник",
            "Обновлено",
        ]
        skipped = 0

        for pair, record in records:
            source_code = pair.split("_", maxsplit=1)[0]

            try:
                converted_rate = (
                    1.0
                    if source_code == base_currency
                    else self.rates.get_rate(source_code, base_currency)
                )
            except (
                ApiRequestError,
                CurrencyNotFoundError,
                ValueError,
                TypeError,
            ) as error:
                skipped += 1
                logger.warning(
                    "Не удалось преобразовать курс %s в %s: %s",
                    source_code,
                    base_currency,
                    error,
                )
                continue

            table.add_row(
                [
                    f"{source_code}_{base_currency}",
                    f"{converted_rate:.8g}",
                    record.get("source", "-"),
                    record.get("updated_at", "-"),
                ]
            )

        if not table.rows:
            print("Не удалось показать курсы для выбранной базовой валюты.")
            if skipped:
                print(f"Пропущено строк из-за ошибок конвертации: {skipped}")
            return

        print(table)
        if skipped:
            print(f"Предупреждение: пропущено строк: {skipped}")

    def exit(self, args: list[str] | None = None) -> None:
        """Завершает работу приложения."""
        if args:
            raise ValueError("Использование: exit")

        self.running = False
        print("До свидания!")
