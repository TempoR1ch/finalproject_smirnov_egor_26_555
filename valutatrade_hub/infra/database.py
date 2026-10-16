"""Работа с JSON-файлами приложения."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from valutatrade_hub.infra.settings import BASE_DIR


class DatabaseManager:
    """Единая точка доступа к JSON-хранилищу по паттерну Singleton."""

    _instance: "DatabaseManager | None" = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def _resolve_path(file_path: str | Path) -> Path:
        """Преобразует путь к файлу в абсолютный."""
        path = Path(file_path)
        if not path.is_absolute():
            path = BASE_DIR / path
        return path

    def read_json(
        self,
        file_path: str | Path,
        default: Any = None,
    ) -> Any:
        """Читает JSON и возвращает значение по умолчанию, если файла нет."""
        path = self._resolve_path(file_path)

        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            return default

    def write_json(
        self,
        file_path: str | Path,
        data: Any,
    ) -> None:
        """Атомарно записывает данные в JSON-файл."""
        path = self._resolve_path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        temporary_path: str | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                suffix=".tmp",
                delete=False,
            ) as file:
                temporary_path = file.name
                json.dump(data, file, ensure_ascii=False, indent=4)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())

            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None and os.path.exists(temporary_path):
                os.unlink(temporary_path)
