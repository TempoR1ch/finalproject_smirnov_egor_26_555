"""Хранение текущих валютных курсов и истории обновлений."""

from datetime import datetime, timezone

from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.parser_service.config import (
    EXCHANGE_RATES_PATH,
    RATES_PATH,
)


class RatesStorage:
    """Сохраняет текущие курсы и историю изменений в JSON."""

    def __init__(self, database: DatabaseManager | None = None) -> None:
        self.database = database or DatabaseManager()

    def get_current_rates(self) -> dict:
        """Возвращает сохранённые текущие курсы."""
        data = self.database.read_json(RATES_PATH, default={})

        if not isinstance(data, dict):
            return {}

        return data

    def save_current_rates(
        self,
        rates: dict[str, float],
        sources: dict[str, str],
    ) -> None:
        """Сохраняет текущие курсы, не удаляя остальные валютные пары."""
        data = self.get_current_rates()
        pairs = data.get("pairs", {})

        if not isinstance(pairs, dict):
            pairs = {}

        updated_at = datetime.now(timezone.utc).isoformat()

        for pair, rate in rates.items():
            pairs[pair] = {
                "rate": rate,
                "updated_at": updated_at,
                "source": sources[pair],
            }

        data["pairs"] = pairs
        data["last_refresh"] = updated_at

        self.database.write_json(RATES_PATH, data)

    def append_history(
        self,
        rates: dict[str, float],
        sources: dict[str, str],
    ) -> None:
        """Добавляет полученные курсы в историю обновлений."""
        history = self.database.read_json(
            EXCHANGE_RATES_PATH,
            default=[],
        )

        if not isinstance(history, list):
            history = []

        existing_ids = {
            record["id"]
            for record in history
            if isinstance(record, dict) and isinstance(record.get("id"), str)
        }

        for pair, rate in rates.items():
            from_currency, to_currency = pair.split("_", maxsplit=1)
            timestamp_dt = datetime.now(timezone.utc)
            timestamp = timestamp_dt.isoformat(timespec="microseconds").replace(
                "+00:00", "Z"
            )
            timestamp_id = timestamp

            record_id = f"{from_currency}_{to_currency}_{timestamp_id}"
            suffix = 1

            while record_id in existing_ids:
                record_id = f"{from_currency}_{to_currency}_{timestamp_id}_{suffix}"
                suffix += 1

            existing_ids.add(record_id)

            history.append(
                {
                    "id": record_id,
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "rate": rate,
                    "timestamp": timestamp,
                    "source": sources[pair],
                }
            )

        self.database.write_json(EXCHANGE_RATES_PATH, history)
