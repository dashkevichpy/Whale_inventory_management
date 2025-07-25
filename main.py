"""Entry point for the whale management bot."""

import asyncio
import logging
import os

# use test mode to skip database writes
os.environ.setdefault("TEST_MODE", "true")

from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from dotenv import load_dotenv

from class_StartKeyboard import keyboard_start
from logging_config import setup_logging
from decorators import check_group
from Conversations.conversationChooseWhale import (
    conversation_choose_whale,
    reset_store_employee,
)
from Conversations.conversationRegister import conversation_register
from Conversations.conversationStoplist import conversation_stoplist
from Conversations.conversationStocks import conversation_stocks
from Conversations.conversationTransfer import conversation_transfer
from Conversations.conversationBreak import add_observer_broken
from Conversations.conversationWaiting import conversation_waiting
from Conversations.conversationErrors import conversation_errors
from Conversations.conversationDeliveryWaiting import conversation_delivery_waiting
from postgres import log_tables_structure

load_dotenv()
TOKEN = os.getenv("TG_TOKEN")

router = Router()


@router.message(CommandStart())
@check_group
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Send greeting and start keyboard."""
    logging.debug("cmd_start from %s", message.from_user.id)
    await message.answer(
        text=f"Привет, {message.from_user.first_name}!",
        reply_markup=await keyboard_start(message.chat.id, state),
    )


@router.message(Command("reset_store"))
@check_group
async def cmd_reset_store(message: Message, state: FSMContext) -> None:
    """Reset employee store choice."""
    logging.debug("cmd_reset_store from %s", message.from_user.id)
    await reset_store_employee(message, state)


@router.message(Command("tab"))
@check_group
async def cmd_tab(message: Message) -> None:
    """Log database table structures."""

    await message.answer("Смотрим логи")
    log_tables_structure()


async def main() -> None:
    """Run bot polling."""
    logging.debug("Starting bot")
    if not TOKEN:
        raise RuntimeError("TG_TOKEN not set")

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    dp.include_router(conversation_choose_whale())
    dp.include_router(conversation_register())
    dp.include_router(conversation_stoplist())
    dp.include_router(conversation_stocks())
    dp.include_router(conversation_transfer())
    dp.include_router(add_observer_broken())
    dp.include_router(conversation_waiting())
    dp.include_router(conversation_errors())
    dp.include_router(conversation_delivery_waiting())


    bot = Bot(
        TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await dp.start_polling(bot)



if __name__ == "__main__":
    setup_logging()
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass