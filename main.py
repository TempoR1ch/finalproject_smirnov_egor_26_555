"""Точка входа приложения ValutaTrade Hub."""

from valutatrade_hub.cli.interface import run
from valutatrade_hub.logging_config import setup_logging


def main() -> None:
    """Настраивает логирование и запускает приложение."""
    setup_logging()
    run()


if __name__ == "__main__":
    main()