"""Conversation flow for recording employee errors."""

from __future__ import annotations

import logging
import os
from typing import Optional

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
from gSheet import insert_entry_errors_gs
from keyboards import (
    BUTTON_ERROR_CANCEL,
    BUTTON_ERROR_TITLE,
    keyboard_accept_read,
    keyboard_cancel_error,
    keyboard_from_list,
    keyboard_yes_no,
)
from postgres import get_stores_open, query_postgre

load_dotenv()
CHAT_TIMEOUT = int(os.getenv("CHAT_TIMEOUT"))
ERROR_ADMIN_ID = os.getenv("ERROR_ADMIN_ID")

PHOTO_ERROR_TYPE = [
    "Качество заготовок",
    "документы Корниенко",
    "документы GH",
]

router = Router()


class ErrorState(StatesGroup):
    """States for error conversation."""

    which_post = State()
    what_error = State()
    what_location = State()
    date_error = State()
    detail_comment = State()
    add_photo = State()
    get_photo = State()
    confirm = State()


@router.message(Text(BUTTON_ERROR_TITLE))
@check_group
async def error_start(message: Message, state: FSMContext) -> None:
    """Start error input flow."""

    await state.update_data(
        id_user_chat=message.chat.id,
        user_name=message.from_user.username,
        photo_file_id=None,
        id_message_to_delete=message.message_id + 2,
    )

    query_db = """
        SELECT department_name
        FROM errors_departments;
    """
    department = np.array(query_postgre(query_db)).flatten()

    await message.answer(
        text="<b> Выбрали: </b> 📯Ошибка",
        reply_markup=keyboard_cancel_error(),
        parse_mode=ParseMode.HTML,
    )
    await message.answer(
        text="Кто ошибся?",
        reply_markup=keyboard_from_list(department, 2),
    )
    await state.set_state(ErrorState.which_post)


@router.callback_query(ErrorState.which_post)
async def error_type(query: CallbackQuery, state: FSMContext) -> None:
    """Select error type."""

    await state.update_data(which_post=query.data)

    query_db = f"""
        SELECT error_name, group_telegram_id, personal_telegram_id
        FROM error_types
        INNER JOIN errors_departments USING(id_errors_categories)
        WHERE department_name = '{query.data}';
    """
    type_error = np.array(query_postgre(query_db))

    try:
        await state.update_data(
            chat_id_not1=type_error[0, 1],
            chat_id_not2=type_error[0, 2],
        )
    except Exception as exc:  # pragma: no cover - just logging
        logging.info("type_error parse fail %s %s", type_error, exc)
        await error_cancel(query, state)
        return

    await query.message.edit_text(
        text=f"<b>Ошиблись:</b> {query.data}\nТип ошибки:",
        reply_markup=keyboard_from_list(type_error[:, 0].flatten(), 2),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(ErrorState.what_error)


@router.callback_query(ErrorState.what_error)
async def error_location(query: CallbackQuery, state: FSMContext) -> None:
    """Select store where error occurred."""

    await state.update_data(what_error=query.data)
    stores = np.array(get_stores_open("store_name")).flatten()
    stores = np.insert(stores, len(stores), "B2B")
    data = await state.get_data()

    await query.message.edit_text(
        text=(
            f"<b>Ошиблись: </b>{data['which_post']}\n"
            f"<b>Тип ошибки: </b>{data['what_error']}\n\n"
            "Точка: "
        ),
        reply_markup=keyboard_from_list(stores, 2),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(ErrorState.what_location)


@router.callback_query(ErrorState.what_location)
async def error_date_time(query: CallbackQuery, state: FSMContext) -> None:
    """Request date and time of the error."""

    await state.update_data(what_location=query.data)
    data = await state.get_data()

    await query.message.edit_text(
        text=(
            f"<b>Ошиблись:  </b>{data['which_post']}\n"
            f"<b>Тип ошибки:  </b>{data['what_error']}\n"
            f"<b>Точка:  </b>{data['what_location']}\n\n"
            "Укажите дату / время ошибки, номер заказа: "
        ),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(ErrorState.date_error)


@router.message(ErrorState.date_error)
async def error_comment(message: Message, state: FSMContext) -> None:
    """Ask for detailed error description."""

    if message.text == BUTTON_ERROR_CANCEL:
        await error_cancel(message, state)
        return

    await state.update_data(date_error=message.text)
    data = await state.get_data()

    await message.answer(
        text=(
            f"<b>Ошиблись:</b> {data['which_post']}\n"
            f"<b>Тип ошибки:</b> {data['what_error']}\n"
            f"<b>Точка:</b> {data['what_location']}\n"
            f"<b>Дату / время ошибки, номер заказа:</b> {data['date_error']}\n\n"
            "<b>Комментарии к ошибке </b>"
        ),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(ErrorState.detail_comment)


@router.message(ErrorState.detail_comment)
async def error_check(message: Message, state: FSMContext) -> None:
    """Confirm collected data or ask for photo."""

    await state.update_data(detail_comment=message.text)
    data = await state.get_data()

    if data["what_error"] in PHOTO_ERROR_TYPE and not data.get("photo_file_id"):
        await message.answer(
            text="📷 Фото прикрепим?",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard_yes_no(),
        )
        await state.set_state(ErrorState.add_photo)
        return

    await message.answer(
        text=(
            "Спасибо! Все верно?\n\n"
            f"<b>Должность:</b> {data['which_post']}\n"
            f"<b>Ошибка:</b> {data['what_error']}\n"
            f"<b>Точка:</b> {data['what_location']}\n"
            f"<b>Дата/время:</b> {data['date_error']}\n"
            f"<b>Комментарий:</b> {data['detail_comment']}"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_yes_no(),
    )
    await state.set_state(ErrorState.confirm)


@router.callback_query(ErrorState.add_photo)
async def error_request_photo(query: CallbackQuery, state: FSMContext) -> None:
    """Ask user to send a photo."""

    if query.data == "Yes":
        await query.message.edit_text(text="Можно прямо в бот 📸")
        await state.set_state(ErrorState.get_photo)
        return

    data = await state.get_data()
    await query.message.edit_text(
        text=(
            "Нет, так нет! \nПроверь, что всё верно 👇\n\n"
            f"<b>Должность:</b> {data['which_post']}\n"
            f"<b>Ошибка:</b> {data['what_error']}\n"
            f"<b>Точка:</b> {data['what_location']}\n"
            f"<b>Дата/время:</b> {data['date_error']}\n"
            f"<b>Комментарий:</b> {data['detail_comment']}"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_yes_no(),
    )
    await state.set_state(ErrorState.confirm)


@router.message(ErrorState.get_photo)
async def error_receive_photo(message: Message, state: FSMContext) -> None:
    """Receive photo from user."""

    if not message.photo:
        await message.answer("😓 это не фото, а надо фото. Ещё разок")
        return

    await state.update_data(photo_file_id=message.photo[-1].file_id)
    data = await state.get_data()

    await message.answer(
        text=(
            "Спасибо! Все верно?\n\n"
            f"<b>Должность:</b> {data['which_post']}\n"
            f"<b>Ошибка:</b> {data['what_error']}\n"
            f"<b>Точка:</b> {data['what_location']}\n"
            f"<b>Дата/время:</b> {data['date_error']}\n"
            f"<b>Комментарий:</b> {data['detail_comment']}"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_yes_no(),
    )
    await state.set_state(ErrorState.confirm)


@router.callback_query(ErrorState.confirm)
async def error_finish(query: CallbackQuery, state: FSMContext) -> None:
    """Write data to sheet and notify."""

    data = await state.get_data()
    if query.data == "Yes":
        try:
            insert_entry_errors_gs(
                data["id_user_chat"],
                data["what_location"],
                data["date_error"],
                data["what_error"],
                data["detail_comment"],
                data["which_post"],
            )
            await query.message.answer(
                text="Спасибо!",
                reply_markup=await keyboard_start(data["id_user_chat"], state),
            )
            text = (
                "Ошибка:"\
                f"\n\nДолжность: {data['which_post']}"\
                f"\n От: {data['user_name']}"\
                f"\n Точка: {data['what_location']}"\
                f"\n Тип ошибки: {data['what_error']}"\
                f"\n Дата ошибки: {data['date_error']}"\
                f"\n Комментарий: {data['detail_comment']}"
            )
            try:
                if data.get("photo_file_id"):
                    await query.bot.send_photo(
                        chat_id=data["chat_id_not1"],
                        caption=text,
                        photo=data["photo_file_id"],
                    )
                else:
                    await query.bot.send_message(
                        chat_id=data["chat_id_not1"],
                        text=text,
                        reply_markup=keyboard_accept_read(),
                    )
            except Exception as exc:  # pragma: no cover - network
                logging.error(
                    "send notify error %s for %s", exc, data["which_post"]
                )
                await query.bot.send_message(
                    chat_id=ERROR_ADMIN_ID,
                    text="ошибка бота ошибок: некорректный ID для отправки сообщений",
                )
        except Exception as exc:  # pragma: no cover - network
            logging.error(
                "insert data to table %s - ошибка %s", data["which_post"], exc
            )
            await query.message.answer(
                text="Возникла ошибка! Сообщите о ней",
                reply_markup=await keyboard_start(data["id_user_chat"], state),
            )
            await query.bot.send_message(
                chat_id=ERROR_ADMIN_ID,
                text=f"Ошибка при внесении замечания {data['which_post']} - {exc}",
            )
    else:
        await query.message.answer(
            text="Сообщение удалено",
            reply_markup=await keyboard_start(data["id_user_chat"], state),
        )
    await state.clear()


async def error_cancel(
    message: Message | CallbackQuery, state: FSMContext
) -> None:
    """Cancel error conversation."""

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
        text="Внесение ошибки прервано, вернулись в стартовое меню:",
        reply_markup=await keyboard_start(data.get("id_user_chat"), state),
    )
    await state.clear()


@router.callback_query(ErrorState, state="*")
async def timeout_callback_error(query: CallbackQuery, state: FSMContext) -> None:
    """Handle timeout for callback events."""

    await query.message.edit_text(
        text="Прервали внесение 📯 ошибки, не было активностей",
    )
    data = await state.get_data()
    await query.message.answer(
        text="Вернулись в стартовое меню",
        reply_markup=await keyboard_start(data.get("id_user_chat"), state),
    )
    await state.clear()


@router.message(ErrorState, state="*")
async def timeout_message_error(message: Message, state: FSMContext) -> None:
    """Handle timeout for message events."""

    data = await state.get_data()
    await message.answer(
        text="Прервали внесение 📯 ошибки, не было активностей",
        reply_markup=await keyboard_start(data.get("id_user_chat"), state),
    )
    await state.clear()


def conversation_errors() -> Router:
    """Return router with error handlers."""

    return router