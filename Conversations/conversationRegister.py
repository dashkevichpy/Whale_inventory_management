
"""Conversation flow for employee registration."""

from __future__ import annotations

from typing import Union
import logging

from aiogram import Router
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message


from class_StartKeyboard import keyboard_start
from decorators import check_group
from keyboards import (
    BUTTON_CANCEL_CONVERSATION,
    BUTTON_REGISTER,
    keyboard_cancel_conversation,
    keyboard_from_list,
)
from postgres import pg_get_department, pg_get_position_by_dept, pg_insert_new_employee


router = Router()


class RegisterState(StatesGroup):
    """Conversation states for registration."""

    department = State()
    position = State()


@router.message(F.text == BUTTON_REGISTER)
@check_group
async def register_start(message: Message, state: FSMContext) -> None:
    """Start registration and ask for employee department."""
    logging.debug("register_start from %s", message.from_user.id)

    departments = pg_get_department()
    await message.answer(
        text="Привет! 👋 давай знакомиться",
        reply_markup=keyboard_cancel_conversation(),
    )
    sent = await message.answer(
        text="Где ты работаешь?",
        reply_markup=keyboard_from_list(departments, 2),
    )
    await state.update_data(
        id_user_chat=message.chat.id, id_message_to_delete=sent.message_id
    )
    await state.set_state(RegisterState.department)


@router.callback_query(RegisterState.department)
async def register_choose_position(query: CallbackQuery, state: FSMContext) -> None:
    """Send job titles for selected department."""
    logging.debug("register_choose_position: %s", query.data)

    department = query.data
    await state.update_data(department=department)
    positions = pg_get_position_by_dept(department)
    await query.message.edit_text(
        text=f"Выбрали {department}\nдальше - должность?",
        reply_markup=keyboard_from_list(positions, 1),
    )
    await state.set_state(RegisterState.position)


@router.callback_query(RegisterState.position)
async def register_finish(query: CallbackQuery, state: FSMContext) -> None:
    """Save employee information and show start menu."""
    logging.debug("register_finish: %s", query.data)

    position = query.data
    await query.message.edit_text(
        text=f"Спасибо! Записались должность - {position}",
    )
    pg_insert_new_employee(
        query.message.chat.id,
        position,
        query.from_user.first_name or "",
        query.from_user.last_name or "",
        query.from_user.username or "",
    )
    await query.message.answer(
        text="Вернулись в стартовое меню",
        reply_markup=await keyboard_start(query.message.chat.id, state),
    )
    await state.clear()


async def register_cancel(
    message: Union[Message, CallbackQuery], state: FSMContext
) -> None:
    """Cancel registration and return to start menu."""
    logging.debug("register_cancel")

    data = await state.get_data()
    try:
        await message.bot.delete_message(
            chat_id=data.get("id_user_chat"),
            message_id=data.get("id_message_to_delete"),
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
        text="Вернулись в cтартовое меню",
        reply_markup=await keyboard_start(send.chat.id, state),
    )
    await state.clear()


@router.message(F.text == BUTTON_CANCEL_CONVERSATION)
async def register_cancel_message(message: Message, state: FSMContext) -> None:
    """Cancel registration via text button."""

    await register_cancel(message, state)


def conversation_register() -> Router:
    """Return router with registration handlers."""

    return router
