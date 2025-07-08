"""Conversation flow for choosing a working store."""

import logging
import os
from typing import Optional

import numpy as np
from aiogram import Router
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from dotenv import load_dotenv

from class_StartKeyboard import keyboard_start
from decorators import check_group
from keyboards import BUTTON_WHAT_WHALE, keyboard_from_list
from postgres import get_stores_open, pg_del_employee_from_store, query_postgre

load_dotenv()
CHAT_TIMEOUT = int(os.getenv("CHAT_TIMEOUT"))

router = Router()


class ChooseWhaleState(StatesGroup):
    """States for choosing a store."""

    assign_whale = State()


async def reset_store_employee(
    message: Message, state: Optional[FSMContext] = None
) -> None:
    """Clear store assignment for user."""
    logging.debug("reset_store_employee for %s", message.from_user.id)

    id_employee = pg_del_employee_from_store(message.chat.id)
    if id_employee:
        text = (
            f"Сбросили текущую точку,\n{BUTTON_WHAT_WHALE} - чтобы выбрать новую"
        )
    else:
        text = "Пожалуйста, выбери где сегодня работаешь"

    await message.answer(text=text, reply_markup=await keyboard_start(message.chat.id, state))


@router.message(F.text == BUTTON_WHAT_WHALE)
@check_group
async def choose_whale_start(message: Message, state: FSMContext) -> None:
    """Send store list to user."""
    logging.debug("choose_whale_start from %s", message.from_user.id)

    stores = np.array(get_stores_open("store_name")).flatten()
    sent = await message.answer(
        text="Выбери точку:",
        reply_markup=keyboard_from_list(stores, 2),
    )
    await state.update_data(
        id_user_chat=message.chat.id, id_message_to_delete=sent.message_id
    )
    await state.set_state(ChooseWhaleState.assign_whale)


@router.callback_query(ChooseWhaleState.assign_whale)
async def assign_whale(query: CallbackQuery, state: FSMContext) -> None:
    """Assign user to selected store."""
    logging.debug("assign_whale %s", query.data)

    whale = query.data
    data = await state.get_data()
    query_db = f"""
        INSERT INTO employee_in_store (id_store, chat_id_telegram)
            SELECT store.id_store, '{data['id_user_chat']}'
            FROM store
            WHERE store.store_name = '{whale}'
    """
    query_postgre(query_db)
    try:
        await query.bot.delete_message(
            chat_id=data["id_user_chat"], message_id=data["id_message_to_delete"]
        )
    except Exception as exc:
        logging.error("Failed to delete choose message: %s", exc)
    await query.message.answer(
        text=f"Выбрали {whale}",
        reply_markup=await keyboard_start(data["id_user_chat"], state),
    )
    await state.clear()


async def timeout_callback_choose_whale(
    query: CallbackQuery, state: FSMContext
) -> None:
    """Notify user about timeout for callback event."""
    logging.debug("timeout_callback_choose_whale")

    data = await state.get_data()
    try:
        await query.bot.delete_message(
            chat_id=data["id_user_chat"], message_id=data["id_message_to_delete"]
        )
    except Exception as exc:
        logging.error("Failed to delete timeout message: %s", exc)
    await query.message.answer(
        text="Прервали выбор точки - не было активностей",
        reply_markup=await keyboard_start(data["id_user_chat"], state),
    )
    await state.clear()


async def timeout_message_choose_whale(
    message: Message, state: FSMContext
) -> None:
    """Notify user about timeout for message event."""
    logging.debug("timeout_message_choose_whale")

    data = await state.get_data()
    try:
        await message.bot.delete_message(
            chat_id=data["id_user_chat"], message_id=data["id_message_to_delete"]
        )
    except Exception as exc:
        logging.error("Failed to delete timeout message: %s", exc)
    await message.answer(
        text="Прервали выбор точки - не было активностей",
        reply_markup=await keyboard_start(data["id_user_chat"], state),
    )
    await state.clear()


async def choose_whale_cancel(
    message: Message | CallbackQuery, state: FSMContext
) -> None:
    """Cancel choosing process."""
    logging.debug("choose_whale_cancel")

    data = await state.get_data()
    try:
        await message.bot.delete_message(
            chat_id=data["id_user_chat"], message_id=data["id_message_to_delete"]
        )
    except Exception as exc:
        logging.error("Failed to delete cancel message: %s", exc)

    send: Message
    if isinstance(message, CallbackQuery):
        send = message.message
        await message.answer()
    else:
        send = message

    await send.answer(
        text="Стартовое меню",
        reply_markup=await keyboard_start(data["id_user_chat"], state),
    )
    await state.clear()


def conversation_choose_whale(dispatcher: object | None = None) -> Router:
    """Return router with choose whale handlers."""
    logging.debug("conversation_choose_whale")
    return router

    return router