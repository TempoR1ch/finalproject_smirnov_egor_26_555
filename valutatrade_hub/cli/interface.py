"""Консольный интерфейс приложения ValutaTrade Hub."""

import shlex

from prettytable import PrettyTable

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
    def _check_args(
        args: list[str],
        expected_count: int,
        usage: str,
    ) -> bool:
        """Проверяет количество аргументов команды."""
        if len(args) != expected_count:
            print(f"Использование: {usage}")
            return False
        return True

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
            print("Использование: help")
            return

        table = PrettyTable()
        table.field_names = ["Команда", "Аргументы", "Описание"]
        table.add_rows(
            [
                ["register", "имя пароль", "Регистрация пользователя"],
                ["login", "имя пароль", "Вход в систему"],
                ["show-portfolio", "", "Просмотр портфеля"],
                ["buy", "валюта количество", "Покупка валюты за USD"],
                ["sell", "валюта количество", "Продажа валюты за USD"],
                ["get-rate", "из_валюты в_валюту", "Получение курса"],
                ["update-rates", "", "Обновление валютных курсов"],
                ["show-rates", "", "Просмотр сохранённых курсов"],
                ["help", "", "Список команд"],
                ["exit", "", "Выход из приложения"],
            ]
        )
        print(table)

    def register(self, args: list[str]) -> None:
        """Регистрирует пользователя."""
        if not self._check_args(args, 2, "register <имя> <пароль>"):
            return

        user = self.users.register(args[0], args[1])
        print(f"Пользователь {user.username} зарегистрирован.")

    def login(self, args: list[str]) -> None:
        """Выполняет вход пользователя."""
        if not self._check_args(args, 2, "login <имя> <пароль>"):
            return

        user = self.users.login(args[0], args[1])
        self.current_user = user
        print(f"Вы вошли как {user.username}.")

    def show_portfolio(self, args: list[str]) -> None:
        """Показывает кошельки и общую стоимость портфеля."""
        if not self._check_args(args, 0, "show-portfolio"):
            return
        if not self._require_login():
            return

        portfolio = self.portfolios.get_portfolio(
            self.current_user.user_id
        )

        table = PrettyTable()
        table.field_names = ["Валюта", "Баланс"]

        for code, wallet in portfolio.wallets.items():
            table.add_row([code, f"{wallet.balance:.8f}"])

        if not portfolio.wallets:
            print("Портфель пока пуст.")
            return

        print(table)

        try:
            total = portfolio.get_total_value()
            print(f"Общая стоимость в USD: {total:.2f}")
        except ValueError as error:
            print(f"Не удалось рассчитать общую стоимость: {error}")

    def buy(self, args: list[str]) -> None:
        """Покупает указанное количество валюты за USD."""
        if not self._check_args(args, 2, "buy <валюта> <количество>"):
            return
        if not self._require_login():
            return

        amount = float(args[1])
        self.exchange.buy(
            self.current_user.user_id,
            args[0],
            amount,
        )
        print(f"Покупка выполнена: {amount} {args[0].upper()}.")

    def sell(self, args: list[str]) -> None:
        """Продаёт указанное количество валюты за USD."""
        if not self._check_args(args, 2, "sell <валюта> <количество>"):
            return
        if not self._require_login():
            return

        amount = float(args[1])
        self.exchange.sell(
            self.current_user.user_id,
            args[0],
            amount,
        )
        print(f"Продажа выполнена: {amount} {args[0].upper()}.")

    def get_rate(self, args: list[str]) -> None:
        """Показывает курс одной валюты к другой."""
        if not self._check_args(args, 2, "get-rate <из_валюты> <в_валюту>"):
            return

        rate = self.rates.get_rate(args[0], args[1])
        print(f"Курс {args[0].upper()}/{args[1].upper()}: {rate:.8f}")

    def update_rates(self, args: list[str]) -> None:
        """Обновляет курсы через внешние API."""
        if not self._check_args(args, 0, "update-rates"):
            return

        updated = self.rates.update_rates()
        print(f"Обновлено валютных пар: {len(updated)}")

    def show_rates(self, args: list[str]) -> None:
        """Показывает все сохранённые валютные курсы."""
        if not self._check_args(args, 0, "show-rates"):
            return

        data = self.rates.show_rates()
        pairs = data.get("pairs", {})

        if not pairs:
            print("Сохранённых курсов нет. Выполните update-rates.")
            return

        table = PrettyTable()
        table.field_names = ["Пара", "Курс", "Источник", "Обновлено"]

        for pair, record in sorted(pairs.items()):
            if not isinstance(record, dict):
                continue

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
        if not self._check_args(args, 0, "exit"):
            return

        self.running = False
        print("До свидания!")


def run() -> None:
    """Запускает консольный интерфейс."""
    ConsoleInterface().run()