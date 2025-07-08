from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pytz
from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from dotenv import load_dotenv

from class_StartKeyboard import keyboard_start
from gSheet import insert_to_error_krsk_bot
from keyboards import (
    BUTTON_TRANSFER,
    BUTTON_TRANSFER_CANCEL,
    keyboard_cancel_conversation,
    keyboard_from_list,
)
from postgres import get_stores_open

load_dotenv()
CHAT_TIMEOUT = int(os.getenv("CHAT_TIMEOUT"))
ERROR_ADMIN_ID = os.getenv("ERROR_ADMIN_ID")

router = Router()

ADDITIONAL_DIST_POINTS_FROM = [
    "ФК",
    "Магазин",
    "сэндвичи (GH и другие)",
    "Прочее",
]
ADDITIONAL_DIST_POINTS_TO = [
    "ФК",
    "Размен",
    "Магазин",
    "сэндвичи (GH и другие)",
    "Прочее",
]
CARGO_TYPE_LIST = ["заготовки", "хоз.средства", "упаковка", "деньги", "прочее"]
DELIVERY_TYPE_LIST = ["🚗 Курьер", "🚖 Такси", "🚘 Сотрудник"]


class TransferState(StatesGroup):
    """Conversation states for cargo transfer."""

    delivery_type = State()
    cargo_type = State()
    cargo_comment = State()
    from_store = State()
    to_store = State()


@router.message(Text(BUTTON_TRANSFER))
async def transfer_start(message: Message, state: FSMContext) -> None:
    """Start transfer conversation."""

    await state.update_data(id_user_chat=message.chat.id)
    await message.answer(
        text=f"Выбрали {BUTTON_TRANSFER}",
        reply_markup=keyboard_cancel_conversation(),
    )
    await message.answer(
        text="Кем перемещаем?",
        reply_markup=keyboard_from_list(DELIVERY_TYPE_LIST, 3),
    )
    await state.set_state(TransferState.delivery_type)


@router.callback_query(TransferState.delivery_type)
async def set_delivery_type(query: CallbackQuery, state: FSMContext) -> None:
    """Select delivery type."""

    delivery_type = query.data
    await state.update_data(delivery_type=delivery_type)
    await query.message.edit_text(
        text=f"<b>Перемещаем: </b>{delivery_type}\nТип груза?",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_from_list(CARGO_TYPE_LIST, 2),
    )
    await state.set_state(TransferState.cargo_type)


@router.callback_query(TransferState.cargo_type)
async def set_cargo_type(query: CallbackQuery, state: FSMContext) -> None:
    """Select cargo type."""

    cargo_type = query.data
    await state.update_data(cargo_type=cargo_type)
    data = await state.get_data()
    await query.message.edit_text(
        text=(
            f"<b>Перемещаем: </b>{data['delivery_type']}\n\n"
            f"<b>Перевозим: </b>{cargo_type}\n\n"
            "Что конкретно? Напишите"
        ),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(TransferState.cargo_comment)


@router.message(TransferState.cargo_comment)
async def set_cargo_comment(message: Message, state: FSMContext) -> None:
    """Save cargo comment and ask origin store."""

    cargo_comment = message.text
    await state.update_data(cargo_comment=cargo_comment)
    data = await state.get_data()
    from_points = np.concatenate(
        (ADDITIONAL_DIST_POINTS_FROM, get_stores_open("store_name")),
        axis=None,
    )
    await message.answer(
        text=(
            f"<b>Перемещаем: </b>{data['delivery_type']}\n\n"
            f"<b>Перевозим: </b>{data['cargo_type']}\n"
            f"<u>{cargo_comment}</u>\n\n"
            "Откуда?"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_from_list(from_points, 2),
    )
    await state.set_state(TransferState.from_store)


@router.callback_query(TransferState.from_store)
async def set_from_store(query: CallbackQuery, state: FSMContext) -> None:
    """Select origin store."""

    from_store = query.data
    await state.update_data(from_store=from_store)
    data = await state.get_data()
    to_points = np.concatenate(
        (ADDITIONAL_DIST_POINTS_TO, get_stores_open("store_name")),
        axis=None,
    )
    index = np.where(to_points == from_store)[0]
    if index.size > 0:
        to_points = np.delete(to_points, index)

    await query.message.edit_text(
        text=(
            f"<b>Перемещаем: </b>{data['delivery_type']}\n\n"
            f"<b>Перевозим: </b>{data['cargo_type']}\n"
            f"<u>{data['cargo_comment']}</u>\n\n"
            f"<b>Откуда: </b>{from_store}\n\n"
            "Куда?"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_from_list(to_points, 2),
    )
    await state.set_state(TransferState.to_store)


@router.callback_query(TransferState.to_store)
async def save_transfer(query: CallbackQuery, state: FSMContext) -> None:
    """Save transfer data to Google Sheet."""

    to_store = query.data
    await state.update_data(to_store=to_store)
    data = await state.get_data()

    krsk_now = datetime.now(
        tz=pytz.timezone("Asia/Krasnoyarsk")
    ).strftime("%d-%m-%Y %H:%M")
    try:
        insert_to_error_krsk_bot(
            "Перемещения",
            [
                krsk_now,
                query.from_user.id,
                query.from_user.username,
                data["from_store"],
                to_store,
                data["delivery_type"],
                data["cargo_type"],
                data["cargo_comment"],
            ],
        )
        await query.message.edit_text(
            text=(
                f"<b>Перемещаем: </b>{data['delivery_type']}\n\n"
                f"<b>Перевозим: </b>{data['cargo_type']}\n"
                f"<u>{data['cargo_comment']}</u>\n\n"
                f"<b>Откуда: </b>{data['from_store']}\n\n"
                f"<b>Куда: </b>{to_store}"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as exc:
        await query.message.answer(
            text="Возникла ошибка записи, вернулись обратно",
            reply_markup=await keyboard_start(query.message.chat.id, state),
        )
        await query.bot.send_message(
            chat_id=ERROR_ADMIN_ID,
            text=f"Ошибка при внесении перемещения {exc}",
        )
    finally:
        await query.message.answer(
            text="Вернулись в меню:",
            reply_markup=await keyboard_start(query.message.chat.id, state),
        )
        await state.clear()


@router.message(Text(BUTTON_TRANSFER_CANCEL))
async def transfer_cancel(message: Message, state: FSMContext) -> None:
    """Cancel transfer conversation."""

    await message.answer(
        text="Вернулись в меню:",
        reply_markup=await keyboard_start(message.chat.id, state),
    )
    await state.clear()


def conversation_transfer() -> Router:
    """Return router with transfer handlers."""

    return router