# ValutaTrade Hub

Консольная платформа для отслеживания валютных курсов и симуляции торговли фиатными и криптовалютами.

## Возможности

- Регистрация пользователей и вход в систему.
- Управление виртуальным валютным портфелем.
- Добавление валютных кошельков и пополнение баланса.
- Покупка и продажа валюты за USD.
- Получение и обновление курсов через внешние API.
- Просмотр сохранённых курсов с фильтрацией.
- Хранение данных в JSON-файлах.
- Логирование действий и обработка ошибок.

## Технологии

- Python 3.12+
- uv — управление зависимостями и запуск проекта.
- Requests — HTTP-запросы к внешним API.
- PrettyTable — форматирование таблиц в консоли.
- JSON — хранение данных.

## Установка и запуск

Клонируйте репозиторий:

```bash
git clone https://github.com/TempoR1ch/finalproject_smirnov_egor_26_555.git
cd finalproject_smirnov_egor_26_555
```

Установите зависимости:

```bash
uv sync
```

Запустите приложение:

```bash
uv run python main.py
```

## Команды

### Регистрация и вход

```text
register --username <имя> --password <пароль>
login --username <имя> --password <пароль>
```

### Портфель

```text
show-portfolio
show-portfolio --base EUR
add-currency --currency BTC
deposit --currency USD --amount 1000
```

### Торговля

```text
buy --currency BTC --amount 0.01
sell --currency BTC --amount 0.01
```

Покупка и продажа выполняются за USD. Для операций нужны сохранённые курсы и достаточный баланс.

### Валютные курсы

```text
get-rate --from USD --to EUR
update-rates
update-rates --source coingecko
update-rates --source exchangerate
show-rates
show-rates --currency BTC
show-rates --top 5
show-rates --base USD
```

Команда `update-rates` обновляет курсы. Параметр `--source` позволяет выбрать источник: `coingecko` или `exchangerate`.

### Справка и выход

```text
help
exit
```

## Источники курсов

- **CoinGecko** — курсы поддерживаемых криптовалют.
- **ExchangeRate-API** — курсы поддерживаемых фиатных валют.

Для ExchangeRate-API может потребоваться API-ключ в переменной окружения `EXCHANGE_RATE_API_KEY`.

## Хранение данных

Приложение использует JSON-файлы для хранения пользователей, портфелей, текущих курсов и истории обновлений.

## Структура проекта

- `valutatrade_hub/core/` — модели и бизнес-логика.
- `valutatrade_hub/cli/` — консольный интерфейс.
- `valutatrade_hub/parser_service/` — получение и хранение валютных курсов.
- `valutatrade_hub/infra/` — настройки и работа с хранилищем.
- `valutatrade_hub/decorators.py` — логирование и измерение времени выполнения.
- `valutatrade_hub/logging_config.py` — настройка логирования.
- `main.py` — точка входа.
