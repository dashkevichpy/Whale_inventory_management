import numpy as np
from telegram.ext import ConversationHandler, MessageHandler, CallbackQueryHandler, Filters

from class_StartKeyboard import keyboard_start
import os
from dotenv import load_dotenv

load_dotenv()
CHAT_TIMEOUT = int(os.getenv('CHAT_TIMEOUT'))
from decorators import check_group
from keyboards import keyboard_from_list, keyboard_cancel_conversation, BUTTON_CANCEL_CONVERSATION, BUTTON_REGISTER
from postgres import  pg_get_department, pg_get_position_by_dept, pg_insert_new_employee

DEPT_NAME, POSITION_NAME, ID_MESSAGE_TO_DELETE = range(3)
CH_POSTION, WRITE = range(2)  # ch - значит choose - выбирать

@check_group
def register_check_choose_department(update, context):
    department_list = pg_get_department()
    update.message.reply_text(
        text='Привет! 👋 давай знакомиться',
        reply_markup=keyboard_cancel_conversation()
    )
    update.message.reply_text(
        text='Где ты работаешь?',
        reply_markup=keyboard_from_list(department_list, 2)
    )
    context.user_data[ID_MESSAGE_TO_DELETE] = update.message.message_id + 2
    return CH_POSTION


def register_wr_dept_ch_position(update, context):
    query = update.callback_query
    context.user_data[DEPT_NAME] = query.data
    position_list = pg_get_position_by_dept(context.user_data[DEPT_NAME])
    query.edit_message_text(
        text=f'Выбрали {context.user_data[DEPT_NAME]}\nдальше - должность?',
        reply_markup=keyboard_from_list(position_list, 1)
    )
    return WRITE


def register_write(update, context):
    query = update.callback_query
    context.user_data[POSITION_NAME] = query.data
    query.edit_message_text(
        text=f'Спасибо! Записались должность - {context.user_data[POSITION_NAME]}',
        reply_markup=None
    )
    pg_insert_new_employee(update.effective_chat.id,
                           context.user_data[POSITION_NAME],
                           update.effective_user.first_name,
                           update.effective_user.last_name,
                           update.effective_user.username)
    update.effective_message.reply_text(
        text='Вернулись в стартовое меню',
        reply_markup=keyboard_start(update.effective_chat.id, context),
    )
    return ConversationHandler.END


def register_timeout(update, context):
    # context.bot.delete_message(chat_id=update.message.chat.id, message_id=context.user_data[ID_MESSAGE_TO_DELETE])
    # update.message.reply_text(
    #     text='Прервали регистрацию - не было активностей',
    #     reply_markup=keyboard_start(update.message.chat_id, context),
    # )

    chat_id = update.callback_query.message.chat.id
    context.bot.delete_message(chat_id=chat_id, message_id=context.user_data[ID_MESSAGE_TO_DELETE])
    update.effective_message.reply_text(
        text='Прервали регистрацию - не было активностей',
        reply_markup=keyboard_start(chat_id, context),
    )
    return ConversationHandler.END


def register_end(update, context):
    context.bot.delete_message(chat_id=update.message.chat.id, message_id=context.user_data[ID_MESSAGE_TO_DELETE])
    update.message.reply_text(
        text='Вернулись в cтартовое меню',
        reply_markup=keyboard_start(update.message.chat_id, context)
    )
    return ConversationHandler.END




def conversation_register(dispatcher):
    dispatcher.add_handler(ConversationHandler(
        # entry_points=[CommandHandler('register', register_check_choose_department, pass_user_data=True)],
        entry_points=[MessageHandler(Filters.regex(BUTTON_REGISTER), register_check_choose_department, pass_user_data=True)],
        states={
            CH_POSTION: [CallbackQueryHandler(register_wr_dept_ch_position, pass_user_data=True)],
            WRITE: [CallbackQueryHandler(register_write, pass_user_data=True)],
            ConversationHandler.TIMEOUT:[CallbackQueryHandler(register_timeout, pass_job_queue=True, pass_update_queue=True)],
        },
        fallbacks=[MessageHandler(Filters.regex(BUTTON_CANCEL_CONVERSATION), register_end, pass_user_data=True)],
        conversation_timeout=CHAT_TIMEOUT
    ))
"""Conversation flow for employee registration."""

from __future__ import annotations

from typing import Union

from aiogram import Router
from aiogram.filters import Text
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


@router.message(Text(BUTTON_REGISTER))
@check_group
async def register_start(message: Message, state: FSMContext) -> None:
    """Start registration and ask for employee department."""

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


@router.message(Text(BUTTON_CANCEL_CONVERSATION))
async def register_cancel_message(message: Message, state: FSMContext) -> None:
    """Cancel registration via text button."""

    await register_cancel(message, state)


def conversation_register() -> Router:
    """Return router with registration handlers."""

    return router
