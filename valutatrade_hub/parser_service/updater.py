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
        self.exchange_rate_client = exchange_rate_client or ExchangeRateApiClient()
        self.storage = storage or RatesStorage()

    def run_update(self, source: str | None = None) -> dict[str, float]:
        """Обновляет курсы из выбранного источника или из всех источников."""
        available_clients = {
            "coingecko": ("CoinGecko", self.coingecko_client),
            "exchangerate": ("ExchangeRate-API", self.exchange_rate_client),
        }

        if source is not None and source not in available_clients:
            raise ValueError("Источник должен быть coingecko или exchangerate.")

        if source is None:
            clients = list(available_clients.values())
        else:
            clients = [available_clients[source]]

        fetched_rates: dict[str, float] = {}
        sources: dict[str, str] = {}

        for source_name, client in clients:
            try:
                rates = client.fetch_rates()
            except ApiRequestError as error:
                logger.warning(
                    "Не удалось получить курсы %s: %s",
                    source_name,
                    error,
                )
                continue

            fetched_rates.update(rates)

            for pair in rates:
                sources[pair] = source_name

        if not fetched_rates:
            raise ApiRequestError("Не удалось обновить курсы ни из одного источника.")

        self.storage.save_current_rates(fetched_rates, sources)
        self.storage.append_history(fetched_rates, sources)

        logger.info("Обновлено валютных пар: %s", len(fetched_rates))

        return fetched_rates
