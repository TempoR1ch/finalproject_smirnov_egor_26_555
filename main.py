"""Точка входа приложения ValutaTrade Hub."""

import sys

from valutatrade_hub.cli.interface import ConsoleInterface
from valutatrade_hub.logging_config import setup_logging


def main() -> None:
    """Запускает приложение в интерактивном или командном режиме."""
    setup_logging()
    interface = ConsoleInterface()

    if len(sys.argv) > 1:
        interface.execute(" ".join(sys.argv[1:]))
    else:
        interface.run()


if __name__ == "__main__":
    main()
