"""Консольный интерфейс приложения ValutaTrade Hub."""

import logging
import math
import shlex

from prettytable import PrettyTable

from valutatrade_hub.core.currencies import (
    CURRENCIES,
    CryptoCurrency,
    get_currency,
)
from valutatrade_hub.core.usecases import (
    ExchangeUseCases,
    PortfolioUseCases,
    RatesUseCases,
    UserUseCases,
)


class ConsoleInterface:
    """Обрабатывает команды пользователя в консоли."""

    def __init__(self) -> None:
        self.users = UserUseCases()
        self.portfolios = PortfolioUseCases()
        self.exchange = ExchangeUseCases()
        self.rates = RatesUseCases()
        self.current_user = None
        self.running = True

    def run(self) -> None:
        """Запускает цикл ввода команд."""
        print("ValutaTrade Hub")
        print("Введите help для списка команд.")

        while self.running:
            try:
                command_line = input("valutatrade> ").strip()
                if not command_line:
                    continue
                self.execute(command_line)
            except (ValueError, TypeError) as error:
                print(f"Ошибка: {error}")
            except KeyboardInterrupt:
                print("\nДля выхода введите exit.")
            except EOFError:
                print("\nРабота приложения завершена.")
                self.running = False

    def execute(self, command_line: str) -> None:
        """Разбирает и выполняет введённую команду."""
        try:
            parts = shlex.split(command_line)
        except ValueError as error:
            print(f"Ошибка разбора команды: {error}")
            return

        if not parts:
            return

        command, *args = parts
        commands = {
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

        handler = commands.get(command)
        if handler is None:
            print(f"Неизвестная команда: {command}. Введите help.")
            return

        try:
            handler(args)
        except (ValueError, TypeError) as error:
            print(f"Ошибка: {error}")
        except Exception as error:
            print(f"Не удалось выполнить команду: {error}")

    @staticmethod
    def _parse_options(
        args: list[str],
        required: set[str],
        optional: set[str] | None = None,
    ) -> dict[str, str]:
        """Разбирает аргументы формата --имя значение."""
        allowed = required | (optional or set())
        options = {}
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
                raise ValueError(f"Для {argument} необходимо указать значение.")

            options[name] = args[index + 1]
            index += 2

        missing = required - options.keys()
        if missing:
            names = ", ".join(f"--{name}" for name in sorted(missing))
            raise ValueError(f"Не указаны обязательные аргументы: {names}")

        return options

    @staticmethod
    def _parse_amount(value: str) -> float:
        """Преобразует сумму и проверяет её корректность."""
        try:
            amount = float(value)
        except ValueError as error:
            raise ValueError("Количество должно быть числом.") from error

        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Количество должно быть положительным конечным числом.")

        return amount

    def _require_login(self) -> bool:
        """Проверяет, вошёл ли пользователь в систему."""
        if self.current_user is None:
            print("Сначала выполните команду login.")
            return False
        return True

    @staticmethod
    def show_help(args: list[str]) -> None:
        """Показывает список доступных команд."""
        if args:
            raise ValueError("Использование: help")

        table = PrettyTable()
        table.field_names = ["Команда", "Аргументы", "Описание"]
        table.add_rows(
            [
                ["register", "--username --password", "Регистрация пользователя"],
                ["login", "--username --password", "Вход в систему"],
                ["show-portfolio", "[--base]", "Просмотр портфеля"],
                ["add-currency", "--currency", "Добавление кошелька"],
                ["deposit", "--currency --amount", "Пополнение кошелька"],
                ["buy", "--currency --amount", "Покупка валюты за USD"],
                ["sell", "--currency --amount", "Продажа валюты за USD"],
                ["get-rate", "--from --to", "Получение курса"],
                ["update-rates", "[--source]", "Обновление курсов"],
                [
                    "show-rates",
                    "[--currency] [--top] [--base]",
                    "Просмотр сохранённых курсов",
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
        """Показывает кошельки и общую стоимость портфеля."""
        options = self._parse_options(args, set(), {"base"})
        if not self._require_login():
            return

        base_currency = options.get("base", "USD").upper()
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
            table.add_row([code, f"{wallet['balance']:.8f}"])
        print(table)
        print(f"Общая стоимость в {base_currency}: {data['total_value']:.2f}")

    def add_currency(self, args: list[str]) -> None:
        """Добавляет валютный кошелёк в портфель."""
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
        print(f"Кошелёк {code} пополнен на {amount:g}.")

    def buy(self, args: list[str]) -> None:
        """Покупает указанное количество валюты за USD."""
        options = self._parse_options(args, {"currency", "amount"})

        if not self._require_login():
            return

        code = options["currency"].upper()
        amount = self._parse_amount(options["amount"])
        self.exchange.buy(self.current_user.user_id, code, amount)
        print(f"Покупка выполнена: {amount:g} {code}.")

    def sell(self, args: list[str]) -> None:
        """Продаёт указанное количество валюты за USD."""
        options = self._parse_options(args, {"currency", "amount"})

        if not self._require_login():
            return

        code = options["currency"].upper()
        amount = self._parse_amount(options["amount"])
        proceeds = self.exchange.sell(self.current_user.user_id, code, amount)
        print(
            f"Продажа выполнена: {amount:g} {code}. "
            f"Оценочная выручка: {proceeds:.2f} USD."
        )

    def get_rate(self, args: list[str]) -> None:
        """Показывает курс одной валюты к другой."""
        options = self._parse_options(args, {"from", "to"})
        source = options["from"].upper()
        target = options["to"].upper()
        rate = self.rates.get_rate(source, target)
        print(f"Курс {source}/{target}: {rate:.8f}")

    def update_rates(self, args: list[str]) -> None:
        """Обновляет курсы через выбранный источник."""
        options = self._parse_options(args, set(), {"source"})
        source = options.get("source")

        if source is not None:
            source = source.lower()
            if source not in {"coingecko", "exchangerate"}:
                raise ValueError("Источник должен быть coingecko или exchangerate.")

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

        if result["errors"]:
            print(
                "Обновление завершено с ошибками. "
                f"Обновлено валютных пар: {result['updated_count']}"
            )
            for error in result["errors"]:
                print(f"Предупреждение: {error}")
        else:
            print(
                f"Обновление успешно. Обновлено валютных пар: {result['updated_count']}"
            )

        print(f"Время обновления: {result['last_refresh']}")

    def show_rates(self, args: list[str]) -> None:
        """Показывает сохранённые курсы с фильтрами и выбранной базой."""
        options = self._parse_options(args, set(), {"currency", "top", "base"})
        data = self.rates.show_rates()
        pairs = data.get("pairs", {})
        if not pairs:
            print("Сохранённых курсов нет. Выполните update-rates.")
            return

        currency = options.get("currency")
        if currency:
            currency = currency.upper()
            get_currency(currency)

        base_currency = options.get("base")
        if base_currency:
            base_currency = base_currency.upper()
            get_currency(base_currency)

        records = []
        for pair, record in pairs.items():
            if not isinstance(record, dict):
                continue
            currencies = pair.split("_")
            if len(currencies) != 2:
                continue
            if currency and currency not in currencies:
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
                if pair.endswith("_USD")
                and isinstance(CURRENCIES.get(pair.split("_")[0]), CryptoCurrency)
            ]
            records.sort(
                key=lambda item: item[1].get("rate", 0),
                reverse=True,
            )
            records = records[:top]
        else:
            records.sort(key=lambda item: item[0])

        if base_currency:
            converted_records = []
            for pair, record in records:
                source_code = pair.split("_")[0]
                if source_code == base_currency:
                    converted_rate = 1.0
                else:
                    try:
                        converted_rate = self.rates.get_rate(source_code, base_currency)
                    except Exception as error:
                        logging.getLogger(__name__).debug(
                            "Не удалось получить %s/%s: %s",
                            source_code,
                            base_currency,
                            error,
                        )
                        continue
                converted_records.append(
                    (
                        f"{source_code}_{base_currency}",
                        {**record, "rate": converted_rate},
                    )
                )
            records = converted_records

        if not records:
            print("Курсы по заданным фильтрам не найдены.")
            return

        table = PrettyTable()
        table.field_names = ["Пара", "Курс", "Источник", "Обновлено"]
        for pair, record in records:
            table.add_row(
                [
                    pair,
                    record.get("rate", "—"),
                    record.get("source", "—"),
                    record.get("updated_at", "—"),
                ]
            )
        print(table)

    def exit(self, args: list[str]) -> None:
        """Завершает работу приложения."""
        if args:
            raise ValueError("Использование: exit")

        self.running = False
        print("До свидания!")


def run() -> None:
    """Запускает консольный интерфейс."""
    ConsoleInterface().run()
