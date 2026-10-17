"""Обновление валютных курсов из внешних API."""

import logging

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.storage import RatesStorage

logger = logging.getLogger(__name__)


class RatesUpdater:
    """Получает курсы через API и передаёт их на сохранение."""

    def __init__(
        self,
        coingecko_client: CoinGeckoClient | None = None,
        exchange_rate_client: ExchangeRateApiClient | None = None,
        storage: RatesStorage | None = None,
    ) -> None:
        self.coingecko_client = coingecko_client or CoinGeckoClient()
        self.exchange_rate_client = (
            exchange_rate_client or ExchangeRateApiClient()
        )
        self.storage = storage or RatesStorage()

    def run_update(self) -> dict[str, float]:
        """Обновляет курсы и возвращает полученные значения."""
        fetched_rates: dict[str, float] = {}
        sources: dict[str, str] = {}

        clients = (
            ("CoinGecko", self.coingecko_client),
            ("ExchangeRate-API", self.exchange_rate_client),
        )

        for source, client in clients:
            try:
                rates = client.fetch_rates()
            except ApiRequestError as error:
                logger.warning(
                    "Не удалось получить курсы %s: %s",
                    source,
                    error,
                )
                continue

            fetched_rates.update(rates)

            for pair in rates:
                sources[pair] = source

        if not fetched_rates:
            raise ApiRequestError(
                "Не удалось обновить курсы ни из одного источника."
            )

        self.storage.save_current_rates(fetched_rates, sources)
        self.storage.append_history(fetched_rates, sources)

        logger.info("Обновлено валютных пар: %s", len(fetched_rates))

        return fetched_rates
