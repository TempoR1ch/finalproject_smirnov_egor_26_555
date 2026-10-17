"""Периодическое обновление валютных курсов."""

import logging
from threading import Event, Thread

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.updater import RatesUpdater

logger = logging.getLogger(__name__)


class RatesScheduler:
    """Запускает периодическое обновление валютных курсов."""

    def __init__(self, updater: RatesUpdater | None = None) -> None:
        self.updater = updater or RatesUpdater()
        self.interval = SettingsLoader.get_rates_ttl()
        self._stop_event = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        """Запускает обновление в фоновом потоке."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Планировщик уже запущен.")
            return

        self._stop_event.clear()
        self._thread = Thread(
            target=self._run,
            name="rates-scheduler",
            daemon=True,
        )
        self._thread.start()
        logger.info("Планировщик запущен. Интервал: %s сек.", self.interval)

    def stop(self) -> None:
        """Останавливает планировщик."""
        self._stop_event.set()

        if self._thread is not None:
            self._thread.join()

        logger.info("Планировщик остановлен.")

    def _run(self) -> None:
        """Обновляет курсы с заданным интервалом."""
        while not self._stop_event.is_set():
            try:
                self.updater.run_update()
            except ApiRequestError as error:
                logger.error("Ошибка обновления курсов: %s", error)
            except Exception:
                logger.exception("Непредвиденная ошибка при обновлении курсов.")

            if self._stop_event.wait(self.interval):
                break
