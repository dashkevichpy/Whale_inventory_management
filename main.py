"""Entry point for the whale management bot."""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from dotenv import load_dotenv

from class_StartKeyboard import keyboard_start
from decorators import check_group
from Conversations.conversationChooseWhale import (
    conversation_choose_whale,
    reset_store_employee,
)

load_dotenv()
TOKEN = os.getenv("TG_TOKEN")

router = Router()


@router.message(CommandStart())
@check_group
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Send greeting and start keyboard."""
    await message.answer(
        text=f"Привет, {message.from_user.first_name}!",
        reply_markup=await keyboard_start(message.chat.id, state),
    )


@router.message(Command("reset_store"))
@check_group
async def cmd_reset_store(message: Message, state: FSMContext) -> None:
    """Reset employee store choice."""
    await reset_store_employee(message, state)


async def main() -> None:
    """Run bot polling."""
    if not TOKEN:
        raise RuntimeError("TG_TOKEN not set")

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    dp.include_router(conversation_choose_whale())

    bot = Bot(TOKEN, parse_mode=ParseMode.HTML)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass