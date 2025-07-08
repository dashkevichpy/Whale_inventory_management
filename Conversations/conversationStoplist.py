"""Conversation flow for managing stop list."""

from __future__ import annotations

import os
from enum import Enum
from typing import Union, TYPE_CHECKING

from aiogram import Router
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dotenv import load_dotenv

from decorators import check_group
from keyboards import (
    BUTTON_CANCEL_CONVERSATION,
    BUTTON_STOP_START,
    keyboard_cancel_conversation,
    keyboard_from_list,
)

if TYPE_CHECKING:
    from class_StartKeyboard import Employee
from postgres import (
    pg_add_stop_list,
    pg_get_nomenclature_to_stop_list,
    pg_get_stop_list,
    pg_remove_stop_list,
)

load_dotenv()
TG_GROUP_NAMES = eval(os.getenv("TG_GROUP_NAMES", "{}"))
STOPS_TG = os.getenv("STOPS_TG", "")


router = Router()


class StopListState(StatesGroup):
    """Conversation states for stop list."""

    dispatch = State()
    add = State()
    remove = State()


class StopAction(Enum):
    """Available actions in stop list dialog."""

    ADD = ("добавить STOP", "add")
    REMOVE = ("снять со STOP", "remove")

    def __init__(self, text: str, callback: str) -> None:
        self.text = text
        self.callback = callback



def keyboard_stop_actions(has_remove: bool) -> InlineKeyboardMarkup:
    """Return keyboard with available stop list actions."""

    keyboard = [[InlineKeyboardButton(StopAction.ADD.text, callback_data=StopAction.ADD.callback)]]
    if has_remove:
        keyboard.append([InlineKeyboardButton(StopAction.REMOVE.text, callback_data=StopAction.REMOVE.callback)])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def _to_dispatch(message: Message, state: FSMContext, info: str | None = None) -> None:
    """Show dispatch menu with optional info message."""

    data = await state.get_data()
    employee: Employee = data["employee"]
    stop_list = pg_get_stop_list(employee.id_store)
    text = "Выберите действие:"
    if info:
        text = f"{info}\n{text}"
    await message.edit_text(text=text, reply_markup=keyboard_stop_actions(bool(stop_list)))
    await state.set_state(StopListState.dispatch)


async def _cancel_reply(sender: Union[Message, CallbackQuery], state: FSMContext) -> None:
    """Return to start menu and clear state."""

    from class_StartKeyboard import keyboard_start

    send: Message
    if isinstance(sender, CallbackQuery):
        await sender.answer()
        send = sender.message
    else:
        send = sender

    await send.answer(
        text="Вернулись в стартовое меню",
        reply_markup=await keyboard_start(send.chat.id, state),
    )
    await state.clear()


@router.message(F.text == BUTTON_STOP_START)
@check_group
async def stoplist_start(message: Message, state: FSMContext) -> None:
    """Entry point for stop list actions."""

    from class_StartKeyboard import keyboard_start

    await state.update_data(id_user_chat=message.chat.id)
    data = await state.get_data()
    employee: Employee | None = data.get("employee")
    if not employee:
        await message.answer(
            text="Сначала выбери точку, где работаешь",
            reply_markup=await keyboard_start(message.chat.id, state),
        )
        await state.clear()
        return

    stop_list = pg_get_stop_list(employee.id_store)
    await message.answer(text="Выбрали 🛑STOP", reply_markup=keyboard_cancel_conversation())
    await message.answer(
        text="Выберите действие:",
        reply_markup=keyboard_stop_actions(bool(stop_list)),
    )
    await state.set_state(StopListState.dispatch)


@router.callback_query(StopListState.dispatch, F.data == StopAction.ADD.callback)
async def stoplist_add(query: CallbackQuery, state: FSMContext) -> None:
    """Show available items to add to stop list."""

    data = await state.get_data()
    employee: Employee = data["employee"]
    items = pg_get_nomenclature_to_stop_list(employee.id_store)
    if not items:
        await query.answer(text="Нечего добавлять", show_alert=True)
        await _to_dispatch(query.message, state)
        return

    await query.message.edit_text(
        text="Что ставим на стоп?",
        reply_markup=keyboard_from_list(items, 2),
    )
    await state.set_state(StopListState.add)


@router.callback_query(StopListState.dispatch, F.data == StopAction.REMOVE.callback)
async def stoplist_remove(query: CallbackQuery, state: FSMContext) -> None:
    """Show active stop list for removal."""

    data = await state.get_data()
    employee: Employee = data["employee"]
    items = pg_get_stop_list(employee.id_store)
    if not items:
        await query.answer(text="Стоп-лист пуст", show_alert=True)
        await _to_dispatch(query.message, state)
        return

    await query.message.edit_text(
        text="Что снимаем со стопа?",
        reply_markup=keyboard_from_list(items, 2),
    )
    await state.set_state(StopListState.remove)


@router.callback_query(StopListState.add)
async def stoplist_add_select(query: CallbackQuery, state: FSMContext) -> None:
    """Add selected item to stop list."""

    data = await state.get_data()
    employee: Employee = data["employee"]
    nomenclature = query.data
    pg_add_stop_list(employee.id_store, nomenclature)
    await query.bot.send_message(
        chat_id=TG_GROUP_NAMES.get(STOPS_TG, ""),
        text=f"➕⛔ {nomenclature} в {employee.store_name}",
    )
    await _to_dispatch(query.message, state, info=f"Добавили {nomenclature}")


@router.callback_query(StopListState.remove)
async def stoplist_remove_select(query: CallbackQuery, state: FSMContext) -> None:
    """Remove selected item from stop list."""

    data = await state.get_data()
    employee: Employee = data["employee"]
    nomenclature = query.data
    pg_remove_stop_list(employee.id_store, nomenclature)
    await query.bot.send_message(
        chat_id=TG_GROUP_NAMES.get(STOPS_TG, ""),
        text=f"➖⛔ {nomenclature} в {employee.store_name}",
    )
    await _to_dispatch(query.message, state, info=f"Сняли {nomenclature}")


@router.message(F.text == BUTTON_CANCEL_CONVERSATION)
async def stoplist_cancel_message(message: Message, state: FSMContext) -> None:
    """Cancel stop list dialog via message."""

    await _cancel_reply(message, state)


@router.callback_query(F.data == BUTTON_CANCEL_CONVERSATION)
async def stoplist_cancel_callback(query: CallbackQuery, state: FSMContext) -> None:
    """Cancel stop list dialog via callback."""

    await _cancel_reply(query, state)


def conversation_stoplist() -> Router:
    """Return router with stop list handlers."""

    return router