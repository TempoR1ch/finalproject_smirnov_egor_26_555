"""Обновление и сохранение валютных курсов."""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import (
    EXCHANGE_RATES_PATH,
    RATES_PATH,
)

logger = logging.getLogger(__name__)


class RatesUpdater:
    """Получает валютные курсы и сохраняет текущие значения и историю."""

    def __init__(
        self,
        coingecko_client: CoinGeckoClient | None = None,
        exchange_rate_client: ExchangeRateApiClient | None = None,
        database: DatabaseManager | None = None,
    ) -> None:
        self.coingecko_client = coingecko_client or CoinGeckoClient()
        self.exchange_rate_client = (
            exchange_rate_client or ExchangeRateApiClient()
        )
        self.database = database or DatabaseManager()

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
                logger.warning("Не удалось получить курсы %s: %s", source, error)
                continue

            fetched_rates.update(rates)

            for pair in rates:
                sources[pair] = source

        if not fetched_rates:
            raise ApiRequestError(
                "Не удалось обновить курсы ни из одного источника."
            )

        updated_at = datetime.now(timezone.utc).isoformat()

        current_data = self.database.read_json(RATES_PATH, default={})
        if not isinstance(current_data, dict):
            current_data = {}

        current_pairs = current_data.get("pairs", {})
        if not isinstance(current_pairs, dict):
            current_pairs = {}

        for pair, rate in fetched_rates.items():
            current_pairs[pair] = {
                "rate": rate,
                "updated_at": updated_at,
                "source": sources[pair],
            }

        current_data["pairs"] = current_pairs
        current_data["last_refresh"] = updated_at

        history = self.database.read_json(
            EXCHANGE_RATES_PATH,
            default=[],
        )
        if not isinstance(history, list):
            history = []

        for pair, rate in fetched_rates.items():
            from_currency, to_currency = pair.split("_", maxsplit=1)

            history.append(
                {
                    "id": str(uuid4()),
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "rate": rate,
                    "timestamp": updated_at,
                    "source": sources[pair],
                }
            )

        self.database.write_json(RATES_PATH, current_data)
        self.database.write_json(EXCHANGE_RATES_PATH, history)

        logger.info("Обновлено валютных пар: %s", len(fetched_rates))

        return fetched_rates