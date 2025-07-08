"""Conversation flow for breakage reports."""

from __future__ import annotations

import os
from typing import Any, Dict

import numpy as np
from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from dotenv import load_dotenv

from class_StartKeyboard import keyboard_start
from decorators import check_group
from gSheet import insert_entry_breakages_gs
from keyboards import (
    BUTTON_BREAK_CANCEL,
    BUTTON_BREAK_TITLE,
    keyboard_cancel_breakage,
    keyboard_critical,
    keyboard_from_list,
    keyboard_yes_no,
)
from postgres import get_stores_open, query_postgre

load_dotenv()
CHAT_TIMEOUT = int(os.getenv("CHAT_TIMEOUT"))
BREAKAGES_ENTRY_SHEET_NAME = os.getenv("BREAKAGES_ENTRY_SHEET_NAME")

router = Router()


class BreakageState(StatesGroup):
    """States for breakage conversation."""

    which_whale = State()
    what_broken = State()
    critical = State()
    comment = State()
    confirm = State()


@router.message(Text(BUTTON_BREAK_TITLE))
@check_group
async def broken_start(message: Message, state: FSMContext) -> None:
    """Start breakage input."""

    await state.update_data(
        id_user_chat=message.chat.id,
        user_name=message.from_user.last_name,
        id_message_to_delete=message.message_id + 2,
    )

    store_postgre = np.array(get_stores_open("store_name")).flatten()
    store_postgre = np.insert(store_postgre, 1, "ФК")

    await message.answer(
        text="Выбрали 🛠Поломка",
        reply_markup=keyboard_cancel_breakage(),
    )
    await message.answer(
        text="Выберите место поломки:",
        reply_markup=keyboard_from_list(store_postgre, 2),
    )
    await state.set_state(BreakageState.which_whale)


@router.callback_query(BreakageState.which_whale)
async def broken_what(query: CallbackQuery, state: FSMContext) -> None:
    """Select equipment type."""

    whale = query.data
    await state.update_data(which_whale=whale)

    pg_query = """
        SELECT equiment_type
        FROM breakages
    """
    equiment_type = np.array(query_postgre(pg_query)).flatten()

    await query.message.edit_text(
        text=f"<b>Точка:</b> {whale}\nВыберите тип оборудования",
        reply_markup=keyboard_from_list(equiment_type, 2),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(BreakageState.what_broken)


@router.callback_query(BreakageState.what_broken)
async def broken_is_crit(query: CallbackQuery, state: FSMContext) -> None:
    """Select criticality."""

    what_broken = query.data
    await state.update_data(what_broken=what_broken)

    pg_query = (
        "SELECT telegram_gr FROM breakages WHERE equiment_type = '{}'".format(
            what_broken
        )
    )
    chat_id = str(np.array(query_postgre(pg_query))[0][0])
    await state.update_data(id_tg_chat_report=chat_id)
    data = await state.get_data()

    await query.message.edit_text(
        text=(
            f"<b>Точка:</b> {data['which_whale']}\n"
            f"<b>Оборудование:</b> {what_broken}\n"
            "Дальнейшая работа возможна?:"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_critical(),
    )
    await state.set_state(BreakageState.critical)


@router.callback_query(BreakageState.critical)
async def broken_comment(query: CallbackQuery, state: FSMContext) -> None:
    """Request breakage description."""

    critical = query.data
    await state.update_data(critical=critical)
    data = await state.get_data()

    await query.message.edit_text(
        text=(
            f"<b>Точка:</b> {data['which_whale']}\n"
            f"<b>Оборудование:</b> {data['what_broken']}\n"
            f"<b>Дальнейшая работа возможна?:</b> {critical}\n"
            "Опишите поломку:"
        ),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(BreakageState.comment)


@router.message(BreakageState.comment)
async def broken_check(message: Message, state: FSMContext) -> None:
    """Confirm input data."""

    if message.text == BUTTON_BREAK_CANCEL:
        await broken_cancel(message, state)
        return

    await state.update_data(comment=message.text)
    data = await state.get_data()
    text_message = (
        "Спасибо! Все верно?"
        f"\n\n<b>Точка:</b> {data['which_whale']}"
        f"\n <b>Оборудование:</b> {data['what_broken']}"
        f"\n <b>Критическая:</b> {data['critical']}"
        f"\n <b>Комментарий:</b> {data['comment']}"
    )
    await state.update_data(text_message=text_message)

    await message.answer(
        text=text_message,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_yes_no(),
    )
    await state.set_state(BreakageState.confirm)


@router.callback_query(BreakageState.confirm)
async def broken_finish(query: CallbackQuery, state: FSMContext) -> None:
    """Save breakage report and notify."""

    data = await state.get_data()
    if query.data == "Yes":
        insert_entry_breakages_gs(
            data["id_user_chat"],
            data["which_whale"],
            data["what_broken"],
            data["critical"],
            data["comment"],
            BREAKAGES_ENTRY_SHEET_NAME,
        )
        await query.message.answer(
            text="Спасибо!",
            reply_markup=await keyboard_start(data["id_user_chat"], state),
        )
        await query.bot.send_message(
            chat_id=data["id_tg_chat_report"],
            text=data["text_message"],
            parse_mode=ParseMode.HTML,
        )
    else:
        await query.message.answer(
            text="Сообщение удалено",
            reply_markup=await keyboard_start(data["id_user_chat"], state),
        )
    await state.clear()


async def broken_cancel(message: Message | CallbackQuery, state: FSMContext) -> None:
    """Cancel breakage dialog."""

    data = await state.get_data()
    try:
        await message.bot.delete_message(
            chat_id=data["id_user_chat"],
            message_id=data["id_message_to_delete"],
        )
    except Exception:
        pass

    send: Message
    if isinstance(message, CallbackQuery):
        send = message.message
        await message.answer()
    else:
        send = message

    await send.answer(
        text="Внесение поломки прервано, вернулись в стартовое меню:",
        reply_markup=await keyboard_start(data["id_user_chat"], state),
    )
    await state.clear()


async def timeout_callback_broken(query: CallbackQuery, state: FSMContext) -> None:
    """Notify user about timeout."""

    await query.message.edit_text(
        text="Прервали внесение 🛠 поломки, не было активностей",
    )
    data = await state.get_data()
    await query.message.answer(
        text="Вернулись в стартовое меню",
        reply_markup=await keyboard_start(data["id_user_chat"], state),
    )
    await state.clear()


async def timeout_message_broken(message: Message, state: FSMContext) -> None:
    """Timeout for message event."""

    data = await state.get_data()
    await message.answer(
        text="Прервали внесение 🛠 поломки, не было активностей",
        reply_markup=await keyboard_start(data["id_user_chat"], state),
    )
    await state.clear()


def add_observer_broken() -> Router:
    """Return router with breakage conversation handlers."""

    return router