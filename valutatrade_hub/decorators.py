"""Декораторы для логирования операций приложения."""

import inspect
import logging
from collections.abc import Callable
from functools import wraps
from time import perf_counter
from typing import Any

from valutatrade_hub.infra.settings import DEFAULT_BASE_CURRENCY

logger = logging.getLogger(__name__)


def _get_log_context(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Извлекает контекст операции для логирования."""
    try:
        bound = inspect.signature(func).bind_partial(*args, **kwargs)
        arguments = bound.arguments
    except (TypeError, ValueError):
        arguments = kwargs.copy()

    return {
        "action": func.__name__.upper(),
        "user_id": arguments.get("user_id", "-"),
        "username": arguments.get("username", "-"),
        "currency_code": arguments.get("currency_code", "-"),
        "amount": arguments.get("amount", "-"),
        "base": arguments.get("base_currency", "-"),
    }


def _get_wallet_balance(
    args: tuple[Any, ...],
    context: dict[str, Any],
) -> float | None:
    """Получает баланс кошелька для подробного логирования."""
    if not args or context["user_id"] == "-":
        return None

    instance = args[0]
    currency_code = context["currency_code"]

    if not isinstance(currency_code, str) or currency_code == "-":
        return None

    portfolios = getattr(instance, "portfolios", instance)
    get_portfolio = getattr(portfolios, "get_portfolio", None)

    if not callable(get_portfolio):
        return None

    try:
        portfolio = get_portfolio(int(context["user_id"]))
        wallets = getattr(portfolio, "wallets", {})
        wallet = wallets.get(currency_code.strip().upper())
        return wallet.balance if wallet is not None else 0.0
    except (ValueError, TypeError, KeyError, AttributeError):
        logger.debug("Не удалось получить баланс для логирования", exc_info=True)
        return None


def log_action(
    func: Callable[..., Any] | None = None,
    *,
    verbose: bool = False,
) -> Callable[..., Any]:
    """Логирует параметры, результат и ошибки операции."""

    def decorator(target: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(target)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            context = _get_log_context(target, args, kwargs)
            before_balance = _get_wallet_balance(args, context) if verbose else None

            try:
                result = target(*args, **kwargs)
            except Exception as error:
                logger.exception(
                    "action=%s username=%s user_id=%s "
                    "currency_code=%s amount=%s base=%s "
                    "result=ERROR error_type=%s error_message=%r",
                    context["action"],
                    context["username"],
                    context["user_id"],
                    context["currency_code"],
                    context["amount"],
                    context["base"],
                    type(error).__name__,
                    str(error),
                )
                raise

            fields = [
                f"action={context['action']}",
                f"username={context['username']}",
                f"user_id={context['user_id']}",
                f"currency_code={context['currency_code']}",
                f"amount={context['amount']}",
            ]

            if context["base"] != "-":
                fields.append(f"base={context['base']}")

            if (
                context["action"] == "SELL"
                and isinstance(result, (int, float))
                and not isinstance(result, bool)
                and isinstance(context["amount"], (int, float))
                and not isinstance(context["amount"], bool)
                and context["amount"] > 0
            ):
                fields.append(f"rate={result / context['amount']:.8g}")
                fields.append(f"base={DEFAULT_BASE_CURRENCY}")
                fields.append(f"proceeds={result:.8g}")

            fields.append("result=OK")

            if verbose:
                after_balance = _get_wallet_balance(args, context)
                if before_balance is not None or after_balance is not None:
                    fields.append(f"balance_before={before_balance!r}")
                    fields.append(f"balance_after={after_balance!r}")

            logger.info("%s", " ".join(fields))
            return result

        return wrapper

    if func is not None:
        return decorator(func)

    return decorator


def measure_time(func: Callable[..., Any]) -> Callable[..., Any]:
    """Измеряет время выполнения функции."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = perf_counter()

        try:
            return func(*args, **kwargs)
        finally:
            elapsed = perf_counter() - start
            logger.info(
                "action=%s duration_seconds=%.4f",
                func.__name__.upper(),
                elapsed,
            )

    return wrapper
