"""Reusable decorators for aiogram handlers."""

from functools import wraps
from typing import Any, Awaitable, Callable

from aiogram.types import Message


def check_group(handler: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    """Prevent handler execution in group chats."""

    @wraps(handler)
    async def wrapper(message: Message, *args: Any, **kwargs: Any) -> Any:
        if message.chat.type in {"group", "supergroup"}:
            await message.answer("Команды в группе не принимаются")
            return None
        return await handler(message, *args, **kwargs)

    return wrapper